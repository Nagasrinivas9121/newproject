import datetime
import uuid
from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship
from server.core.database import Base, utc_now


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    contact_email = Column(String(128), nullable=False)
    contact_phone = Column(String(32), nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, SUSPENDED, PENDING
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="tenant", cascade="all, delete-orphan")
    families = relationship("Family", back_populates="tenant", cascade="all, delete-orphan")
    pilgrims = relationship("Pilgrim", back_populates="tenant", cascade="all, delete-orphan")
    tickets = relationship("TicketFile", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Tenant {self.slug} ({self.status})>"
