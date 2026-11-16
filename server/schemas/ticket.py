import datetime
from pydantic import BaseModel


class TicketResponse(BaseModel):
    id: str
    tenant_id: str
    family_id: str
    original_filename: str
    safe_filename: str
    mime_type: str
    file_size: int
    sha256_checksum: str
    uploaded_at: datetime.datetime

    model_config = {"from_attributes": True}
