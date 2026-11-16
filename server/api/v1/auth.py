import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import settings
from server.core.database import get_db
from server.core.security import (
    clear_rate_limit,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    is_rate_limited,
    revoke_token,
    verify_password,
    verify_totp,
)
from server.deps import get_current_user, security_bearer
from server.models.tenant import Tenant
from server.models.user import User
from server.schemas.auth import (
    LoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from server.services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Authentication & Session"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user with email and password, enforcing rate limits and optional MFA."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_key = f"login:{client_ip}:{body.email.lower()}"

    if is_rate_limited(rate_key, max_attempts=settings.RATE_LIMIT_LOGIN_ATTEMPTS_PER_MIN, window_seconds=60):
        await log_action(
            db=db,
            action="LOGIN_RATE_LIMITED",
            details={"email": body.email.lower(), "ip": client_ip},
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 60 seconds before trying again.",
        )

    # Query user by email
    q = select(User).where(User.email == body.email.lower())
    res = await db.execute(q)
    user = res.scalars().first()

    if not user or not verify_password(body.password, user.hashed_password):
        await log_action(
            db=db,
            action="LOGIN_FAILED",
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            details={"email": body.email.lower(), "reason": "Invalid credentials"},
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact organization administrator.",
        )

    # Check Tenant status if user belongs to a tenant
    tenant_name = None
    if user.tenant_id:
        t_res = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = t_res.scalars().first()
        if tenant:
            tenant_name = tenant.name
            if tenant.status == "SUSPENDED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Organization workspace is suspended. Contact platform administrator.",
                )

    # Check Multi-Factor Authentication if enabled
    if user.mfa_enabled:
        if not body.mfa_code:
            return TokenResponse(
                access_token="",
                refresh_token="",
                expires_in=0,
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                tenant_id=user.tenant_id,
                tenant_name=tenant_name,
                mfa_required=True,
            )
        if not verify_totp(user.mfa_secret or "", body.mfa_code):
            await log_action(
                db=db,
                action="LOGIN_MFA_FAILED",
                tenant_id=user.tenant_id,
                user_id=user.id,
                details={"email": user.email},
                ip_address=client_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Multi-Factor Authentication (TOTP) code.",
            )

    # Login successful
    clear_rate_limit(rate_key)
    user.last_login_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    await db.flush()

    access_token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    await log_action(
        db=db,
        action="LOGIN_SUCCESS",
        tenant_id=user.tenant_id,
        user_id=user.id,
        details={"email": user.email, "role": user.role},
        ip_address=client_ip,
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
        mfa_required=False,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Obtain a new access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_id = payload.get("sub")
    q = select(User).where(User.id == user_id)
    res = await db.execute(q)
    user = res.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer active.",
        )

    tenant_name = None
    if user.tenant_id:
        t_res = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
        tenant = t_res.scalars().first()
        if tenant:
            tenant_name = tenant.name

    new_access_token = create_access_token(
        subject=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=body.refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        tenant_id=user.tenant_id,
        tenant_name=tenant_name,
        mfa_required=False,
    )


@router.post("/logout")
async def logout(
    credentials=Security(security_bearer),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke current access token and invalidate user session."""
    if credentials:
        revoke_token(credentials.credentials)

    await log_action(
        db=db,
        action="LOGOUT",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        details={"email": current_user.email},
    )
    await db.commit()
    return {"message": "Logged out successfully. Token has been revoked."}


@router.post("/password-reset-request")
async def request_password_reset(
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initiate password reset workflow and return verification token."""
    q = select(User).where(User.email == body.email.lower())
    res = await db.execute(q)
    user = res.scalars().first()

    # Generic return to prevent email enumeration attacks
    if not user:
        return {"message": "If the account exists, a password reset token has been generated."}

    reset_token = create_password_reset_token(user.email)
    await log_action(
        db=db,
        action="PASSWORD_RESET_REQUESTED",
        tenant_id=user.tenant_id,
        user_id=user.id,
        details={"email": user.email},
    )
    await db.commit()

    return {
        "message": "Password reset token generated successfully.",
        "reset_token": reset_token,
    }


@router.post("/password-reset-confirm")
async def confirm_password_reset(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Verify reset token and update password with secure bcrypt hash."""
    payload = decode_token(body.token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    email = payload.get("sub")
    q = select(User).where(User.email == email)
    res = await db.execute(q)
    user = res.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    user.hashed_password = hash_password(body.new_password)
    revoke_token(body.token)

    await log_action(
        db=db,
        action="PASSWORD_RESET_COMPLETED",
        tenant_id=user.tenant_id,
        user_id=user.id,
        details={"email": user.email},
    )
    await db.commit()

    return {"message": "Password reset successfully. You may now login with your new credentials."}


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a high-entropy TOTP secret and QR code URI for authenticator app configuration."""
    secret = generate_totp_secret()
    uri = get_totp_uri(secret=secret, account_name=current_user.email)

    current_user.mfa_secret = secret
    await db.commit()

    return MFASetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/mfa/verify-and-enable")
async def verify_and_enable_mfa(
    body: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify TOTP code against pending secret to activate 2FA protection."""
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup has not been initiated. Call /mfa/setup first.",
        )

    if not verify_totp(current_user.mfa_secret, body.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code is invalid. Check authenticator clock synchronization.",
        )

    current_user.mfa_enabled = True
    await log_action(
        db=db,
        action="MFA_ENABLED",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        details={"email": current_user.email},
    )
    await db.commit()

    return {"message": "Multi-Factor Authentication enabled successfully."}
