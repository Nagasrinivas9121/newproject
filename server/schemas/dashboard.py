from typing import List, Optional
from pydantic import BaseModel
from server.schemas.tenant import TenantUsageStats


class SuperAdminDashboardStats(BaseModel):
    total_clients: int
    active_clients: int
    suspended_clients: int
    pending_clients: int
    total_users: int
    active_subscriptions: int
    expired_subscriptions: int
    grace_period_subscriptions: int
    clients: List[TenantUsageStats]


class ClientDashboardStats(BaseModel):
    tenant_id: str
    tenant_name: str
    total_families: int
    total_pilgrims: int
    completed_bookings: int
    pending_bookings: int
    in_progress_bookings: int
    unavailable_bookings: int
    cancelled_bookings: int
    completion_rate_pct: float
    total_donations_pledged: float
    total_donations_collected: float
    plan_name: str
    subscription_status: str
    days_remaining: int
    in_grace_period: bool
    recent_families: List[dict] = []
