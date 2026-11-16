"""
SRIVANI BOOKING MANAGER - Dedicated Family Booking Workspace & Step-by-Step Assistant
Phase 9 Fast Booking Preparation Engine Integration.
"""
from typing import Optional, Callable
from preparation_workspace import ManualBookingWorkspaceDialog

# Alias BookingWorkspaceDialog directly to Phase 9 ManualBookingWorkspaceDialog
class BookingWorkspaceDialog(ManualBookingWorkspaceDialog):
    """
    Dedicated Family Booking Workspace.
    Provides complete devotee details, document readiness verification,
    step-by-step booking checklist, official TTD portal launcher,
    and rapid status/ticket recording.
    """
    def __init__(
        self,
        parent,
        family_id: int,
        on_update_callback: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, family_id, on_update_callback)
