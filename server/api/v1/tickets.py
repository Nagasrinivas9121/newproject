from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.models.family import Family
from server.models.ticket import TicketFile
from server.schemas.ticket import TicketResponse
from server.services.audit_service import log_action
from server.services.storage_service import save_ticket_pdf, verify_ticket_access

router = APIRouter(prefix="/tickets", tags=["Private Ticket Storage"])


@router.post("/families/{family_id}/upload", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def upload_ticket_pdf(
    family_id: str,
    file: UploadFile = File(...),
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Secure, private ticket PDF upload.
    - Validates MIME type and %PDF magic bytes.
    - Limits size to 10MB.
    - Computes SHA-256 checksum.
    - Stores file in tenant-isolated directory: storage/tenants/{tenant_id}/tickets/...
    """
    # 1. Verify family belongs to tenant
    fam_q = select(Family).where(
        Family.id == family_id, Family.tenant_id == ctx.tenant_id
    )
    fam = (await db.execute(fam_q)).scalars().first()
    if not fam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family not found in your organization workspace.",
        )

    # 2. Read and validate content
    content = await file.read()
    save_result = await save_ticket_pdf(
        tenant_id=ctx.tenant_id,
        family_id=fam.id,
        original_filename=file.filename or "ticket.pdf",
        file_bytes=content,
    )

    # 3. Create TicketFile database record
    ticket = TicketFile(
        tenant_id=ctx.tenant_id,  # FORCED SERVER-SIDE
        family_id=fam.id,
        original_filename=save_result["original_filename"],
        safe_filename=save_result["safe_filename"],
        storage_path=save_result["storage_path"],
        mime_type=save_result["mime_type"],
        file_size=save_result["file_size"],
        sha256_checksum=save_result["sha256_checksum"],
    )
    db.add(ticket)
    await db.flush()

    await log_action(
        db=db,
        action="TICKET_UPLOADED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="TicketFile",
        entity_id=ticket.id,
        details={
            "filename": ticket.original_filename,
            "size": ticket.file_size,
            "sha256": ticket.sha256_checksum,
        },
    )
    await db.commit()

    return ticket


@router.get("/families/{family_id}", response_model=List[TicketResponse])
async def list_tickets_for_family(
    family_id: str,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """List ticket files attached to a family with tenant authorization."""
    q = (
        select(TicketFile)
        .where(
            TicketFile.tenant_id == ctx.tenant_id,
            TicketFile.family_id == family_id,
        )
        .order_by(TicketFile.uploaded_at.desc())
    )
    res = await db.execute(q)
    return res.scalars().all()


@router.get("/{ticket_id}/download")
async def download_ticket_pdf(
    ticket_id: str,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Authorized private streaming download for ticket PDFs.
    - Strictly checks that ticket belongs to caller's tenant.
    - Prevents directory traversal.
    - NEVER exposes public URLs.
    """
    q = select(TicketFile).where(
        TicketFile.id == ticket_id,
        TicketFile.tenant_id == ctx.tenant_id,  # Strict tenant isolation
    )
    ticket = (await db.execute(q)).scalars().first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket record not found in your organization workspace.",
        )

    file_path = verify_ticket_access(
        tenant_id=ctx.tenant_id, storage_path=ticket.storage_path
    )

    await log_action(
        db=db,
        action="TICKET_DOWNLOADED",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        entity_type="TicketFile",
        entity_id=ticket.id,
        details={"filename": ticket.original_filename},
    )
    await db.commit()

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=ticket.original_filename,
    )
