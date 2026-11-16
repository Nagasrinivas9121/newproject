import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PilgrimCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    age: int = Field(ge=0, le=125)
    gender: str = Field(min_length=1, max_length=16)
    id_type: str = Field(min_length=2, max_length=32)
    id_number: str = Field(min_length=4, max_length=64)


class PilgrimUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=125)
    gender: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None


class PilgrimResponse(BaseModel):
    id: str
    tenant_id: str
    family_id: str
    name: str
    age: int
    gender: str
    id_type: str
    id_number_masked: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
