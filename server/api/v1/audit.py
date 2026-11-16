from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.models.audit import AuditLog
from server.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Trail"])


@router.get("", response_model=List[AuditLogResponse])
async def list_tenant_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    action: Optional[str] = None,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve immutable audit events strictly within the caller's tenant organization."""
    q = (
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if action:
        q = q.where(AuditLog.action == action)

    res = await db.execute(q)
    return res.scalars().all()
