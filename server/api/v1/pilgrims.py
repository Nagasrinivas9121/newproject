from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.models.family import Family
from server.models.pilgrim import Pilgrim
from server.schemas.pilgrim import PilgrimCreate, PilgrimResponse, PilgrimUpdate
from server.services.audit_service import log_action
from server.services.sync_service import mask_id_number

router = APIRouter(prefix="/families/{family_id}/pilgrims", tags=["Pilgrim Management"])


@router.get("", response_model=List[PilgrimResponse])
async def list_pilgrims_for_family(
    family_id: str,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List all pilgrims in a family with server-side tenant isolation."""
    # First verify family belongs to tenant
    fam_q = select(Family).where(
        Family.id == family_id, Family.tenant_id == ctx.tenant_id
    )
    fam = (await db.execute(fam_q)).scalars().first()
    if not fam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found in your organization workspace.",
        )

    q = (
        select(Pilgrim)
        .where(
            Pilgrim.tenant_id == ctx.tenant_id,
            Pilgrim.family_id == family_id,
        )
        .order_by(Pilgrim.created_at.asc())
    )
    res = await db.execute(q)
    return res.scalars().all()


@router.post("", response_model=PilgrimResponse, status_code=status.HTTP_201_CREATED)
async def add_pilgrim_to_family(
    family_id: str,
    body: PilgrimCreate,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new pilgrim to a family with automatic ID masking for privacy.
    Ensures family belongs to authenticated tenant.
    """
    fam_q = select(Family).where(
        Family.id == family_id, Family.tenant_id == ctx.tenant_id
    )
    fam = (await db.execute(fam_q)).scalars().first()
    if not fam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found in your organization workspace.",
        )

    pilgrim = Pilgrim(
        tenant_id=ctx.tenant_id,  # Mandatory isolation
        family_id=fam.id,
        name=body.name,
        age=body.age,
        gender=body.gender,
        id_type=body.id_type,
        id_number_masked=mask_id_number(body.id_number),
    )
    db.add(pilgrim)
    await db.flush()

    await log_action(
        db=db,
        action="PILGRIM_ADDED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="Pilgrim",
        entity_id=pilgrim.id,
        details={"name": pilgrim.name, "id_type": pilgrim.id_type, "family_id": fam.id},
    )
    await db.commit()

    return pilgrim


@router.delete("/{pilgrim_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_pilgrim(
    family_id: str,
    pilgrim_id: str,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Delete pilgrim from family with tenant authorization."""
    q = select(Pilgrim).where(
        Pilgrim.id == pilgrim_id,
        Pilgrim.family_id == family_id,
        Pilgrim.tenant_id == ctx.tenant_id,  # Mandatory isolation
    )
    pilgrim = (await db.execute(q)).scalars().first()
    if not pilgrim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pilgrim record not found in your organization workspace.",
        )

    await log_action(
        db=db,
        action="PILGRIM_REMOVED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="Pilgrim",
        entity_id=pilgrim.id,
        details={"name": pilgrim.name},
    )

    await db.delete(pilgrim)
    await db.commit()
    return None
