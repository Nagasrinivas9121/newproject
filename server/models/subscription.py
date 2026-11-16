import datetime
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from server.core.database import Base, utc_now


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_name = Column(String(32), default="TRIAL", nullable=False)  # TRIAL, MONTHLY, QUARTERLY, ANNUAL
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, EXPIRED, GRACE_PERIOD, SUSPENDED, CANCELLED
    start_date = Column(DateTime, default=utc_now, nullable=False)
    end_date = Column(DateTime, nullable=False)
    grace_period_days = Column(Integer, default=7, nullable=False)
    max_families = Column(Integer, default=100, nullable=False)
    max_users = Column(Integer, default=3, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    tenant = relationship("Tenant", back_populates="subscriptions")

    @property
    def is_valid(self) -> bool:
        """Verify whether subscription is currently usable (Active or within Grace Period)."""
        now = utc_now()
        if self.status == "SUSPENDED" or self.status == "CANCELLED":
            return False
        if now <= self.end_date:
            return True
        grace_end = self.end_date + datetime.timedelta(days=self.grace_period_days)
        return now <= grace_end

    @property
    def in_grace_period(self) -> bool:
        now = utc_now()
        if self.status in ("SUSPENDED", "CANCELLED"):
            return False
        grace_end = self.end_date + datetime.timedelta(days=self.grace_period_days)
        return self.end_date < now <= grace_end

    def __repr__(self) -> str:
        return f"<Subscription {self.plan_name} ({self.status}) valid_until={self.end_date}>"
