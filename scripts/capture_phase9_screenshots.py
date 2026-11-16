"""
SRIVANI BOOKING MANAGER - Phase 9 Fast Booking Preparation Engine UI Screenshot Capture Utility
Captures high-resolution PNG screenshots of Phase 9 components:
1. Fast Booking Dashboard
2. Manual Booking Workspace Dialog
3. Document Management Dialog
4. Booking History View
"""
import os
import sys
import time
import datetime
import ctypes
from pathlib import Path
import tkinter as tk
from PIL import Image

# Ensure repo root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import config

demo_db = REPO_ROOT / "data" / "demo_phase9.db"
demo_db.parent.mkdir(parents=True, exist_ok=True)
config.DB_PATH = demo_db

from database import (
    init_db,
    get_connection,
    add_family_with_pilgrims,
    add_family_document,
    update_family_readiness,
    update_family_payment_tracking,
)
from preparation_workspace import (
    FastBookingDashboardView,
    ManualBookingWorkspaceDialog,
    DocumentManagementDialog,
    BookingHistoryFrame,
)
from readiness_engine import (
    calculate_booking_readiness,
    STATUS_READY_FOR_MANUAL_BOOKING,
    STATUS_INCOMPLETE,
    STATUS_BOOKING_IN_PROGRESS,
    STATUS_BOOKED,
    PAYMENT_PAID,
    PAYMENT_PENDING,
    PAYMENT_NOT_PAID,
)

SCREENSHOTS_DIR = REPO_ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def grab_window(win, dest_path: Path):
    """Capture native Windows window using PrintWindow GDI."""
    win.update_idletasks()
    win.update()
    time.sleep(0.4)
    hwnd = win.winfo_id()
    w = max(win.winfo_width(), 950)
    h = max(win.winfo_height(), 650)

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    hdc = user32.GetWindowDC(hwnd)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(memdc, bmp)

    # PrintWindow flag 2 = PW_RENDERFULLCONTENT
    user32.PrintWindow(hwnd, memdc, 2)

    bi = (ctypes.c_byte * 40)()
    ctypes.cast(bi, ctypes.POINTER(ctypes.c_uint32))[0] = 40
    ctypes.cast(bi, ctypes.POINTER(ctypes.c_int32))[1] = w
    ctypes.cast(bi, ctypes.POINTER(ctypes.c_int32))[2] = -h
    ctypes.cast(bi, ctypes.POINTER(ctypes.c_uint16))[6] = 1
    ctypes.cast(bi, ctypes.POINTER(ctypes.c_uint16))[7] = 32

    buf = (ctypes.c_byte * (w * h * 4))()
    gdi32.GetDIBits(memdc, bmp, 0, h, buf, bi, 0)

    img = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1)
    img.convert("RGB").save(dest_path)
    print(f"Captured: {dest_path.name} ({w}x{h})")

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(hwnd, hdc)


def seed_phase9_data(db_path: Path):
    """Seed comprehensive families and pilgrims for Phase 9 demonstration."""
    init_db(db_path)
    today = datetime.date.today().strftime("%Y-%m-%d")

    # Family 1: Ready for Manual Booking
    f1 = {
        "family_name": "Tirumala Seva Trust - Srinivasa Family",
        "contact_name": "Sri Raghavan Iyengar",
        "phone": "9845012345",
        "donation_amount": 20000.0,
        "booking_type": "Advance",
        "preferred_date": today,
        "status": "Pending",
        "payment_status": "Paid",
        "priority": "Urgent",
    }
    p1 = [
        {"full_name": "Raghavan Iyengar", "age": 52, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Padmavathi Iyengar", "age": 48, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]
    f1_id = add_family_with_pilgrims(f1, p1, db_path=db_path)
    r1 = calculate_booking_readiness(f1, p1, [])
    update_family_readiness(f1_id, r1["status"], r1["score"], r1["missing_items"], db_path=db_path)

    # Add mock documents for Family 1
    doc_dir = REPO_ROOT / "data" / "documents" / str(f1_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    doc_file = doc_dir / "aadhaar_cards_combined.pdf"
    doc_file.write_bytes(b"%PDF-1.4 mock content for preview and testing verification")
    add_family_document(f1_id, "aadhaar_cards_combined.pdf", str(doc_file), "application/pdf", len(b"%PDF-1.4 mock content"), "mock_sha256", db_path=db_path)

    # Family 2: Incomplete profile (missing ID proofs)
    f2 = {
        "family_name": "Kalyanam Devotees Group",
        "contact_name": "Venkatesh Rao",
        "phone": "9810011223",
        "donation_amount": 30000.0,
        "booking_type": "Current",
        "preferred_date": today,
        "status": "Pending",
        "payment_status": "Pending",
        "priority": "High",
    }
    p2 = [
        {"full_name": "Venkatesh Rao", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": ""},
        {"full_name": "Lakshmi Rao", "age": 42, "gender": "Female", "id_proof_type": "", "id_proof_last4": "9988"},
    ]
    f2_id = add_family_with_pilgrims(f2, p2, db_path=db_path)
    r2 = calculate_booking_readiness(f2, p2, [])
    update_family_readiness(f2_id, r2["status"], r2["score"], r2["missing_items"], db_path=db_path)

    # Family 3: Completed / Booked
    f3 = {
        "family_name": "Varadarajan Pilgrims Roster",
        "contact_name": "Sundar Varadarajan",
        "phone": "9822233344",
        "donation_amount": 10000.0,
        "booking_type": "Advance",
        "preferred_date": today,
        "status": "Booked",
        "payment_status": "Paid",
        "priority": "Normal",
    }
    p3 = [
        {"full_name": "Sundar Varadarajan", "age": 60, "gender": "Male", "id_proof_type": "Passport", "id_proof_last4": "K901"},
    ]
    f3_id = add_family_with_pilgrims(f3, p3, db_path=db_path)
    r3 = calculate_booking_readiness(f3, p3, [])
    update_family_readiness(f3_id, r3["status"], r3["score"], r3["missing_items"], db_path=db_path)

    return f1_id


def capture_all():
    if demo_db.exists():
        try:
            demo_db.unlink()
        except Exception:
            pass

    f1_id = seed_phase9_data(demo_db)

    root = tk.Tk()
    root.title("SRIVANI BOOKING MANAGER — Phase 9 Fast Booking Engine")
    root.geometry("1150x750")

    class MockApp:
        def __init__(self, db):
            self.db_path = db

        def show_status(self, msg, color=None):
            print(f"[STATUS] {msg}")

        def open_family_workspace(self, family_id):
            ManualBookingWorkspaceDialog(root, family_id=family_id)

        def open_document_manager(self, family_id):
            DocumentManagementDialog(root, family_id=family_id)

    app = MockApp(demo_db)

    # 1. Fast Booking Dashboard View
    dashboard_frame = FastBookingDashboardView(root, app)
    dashboard_frame.pack(fill=tk.BOTH, expand=True)
    dashboard_frame.refresh_dashboard()
    root.update_idletasks()
    root.update()
    grab_window(root, SCREENSHOTS_DIR / "phase9_fast_booking_dashboard.png")
    dashboard_frame.pack_forget()

    # 2. Booking History View
    history_frame = BookingHistoryFrame(root, app)
    history_frame.pack(fill=tk.BOTH, expand=True)
    history_frame.filter_history()
    root.update_idletasks()
    root.update()
    grab_window(root, SCREENSHOTS_DIR / "phase9_booking_history.png")
    history_frame.pack_forget()

    # 3. Manual Booking Workspace Dialog
    ws_dialog = ManualBookingWorkspaceDialog(root, family_id=f1_id)
    ws_dialog.geometry("1020x720")
    ws_dialog.update_idletasks()
    ws_dialog.update()
    grab_window(ws_dialog, SCREENSHOTS_DIR / "phase9_manual_booking_workspace.png")

    # 4. Document Management Dialog
    doc_dialog = DocumentManagementDialog(root, family_id=f1_id)
    doc_dialog.geometry("820x560")
    doc_dialog.update_idletasks()
    doc_dialog.update()
    grab_window(doc_dialog, SCREENSHOTS_DIR / "phase9_document_management.png")

    ws_dialog.destroy()
    doc_dialog.destroy()
    root.destroy()
    print("All Phase 9 screenshots captured successfully!")


if __name__ == "__main__":
    capture_all()
