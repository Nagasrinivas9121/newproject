from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.schemas.subscription import SubscriptionResponse
from server.services.audit_service import log_action
from server.services.subscription_service import (
    evaluate_subscription_status,
    get_tenant_subscription,
)

router = APIRouter(prefix="/subscriptions", tags=["Subscription Management"])

AVAILABLE_PLANS = [
    {
        "plan_name": "TRIAL",
        "duration_days": 14,
        "max_families": 50,
        "max_users": 2,
        "features": ["Basic Family Management", "Pilgrim Registry", "Local Ticket Storage"],
    },
    {
        "plan_name": "MONTHLY",
        "duration_days": 30,
        "max_families": 500,
        "max_users": 5,
        "features": ["Full Family Management", "Analytics Dashboard", "Secure Ticket Storage", "Excel/CSV/PDF Reports"],
    },
    {
        "plan_name": "QUARTERLY",
        "duration_days": 90,
        "max_families": 2000,
        "max_users": 10,
        "features": ["Advanced Queue Intelligence", "Turnaround Analytics", "High-Volume Processing", "Priority Support"],
    },
    {
        "plan_name": "ANNUAL",
        "duration_days": 365,
        "max_families": 10000,
        "max_users": 25,
        "features": ["Unlimited Workspaces", "Custom Exports", "Dedicated Compliance Audit", "24/7 Assisted Desk SLA"],
    },
]


class PlanChangeRequest(BaseModel):
    requested_plan: str
    contact_notes: str = ""


@router.get("/plans", response_model=List[Dict])
async def list_available_plans():
    """List available subscription tier plans and their operational capabilities."""
    return AVAILABLE_PLANS


@router.get("/my-subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve active subscription details and remaining days for the current tenant workspace."""
    sub = await get_tenant_subscription(db, ctx.tenant_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription record found for this organization.",
        )

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


@router.post("/request-change")
async def request_plan_change(
    body: PlanChangeRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a formal subscription upgrade or renewal request.
    COMPLIANCE NOTICE: In accordance with PCI-DSS and financial governance rules,
    automatic payment collection is never performed without explicit payment provider authorization.
    """
    valid_plans = [p["plan_name"] for p in AVAILABLE_PLANS]
    if body.requested_plan.upper() not in valid_plans:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan name '{body.requested_plan}'. Valid options: {valid_plans}",
        )

    await log_action(
        db=db,
        action="SUBSCRIPTION_CHANGE_REQUESTED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="Subscription",
        entity_id=None,
        details={
            "requested_plan": body.requested_plan.upper(),
            "notes": body.contact_notes,
            "tenant_name": ctx.tenant.name,
        },
    )
    await db.commit()

    return {
        "status": "RECEIVED",
        "message": f"Your request to transition to {body.requested_plan.upper()} has been logged. Our billing team will verify and activate your plan.",
        "plan": body.requested_plan.upper(),
    }
