import datetime
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from server.core.database import Base, utc_now


class Pilgrim(Base):
    __tablename__ = "pilgrims"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(String(36), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(16), nullable=False)
    id_type = Column(String(32), nullable=False)  # Aadhaar, Passport, Voter ID
    id_number_masked = Column(String(64), nullable=False)  # e.g. XXXX-XXXX-1234
    id_number_encrypted = Column(String(255), nullable=True)  # AES/Fernet encrypted for operational auto-fill
    photo_path = Column(String(255), nullable=True)
    desktop_source_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    tenant = relationship("Tenant", back_populates="pilgrims")
    family = relationship("Family", back_populates="pilgrims")

    __table_args__ = (
        Index("idx_pilgrims_tenant_family", "tenant_id", "family_id"),
        Index("idx_pilgrims_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Pilgrim {self.name} age={self.age} ({self.id_type})>"
