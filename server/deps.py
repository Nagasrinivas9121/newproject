from typing import Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.core.security import decode_token
from server.models.tenant import Tenant
from server.models.user import User
from server.services.subscription_service import (
    evaluate_subscription_status,
    get_tenant_subscription,
)

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate bearer JWT token, verify against blocklist, and load active user record."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided in request header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject identifier missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    q = select(User).where(User.id == user_id)
    res = await db.execute(q)
    user = res.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account matching token does not exist.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been deactivated or suspended.",
        )

    return user


async def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the authenticated user holds platform-level SUPER_ADMIN authorization."""
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Administrator authorization required for this operation.",
        )
    return current_user


class TenantContext:
    """Encapsulates server-verified tenant identity and authenticated user."""

    def __init__(self, tenant: Tenant, user: User, is_in_grace_period: bool = False):
        self.tenant = tenant
        self.tenant_id = tenant.id
        self.user = user
        self.is_in_grace_period = is_in_grace_period


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    Core Server-Side Multi-Tenant Authorization Guard.
    
    1. Extracts tenant_id strictly from the authenticated user token.
    2. Verifies client organization exists in database.
    3. Verifies client organization is ACTIVE (not suspended).
    4. Evaluates client subscription validity and grace period.
    5. Rejects any cross-tenant spoofing or unauthorized tenant access.
    """
    if current_user.role == "SUPER_ADMIN":
        # Super admin does not belong to a client tenant
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin cannot directly access client workspace data. Strict tenant separation enforced.",
        )

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any active tenant organization.",
        )

    # Fetch Tenant from database
    q = select(Tenant).where(Tenant.id == current_user.tenant_id)
    res = await db.execute(q)
    tenant = res.scalars().first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant organization not found.",
        )

    if tenant.status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant organization account has been suspended by administrator. Please contact support.",
        )

    # Evaluate Subscription status
    sub = await get_tenant_subscription(db, tenant.id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="No active subscription found for this tenant organization.",
        )

    is_valid, in_grace, _ = await evaluate_subscription_status(db, sub)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription expired and grace period lapsed. Access restricted until renewal.",
        )

    return TenantContext(tenant=tenant, user=current_user, is_in_grace_period=in_grace)


async def require_tenant_admin(
    tenant_ctx: TenantContext = Depends(get_current_tenant),
) -> TenantContext:
    """Ensure the user within the tenant holds TENANT_ADMIN role."""
    if tenant_ctx.user.role != "TENANT_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant Administrator role required for this configuration change.",
        )
    return tenant_ctx
