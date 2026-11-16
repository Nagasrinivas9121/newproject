from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.models.family import Family
from server.models.pilgrim import Pilgrim
from server.models.ticket import TicketFile
from server.schemas.family import FamilyCreate, FamilyResponse, FamilyUpdate
from server.services.audit_service import log_action
from server.services.subscription_service import get_tenant_subscription

router = APIRouter(prefix="/families", tags=["Families & Bookings"])


async def _enrich_family_response(db: AsyncSession, fam: Family) -> FamilyResponse:
    """Compute attached pilgrim and ticket counts within tenant boundary."""
    pil_count_q = select(func.count(Pilgrim.id)).where(
        Pilgrim.tenant_id == fam.tenant_id, Pilgrim.family_id == fam.id
    )
    tkt_count_q = select(func.count(TicketFile.id)).where(
        TicketFile.tenant_id == fam.tenant_id, TicketFile.family_id == fam.id
    )

    pil_count = (await db.execute(pil_count_q)).scalar() or 0
    tkt_count = (await db.execute(tkt_count_q)).scalar() or 0

    return FamilyResponse(
        id=fam.id,
        tenant_id=fam.tenant_id,
        family_id_str=fam.family_id_str,
        head_name=fam.head_name,
        contact_number=fam.contact_number,
        email=fam.email,
        city=fam.city,
        state=fam.state,
        preferred_date=fam.preferred_date,
        priority=fam.priority,
        status=fam.status,
        donation_amount=fam.donation_amount,
        payment_status=fam.payment_status,
        payment_reference=fam.payment_reference,
        notes=fam.notes,
        pilgrims_count=pil_count,
        tickets_count=tkt_count,
        created_at=fam.created_at,
        updated_at=fam.updated_at,
    )


@router.get("", response_model=List[FamilyResponse])
async def list_families(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    search: Optional[str] = Query(None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List families strictly within the authenticated tenant workspace."""
    q = (
        select(Family)
        .where(Family.tenant_id == ctx.tenant_id)
        .order_by(Family.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if status_filter:
        q = q.where(Family.status == status_filter)
    if priority_filter:
        q = q.where(Family.priority == priority_filter)
    if search:
        search_pattern = f"%{search}%"
        q = q.where(
            (Family.head_name.ilike(search_pattern))
            | (Family.family_id_str.ilike(search_pattern))
            | (Family.contact_number.ilike(search_pattern))
        )

    res = await db.execute(q)
    families = res.scalars().all()
    return [await _enrich_family_response(db, f) for f in families]


@router.post("", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
async def create_family(
    body: FamilyCreate,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new family record bound strictly to the authenticated tenant.
    Never trusts client-supplied tenant ID.
    Enforces subscription family limit.
    """
    # 1. Check subscription family quota
    sub = await get_tenant_subscription(db, ctx.tenant_id)
    if sub:
        curr_count_q = select(func.count(Family.id)).where(
            Family.tenant_id == ctx.tenant_id
        )
        curr_count = (await db.execute(curr_count_q)).scalar() or 0
        if curr_count >= sub.max_families:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Subscription family quota reached ({curr_count}/{sub.max_families}). Upgrade subscription plan to add more.",
            )

    # 2. Check duplicate family_id_str within this tenant
    dup_q = select(Family).where(
        Family.tenant_id == ctx.tenant_id,
        Family.family_id_str == body.family_id_str,
    )
    if (await db.execute(dup_q)).scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Family ID '{body.family_id_str}' already exists in your workspace.",
        )

    # 3. Create family
    family = Family(
        tenant_id=ctx.tenant_id,  # FORCED SERVER-SIDE
        family_id_str=body.family_id_str,
        head_name=body.head_name,
        contact_number=body.contact_number,
        email=body.email,
        city=body.city,
        state=body.state,
        preferred_date=body.preferred_date,
        priority=body.priority,
        status=body.status,
        donation_amount=body.donation_amount,
        payment_status=body.payment_status,
        payment_reference=body.payment_reference,
        notes=body.notes,
    )
    db.add(family)
    await db.flush()

    await log_action(
        db=db,
        action="FAMILY_CREATED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="Family",
        entity_id=family.id,
        details={"family_id_str": family.family_id_str, "head_name": family.head_name},
    )
    await db.commit()

    return await _enrich_family_response(db, family)


@router.get("/{family_id}", response_model=FamilyResponse)
async def get_family(
    family_id: str,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Fetch single family record with strict tenant isolation check."""
    q = select(Family).where(
        Family.id == family_id,
        Family.tenant_id == ctx.tenant_id,  # Mandatory isolation
    )
    family = (await db.execute(q)).scalars().first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family record not found in your organization workspace.",
        )
    return await _enrich_family_response(db, family)


@router.put("/{family_id}", response_model=FamilyResponse)
async def update_family(
    family_id: str,
    body: FamilyUpdate,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Update family record with tenant authorization and change logging."""
    q = select(Family).where(
        Family.id == family_id,
        Family.tenant_id == ctx.tenant_id,
    )
    family = (await db.execute(q)).scalars().first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family record not found in your organization workspace.",
        )

    old_status = family.status
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(family, k, v)

    # If status changed, record specialized audit entry
    if "status" in update_data and update_data["status"] != old_status:
        await log_action(
            db=db,
            action="BOOKING_STATUS_CHANGED",
            tenant_id=ctx.tenant_id,
            user_id=ctx.user.id,
            entity_type="Family",
            entity_id=family.id,
            details={
                "family_id_str": family.family_id_str,
                "old_status": old_status,
                "new_status": family.status,
            },
        )
    else:
        await log_action(
            db=db,
            action="FAMILY_UPDATED",
            tenant_id=ctx.tenant_id,
            user_id=ctx.user.id,
            entity_type="Family",
            entity_id=family.id,
            details={"updated_fields": list(update_data.keys())},
        )

    await db.commit()
    return await _enrich_family_response(db, family)


@router.delete("/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family(
    family_id: str,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete family record and cascade-delete its pilgrims and tickets within tenant."""
    q = select(Family).where(
        Family.id == family_id,
        Family.tenant_id == ctx.tenant_id,
    )
    family = (await db.execute(q)).scalars().first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family record not found in your organization workspace.",
        )

    await log_action(
        db=db,
        action="FAMILY_DELETED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="Family",
        entity_id=family.id,
        details={"family_id_str": family.family_id_str},
    )

    await db.delete(family)
    await db.commit()
    return None
