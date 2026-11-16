import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    tenant_id: str
    plan_name: str = "TRIAL"  # TRIAL, MONTHLY, QUARTERLY, ANNUAL
    duration_days: int = 30
    grace_period_days: int = 7
    max_families: int = 100
    max_users: int = 3


class SubscriptionUpdate(BaseModel):
    plan_name: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, EXPIRED, GRACE_PERIOD, SUSPENDED, CANCELLED
    extend_days: Optional[int] = None
    grace_period_days: Optional[int] = None
    max_families: Optional[int] = None
    max_users: Optional[int] = None


class SubscriptionResponse(BaseModel):
    id: str
    tenant_id: str
    plan_name: str
    status: str
    start_date: datetime.datetime
    end_date: datetime.datetime
    grace_period_days: int
    max_families: int
    max_users: int
    is_valid: bool
    in_grace_period: bool
    days_remaining: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
