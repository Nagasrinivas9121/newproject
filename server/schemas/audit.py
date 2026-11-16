import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details_sanitized: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
