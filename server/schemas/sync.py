from typing import List, Optional
from pydantic import BaseModel, Field


class DesktopPilgrimImport(BaseModel):
    name: str
    age: int = Field(ge=0, le=125)
    gender: str
    id_type: str
    id_number: str
    desktop_source_id: Optional[int] = None


class DesktopFamilyImport(BaseModel):
    desktop_source_id: int
    family_id_str: str
    head_name: str
    contact_number: str
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
    pilgrims: List[DesktopPilgrimImport] = []


class DesktopSyncImportRequest(BaseModel):
    source_app: str = "SRIVANI BOOKING MANAGER Desktop"
    client_version: str
    families_count: int
    pilgrims_count: int
    checksum: Optional[str] = None
    families: List[DesktopFamilyImport]


class DesktopSyncResponse(BaseModel):
    success: bool
    imported_families: int
    imported_pilgrims: int
    skipped_duplicates: int
    error_count: int
    message: str
