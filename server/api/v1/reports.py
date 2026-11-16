import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.models.family import Family
from server.models.pilgrim import Pilgrim
from server.services.audit_service import log_action

router = APIRouter(prefix="/reports", tags=["Tenant Reports & Exports"])


@router.get("/csv")
async def export_families_csv(
    status_filter: str = Query(None, alias="status"),
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Generate and stream a CSV export of families strictly within tenant workspace."""
    q = (
        select(Family)
        .where(Family.tenant_id == ctx.tenant_id)
        .order_by(Family.created_at.desc())
    )
    if status_filter:
        q = q.where(Family.status == status_filter)

    res = await db.execute(q)
    families = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Family ID",
        "Primary Contact",
        "Phone Number",
        "Email",
        "City",
        "State",
        "Preferred Date",
        "Priority",
        "Status",
        "Donation Amount",
        "Payment Status",
        "Payment Reference",
        "Created At",
    ])

    for f in families:
        writer.writerow([
            f.family_id_str,
            f.head_name,
            f.contact_number,
            f.email or "",
            f.city or "",
            f.state or "",
            f.preferred_date or "",
            f.priority,
            f.status,
            f.donation_amount,
            f.payment_status,
            f.payment_reference or "",
            f.created_at.isoformat(),
        ])

    csv_data = output.getvalue()
    output.close()

    await log_action(
        db=db,
        action="REPORT_EXPORTED_CSV",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="Report",
        details={"records_count": len(families)},
    )
    await db.commit()

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=families_{ctx.tenant.slug}.csv"
        },
    )


@router.get("/summary-json")
async def get_report_summary_json(
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Structured JSON summary for client reporting."""
    fams_q = select(Family).where(Family.tenant_id == ctx.tenant_id)
    fams = (await db.execute(fams_q)).scalars().all()

    pil_q = select(Pilgrim).where(Pilgrim.tenant_id == ctx.tenant_id)
    pils = (await db.execute(pil_q)).scalars().all()

    return {
        "tenant_id": ctx.tenant_id,
        "tenant_name": ctx.tenant.name,
        "total_families": len(fams),
        "total_pilgrims": len(pils),
        "booked_count": sum(1 for f in fams if f.status == "Booked"),
        "pending_count": sum(1 for f in fams if f.status == "Pending"),
        "in_progress_count": sum(1 for f in fams if f.status == "In Progress"),
        "total_donations": sum(f.donation_amount for f in fams),
    }
