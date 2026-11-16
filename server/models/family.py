import datetime
import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from server.core.database import Base, utc_now


class Family(Base):
    __tablename__ = "families"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id_str = Column(String(64), nullable=False)
    head_name = Column(String(128), nullable=False)
    contact_number = Column(String(32), nullable=False)
    email = Column(String(128), nullable=True)
    city = Column(String(64), nullable=True)
    state = Column(String(64), nullable=True)
    preferred_date = Column(String(16), nullable=True)  # YYYY-MM-DD
    priority = Column(String(16), default="Normal", nullable=False)  # Normal, High, Urgent
    status = Column(String(32), default="Pending", nullable=False)  # Pending, In Progress, Booked, Unavailable, Cancelled
    donation_amount = Column(Float, default=0.0, nullable=False)
    payment_status = Column(String(32), default="Pending", nullable=False)  # Pending, Paid, Failed, Refunded
    payment_reference = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    desktop_source_id = Column(Integer, nullable=True)  # Traceability link for migrated desktop records
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    tenant = relationship("Tenant", back_populates="families")
    pilgrims = relationship("Pilgrim", back_populates="family", cascade="all, delete-orphan")
    tickets = relationship("TicketFile", back_populates="family", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_families_tenant_status", "tenant_id", "status"),
        Index("idx_families_tenant_prefdate", "tenant_id", "preferred_date"),
        Index("idx_families_tenant_family_id_str", "tenant_id", "family_id_str", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Family {self.family_id_str} ({self.head_name}) status={self.status}>"
