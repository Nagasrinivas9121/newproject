import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.core.security import hash_password
from server.deps import require_super_admin
from server.models.audit import AuditLog
from server.models.family import Family
from server.models.pilgrim import Pilgrim
from server.models.subscription import Subscription
from server.models.tenant import Tenant
from server.models.ticket import TicketFile
from server.models.user import User
from server.schemas.audit import AuditLogResponse
from server.schemas.dashboard import SuperAdminDashboardStats
from server.schemas.subscription import SubscriptionResponse, SubscriptionUpdate
from server.schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    TenantUsageStats,
)
from server.services.audit_service import log_action
from server.services.subscription_service import evaluate_subscription_status

router = APIRouter(prefix="/super-admin", tags=["Super Admin Operations"])


async def _build_tenant_stats(db: AsyncSession, tenant: Tenant) -> TenantUsageStats:
    """Compute aggregate usage metrics for a single tenant WITHOUT accessing devotee PII."""
    # Subscriptions
    sub_q = select(Subscription).where(Subscription.tenant_id == tenant.id).order_by(Subscription.created_at.desc())
    sub_res = await db.execute(sub_q)
    sub = sub_res.scalars().first()

    is_sub_valid = False
    plan_name = "NONE"
    sub_status = "NONE"
    sub_expiry = None
    if sub:
        is_sub_valid, in_grace, _ = await evaluate_subscription_status(db, sub)
        plan_name = sub.plan_name
        sub_status = sub.status
        sub_expiry = sub.end_date

    # Counts
    fam_count_q = select(func.count(Family.id)).where(Family.tenant_id == tenant.id)
    fam_count = (await db.execute(fam_count_q)).scalar() or 0

    pil_count_q = select(func.count(Pilgrim.id)).where(Pilgrim.tenant_id == tenant.id)
    pil_count = (await db.execute(pil_count_q)).scalar() or 0

    tkt_stats_q = select(func.count(TicketFile.id), func.coalesce(func.sum(TicketFile.file_size), 0)).where(TicketFile.tenant_id == tenant.id)
    tkt_res = (await db.execute(tkt_stats_q)).first()
    tkt_count = tkt_res[0] or 0
    storage_bytes = tkt_res[1] or 0

    user_count_q = select(func.count(User.id)).where(User.tenant_id == tenant.id, User.is_active == True)
    user_count = (await db.execute(user_count_q)).scalar() or 0

    return TenantUsageStats(
        tenant_id=tenant.id,
        slug=tenant.slug,
        name=tenant.name,
        status=tenant.status,
        created_at=tenant.created_at,
        plan_name=plan_name,
        subscription_status=sub_status,
        subscription_expiry=sub_expiry,
        is_subscription_valid=is_sub_valid,
        total_families=fam_count,
        total_pilgrims=pil_count,
        total_tickets=tkt_count,
        storage_bytes=storage_bytes,
        active_users=user_count,
    )


@router.get("/dashboard", response_model=SuperAdminDashboardStats)
async def get_super_admin_dashboard(
    current_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Platform-level administrative overview.
    NOTE: Super Admin has zero access to individual devotee PII. All data is aggregated.
    """
    tenants_res = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    all_tenants = tenants_res.scalars().all()

    clients_stats = []
    total_clients = len(all_tenants)
    active_clients = 0
    suspended_clients = 0
    pending_clients = 0
    active_subs = 0
    expired_subs = 0
    grace_subs = 0

    for t in all_tenants:
        stats = await _build_tenant_stats(db, t)
        clients_stats.append(stats)
        if t.status == "ACTIVE":
            active_clients += 1
        elif t.status == "SUSPENDED":
            suspended_clients += 1
        else:
            pending_clients += 1

        if stats.subscription_status == "ACTIVE":
            active_subs += 1
        elif stats.subscription_status == "GRACE_PERIOD":
            grace_subs += 1
        else:
            expired_subs += 1

    user_count_q = select(func.count(User.id))
    total_users = (await db.execute(user_count_q)).scalar() or 0

    return SuperAdminDashboardStats(
        total_clients=total_clients,
        active_clients=active_clients,
        suspended_clients=suspended_clients,
        pending_clients=pending_clients,
        total_users=total_users,
        active_subscriptions=active_subs,
        expired_subscriptions=expired_subs,
        grace_period_subscriptions=grace_subs,
        clients=clients_stats,
    )


@router.get("/tenants", response_model=List[TenantUsageStats])
async def list_tenants(
    current_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all registered client tenant organizations and their usage metrics."""
    res = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = res.scalars().all()
    return [await _build_tenant_stats(db, t) for t in tenants]


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    current_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Register and provision a new client tenant organization, admin user, and initial subscription."""
    # Check slug collision
    exist_slug = (await db.execute(select(Tenant).where(Tenant.slug == body.slug))).scalars().first()
    if exist_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant identifier slug '{body.slug}' is already taken.",
        )

    # Check admin email collision
    exist_email = (await db.execute(select(User).where(User.email == body.admin_email.lower()))).scalars().first()
    if exist_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User email '{body.admin_email}' is already registered.",
        )

    # 1. Create Tenant
    tenant = Tenant(
        slug=body.slug,
        name=body.name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        status="ACTIVE",
    )
    db.add(tenant)
    await db.flush()

    # 2. Create Tenant Admin User
    admin_user = User(
        tenant_id=tenant.id,
        email=body.admin_email.lower(),
        hashed_password=hash_password(body.admin_password),
        full_name=body.admin_name,
        role="TENANT_ADMIN",
        is_active=True,
    )
    db.add(admin_user)

    # 3. Create Initial Subscription (Trial: 30 days)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    sub = Subscription(
        tenant_id=tenant.id,
        plan_name=body.plan_name.upper(),
        status="ACTIVE",
        start_date=now,
        end_date=now + datetime.timedelta(days=30),
        grace_period_days=7,
        max_families=100 if body.plan_name.upper() == "TRIAL" else 5000,
        max_users=3 if body.plan_name.upper() == "TRIAL" else 15,
    )
    db.add(sub)

    await log_action(
        db=db,
        action="TENANT_CREATED",
        tenant_id=tenant.id,
        user_id=current_admin.id,
        entity_type="Tenant",
        entity_id=tenant.id,
        details={"name": tenant.name, "slug": tenant.slug, "plan": body.plan_name},
    )
    await db.commit()

    return tenant


@router.patch("/tenants/{tenant_id}/status", response_model=TenantResponse)
async def update_tenant_status(
    tenant_id: str,
    body: TenantUpdate,
    current_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Suspend or reactivate a client organization workspace."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    old_status = tenant.status
    if body.status:
        tenant.status = body.status
    if body.name:
        tenant.name = body.name
    if body.contact_email:
        tenant.contact_email = body.contact_email
    if body.contact_phone:
        tenant.contact_phone = body.contact_phone

    await log_action(
        db=db,
        action="TENANT_STATUS_UPDATED",
        tenant_id=tenant.id,
        user_id=current_admin.id,
        entity_type="Tenant",
        entity_id=tenant.id,
        details={"old_status": old_status, "new_status": tenant.status},
    )
    await db.commit()
    return tenant


@router.post("/tenants/{tenant_id}/subscription", response_model=SubscriptionResponse)
async def update_tenant_subscription(
    tenant_id: str,
    body: SubscriptionUpdate,
    current_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update or extend a tenant subscription."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalars().first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

    sub_q = select(Subscription).where(Subscription.tenant_id == tenant_id).order_by(Subscription.created_at.desc())
    sub = (await db.execute(sub_q)).scalars().first()

    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    if not sub:
        # Create brand new subscription
        sub = Subscription(
            tenant_id=tenant.id,
            plan_name=body.plan_name or "MONTHLY",
            status="ACTIVE",
            start_date=now,
            end_date=now + datetime.timedelta(days=body.extend_days or 30),
            grace_period_days=body.grace_period_days or 7,
            max_families=body.max_families or 1000,
            max_users=body.max_users or 5,
        )
        db.add(sub)
    else:
        if body.plan_name:
            sub.plan_name = body.plan_name
        if body.status:
            sub.status = body.status
        if body.extend_days:
            base_date = max(sub.end_date, now)
            sub.end_date = base_date + datetime.timedelta(days=body.extend_days)
            sub.status = "ACTIVE"
        if body.grace_period_days is not None:
            sub.grace_period_days = body.grace_period_days
        if body.max_families is not None:
            sub.max_families = body.max_families
        if body.max_users is not None:
            sub.max_users = body.max_users

    await log_action(
        db=db,
        action="SUBSCRIPTION_UPDATED",
        tenant_id=tenant.id,
        user_id=current_admin.id,
        entity_type="Subscription",
        entity_id=sub.id,
        details={"plan": sub.plan_name, "status": sub.status, "end_date": str(sub.end_date)},
    )
    await db.commit()

    is_valid, in_grace, days_left = await evaluate_subscription_status(db, sub)
    return SubscriptionResponse(
        id=sub.id,
        tenant_id=sub.tenant_id,
        plan_name=sub.plan_name,
        status=sub.status,
        start_date=sub.start_date,
        end_date=sub.end_date,
        grace_period_days=sub.grace_period_days,
        max_families=sub.max_families,
        max_users=sub.max_users,
        is_valid=is_valid,
        in_grace_period=in_grace,
        days_remaining=days_left,
        created_at=sub.created_at,
    )


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_platform_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: Optional[str] = None,
    current_admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Platform audit log inspection for compliance and incident analysis."""
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        q = q.where(AuditLog.action == action)
    res = await db.execute(q)
    return res.scalars().all()
