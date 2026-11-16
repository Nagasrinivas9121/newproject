from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.deps import TenantContext, get_current_tenant
from server.schemas.sync import DesktopSyncImportRequest, DesktopSyncResponse
from server.services.sync_service import process_desktop_sync

router = APIRouter(prefix="/sync", tags=["Desktop Synchronization & Migration"])


@router.post("/import-desktop", response_model=DesktopSyncResponse)
async def import_desktop_data(
    request: Request,
    payload: DesktopSyncImportRequest,
    ctx: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Import and reconcile records exported from a Windows desktop SQLite database.
    - Strict tenant isolation: Records are mapped strictly into the caller's tenant.
    - Prevents duplicates using family ID and desktop ID matching.
    - Validates record counts and schema structure.
    - Requires explicit client authorization and active tenant credentials.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await process_desktop_sync(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user.id,
        payload=payload,
        ip_address=client_ip,
    )
