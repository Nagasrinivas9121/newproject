import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    role: str = "TENANT_OPERATOR"  # TENANT_ADMIN, TENANT_OPERATOR
    tenant_id: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    email: str
    full_name: str
    role: str
    is_active: bool
    mfa_enabled: bool
    last_login_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
