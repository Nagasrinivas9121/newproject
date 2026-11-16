import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FamilyCreate(BaseModel):
    family_id_str: str = Field(min_length=1, max_length=64)
    head_name: str = Field(min_length=2, max_length=128)
    contact_number: str = Field(min_length=7, max_length=32)
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    preferred_date: Optional[str] = None
    priority: str = "Normal"
    status: str = "Pending"
    donation_amount: float = 0.0
    payment_status: str = "Pending"
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


class FamilyUpdate(BaseModel):
    head_name: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    preferred_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    donation_amount: Optional[float] = None
    payment_status: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


class FamilyResponse(BaseModel):
    id: str
    tenant_id: str
    family_id_str: str
    head_name: str
    contact_number: str
    email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    preferred_date: Optional[str] = None
    priority: str
    status: str
    donation_amount: float
    payment_status: str
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    pilgrims_count: int = 0
    tickets_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
