import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_name: str = Field(min_length=2)
    plan_name: str = "TRIAL"


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, SUSPENDED, PENDING


class TenantResponse(BaseModel):
    id: str
    slug: str
    name: str
    contact_email: str
    contact_phone: Optional[str] = None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class TenantUsageStats(BaseModel):
    tenant_id: str
    slug: str
    name: str
    status: str
    created_at: datetime.datetime
    plan_name: str
    subscription_status: str
    subscription_expiry: Optional[datetime.datetime] = None
    is_subscription_valid: bool
    total_families: int
    total_pilgrims: int
    total_tickets: int
    storage_bytes: int
    active_users: int
