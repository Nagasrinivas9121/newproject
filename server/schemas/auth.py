from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    mfa_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    full_name: str
    role: str
    tenant_id: Optional[str] = None
    tenant_name: Optional[str] = None
    mfa_required: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)
