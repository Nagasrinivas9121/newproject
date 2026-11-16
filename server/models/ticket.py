import datetime
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from server.core.database import Base, utc_now


class TicketFile(Base):
    __tablename__ = "ticket_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    safe_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(64), default="application/pdf", nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256_checksum = Column(String(64), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)

    tenant = relationship("Tenant", back_populates="tickets")
    family = relationship("Family", back_populates="tickets")

    __table_args__ = (
        Index("idx_tickets_tenant_family", "tenant_id", "family_id"),
        Index("idx_tickets_tenant_checksum", "tenant_id", "sha256_checksum"),
    )

    def __repr__(self) -> str:
        return f"<TicketFile {self.original_filename} size={self.file_size}B>"
