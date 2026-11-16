from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.models.family import Family
from server.models.pilgrim import Pilgrim
from server.schemas.dashboard import ClientDashboardStats
from server.services.subscription_service import (
    evaluate_subscription_status,
    get_tenant_subscription,
)

router = APIRouter(prefix="/client", tags=["Client Workspace & Dashboard"])


@router.get("/dashboard", response_model=ClientDashboardStats)
async def get_client_dashboard(
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Client operational KPI dashboard.
    Data is strictly isolated to the authenticated tenant workspace.
    """
    tenant_id = ctx.tenant_id

    # 1. Total families and status breakdowns
    status_counts_q = (
        select(Family.status, func.count(Family.id))
        .where(Family.tenant_id == tenant_id)
        .group_by(Family.status)
    )
    status_res = (await db.execute(status_counts_q)).all()
    status_map = {r[0]: r[1] for r in status_res}

    completed = status_map.get("Booked", 0)
    pending = status_map.get("Pending", 0)
    in_progress = status_map.get("In Progress", 0)
    unavailable = status_map.get("Unavailable", 0)
    cancelled = status_map.get("Cancelled", 0)
    total_families = sum(status_map.values())

    completion_rate = (
        round((completed / total_families) * 100, 1) if total_families > 0 else 0.0
    )

    # 2. Total Pilgrims
    pil_count_q = (
        select(func.count(Pilgrim.id)).where(Pilgrim.tenant_id == tenant_id)
    )
    total_pilgrims = (await db.execute(pil_count_q)).scalar() or 0

    # 3. Financial aggregates
    pledged_q = select(func.coalesce(func.sum(Family.donation_amount), 0.0)).where(
        Family.tenant_id == tenant_id
    )
    total_pledged = float((await db.execute(pledged_q)).scalar() or 0.0)

    collected_q = select(func.coalesce(func.sum(Family.donation_amount), 0.0)).where(
        Family.tenant_id == tenant_id, Family.payment_status == "Paid"
    )
    total_collected = float((await db.execute(collected_q)).scalar() or 0.0)

    # 4. Subscription details
    sub = await get_tenant_subscription(db, tenant_id)
    is_valid, in_grace, days_left = False, False, 0
    plan_name = "NONE"
    sub_status = "INACTIVE"
    if sub:
        is_valid, in_grace, days_left = await evaluate_subscription_status(db, sub)
        plan_name = sub.plan_name
        sub_status = sub.status

    # 5. Recent 5 families
    recent_q = (
        select(Family)
        .where(Family.tenant_id == tenant_id)
        .order_by(Family.created_at.desc())
        .limit(5)
    )
    recent_res = (await db.execute(recent_q)).scalars().all()
    recent_list = [
        {
            "id": f.id,
            "family_id_str": f.family_id_str,
            "head_name": f.head_name,
            "contact_number": f.contact_number,
            "status": f.status,
            "preferred_date": f.preferred_date,
            "created_at": f.created_at.isoformat(),
        }
        for f in recent_res
    ]

    return ClientDashboardStats(
        tenant_id=tenant_id,
        tenant_name=ctx.tenant.name,
        total_families=total_families,
        total_pilgrims=total_pilgrims,
        completed_bookings=completed,
        pending_bookings=pending,
        in_progress_bookings=in_progress,
        unavailable_bookings=unavailable,
        cancelled_bookings=cancelled,
        completion_rate_pct=completion_rate,
        total_donations_pledged=total_pledged,
        total_donations_collected=total_collected,
        plan_name=plan_name,
        subscription_status=sub_status,
        days_remaining=days_left,
        in_grace_period=in_grace,
        recent_families=recent_list,
    )
