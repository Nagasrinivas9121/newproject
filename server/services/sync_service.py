import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.models.family import Family
from server.models.pilgrim import Pilgrim
from server.schemas.sync import DesktopSyncImportRequest, DesktopSyncResponse
from server.services.audit_service import log_action


def mask_id_number(id_num: str) -> str:
    """Mask identity proof numbers to display only the last 4 digits for privacy."""
    clean = id_num.strip()
    if len(clean) <= 4:
        return "****"
    return f"XXXX-XXXX-{clean[-4:]}"


async def process_desktop_sync(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    payload: DesktopSyncImportRequest,
    ip_address: str = "127.0.0.1",
) -> DesktopSyncResponse:
    """Import and reconcile records exported from the Windows desktop SQLite database."""
    imported_families = 0
    imported_pilgrims = 0
    skipped_duplicates = 0
    errors = 0

    # Retrieve existing family identifiers for this tenant to prevent duplication
    existing_q = select(Family.family_id_str).where(Family.tenant_id == tenant_id)
    existing_res = await db.execute(existing_q)
    existing_fams = set(existing_res.scalars().all())

    for fam_in in payload.families:
        try:
            if fam_in.family_id_str in existing_fams:
                skipped_duplicates += 1
                continue

            # Create new Family record bound strictly to this tenant
            family = Family(
                tenant_id=tenant_id,
                family_id_str=fam_in.family_id_str,
                head_name=fam_in.head_name,
                contact_number=fam_in.contact_number,
                email=fam_in.email,
                city=fam_in.city,
                state=fam_in.state,
                preferred_date=fam_in.preferred_date,
                priority=fam_in.priority,
                status=fam_in.status,
                donation_amount=fam_in.donation_amount,
                payment_status=fam_in.payment_status,
                payment_reference=fam_in.payment_reference,
                notes=fam_in.notes,
                desktop_source_id=fam_in.desktop_source_id,
            )
            db.add(family)
            await db.flush()  # Generate family.id

            existing_fams.add(fam_in.family_id_str)
            imported_families += 1

            # Process and attach pilgrims
            for pil_in in fam_in.pilgrims:
                pilgrim = Pilgrim(
                    tenant_id=tenant_id,
                    family_id=family.id,
                    name=pil_in.name,
                    age=pil_in.age,
                    gender=pil_in.gender,
                    id_type=pil_in.id_type,
                    id_number_masked=mask_id_number(pil_in.id_number),
                    desktop_source_id=pil_in.desktop_source_id,
                )
                db.add(pilgrim)
                imported_pilgrims += 1

        except Exception:
            errors += 1

    await db.commit()

    # Record Audit Log entry
    await log_action(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="DESKTOP_SYNC_COMPLETED",
        entity_type="Sync",
        entity_id=None,
        details={
            "imported_families": imported_families,
            "imported_pilgrims": imported_pilgrims,
            "skipped_duplicates": skipped_duplicates,
            "errors": errors,
            "client_version": payload.client_version,
        },
        ip_address=ip_address,
    )

    return DesktopSyncResponse(
        success=True,
        imported_families=imported_families,
        imported_pilgrims=imported_pilgrims,
        skipped_duplicates=skipped_duplicates,
        error_count=errors,
        message=f"Sync completed successfully: {imported_families} families imported, {skipped_duplicates} duplicate records safely skipped.",
    )
