"""
SRIVANI BOOKING MANAGER - Automated Analytics Dashboard Screenshot Capture Utility
Populates realistic test data, launches the Analytics Dashboard GUI,
navigates through all operational tabs, and captures high-resolution PNG screenshots.
"""
import os
import sys
import time
import datetime
import ctypes
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageGrab

# Ensure repo root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from database import init_db, get_connection, add_family_with_pilgrims
from analytics_view import AnalyticsDashboardFrame, AnalyticsRuleConfigDialog

SCREENSHOTS_DIR = REPO_ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def populate_demo_database(db_file: Path):
    """Seed comprehensive realistic records for analytics demonstration."""
    init_db(db_file)
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    d3_ago = (today - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    d5_ago = (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    d12_ago = (today - datetime.timedelta(days=12)).strftime("%Y-%m-%d")

    records = [
        # 1. Rao Trust - Booked, Paid, Ticket attached, Complete docs
        (
            {
                "family_name": "Rao Trust & Foundation",
                "contact_name": "Anand Rao",
                "phone": "9876543210",
                "donation_amount": 20000.0,
                "booking_type": "Advance",
                "preferred_date": today_str,
                "status": "Booked",
                "payment_status": "Paid",
                "priority": "Urgent",
                "ticket_pdf_path": str(REPO_ROOT / "data" / "tickets" / "ticket_rao.pdf"),
                "ticket_checksum": "SHA256-RAO-9883",
                "payment_ref": "TXN-RAO-7788",
                "booked_at": f"{today_str} 11:30:00",
                "created_at": f"{yesterday_str} 14:00:00",
            },
            [
                {"full_name": "Anand Rao", "age": 48, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
                {"full_name": "Sunita Rao", "age": 45, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
            ]
        ),
        # 2. Kulkarni Family - In Progress, Imminent date, Paid
        (
            {
                "family_name": "Kulkarni Devotee Group",
                "contact_name": "Vijay Kulkarni",
                "phone": "9812345678",
                "donation_amount": 30000.0,
                "booking_type": "Current",
                "preferred_date": (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                "status": "In progress",
                "payment_status": "Paid",
                "priority": "Urgent",
                "payment_ref": "TXN-KULK-4421",
                "created_at": f"{yesterday_str} 09:15:00",
            },
            [
                {"full_name": "Vijay Kulkarni", "age": 52, "gender": "Male", "id_proof_type": "Passport", "id_proof_last4": "Z981"},
                {"full_name": "Lata Kulkarni", "age": 49, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "4321"},
                {"full_name": "Amit Kulkarni", "age": 22, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "8765"},
            ]
        ),
        # 3. Sharma Pilgrims - Pending, Old (>10d), Incomplete docs
        (
            {
                "family_name": "Sharma Pilgrims Roster",
                "contact_name": "Mohan Sharma",
                "phone": "9870001111",
                "donation_amount": 40000.0,
                "booking_type": "Advance",
                "preferred_date": (today + datetime.timedelta(days=10)).strftime("%Y-%m-%d"),
                "status": "Pending",
                "payment_status": "Pending",
                "priority": "Normal",
                "created_at": f"{d12_ago} 10:00:00",
            },
            [
                {"full_name": "Mohan Sharma", "age": 64, "gender": "Male", "id_proof_type": "Voter ID", "id_proof_last4": ""},  # Missing last-4
                {"full_name": "Radha Sharma", "age": 60, "gender": "Female", "id_proof_type": "", "id_proof_last4": "9999"},     # Missing proof type
                {"full_name": "Gaurav Sharma", "age": 31, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1122"},
                {"full_name": "Pooja Sharma", "age": 28, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "3344"},
            ]
        ),
        # 4. Verma Group - Unavailable, Paid (Potential Refund Review)
        (
            {
                "family_name": "Verma Pilgrim Seva",
                "contact_name": "Sunil Verma",
                "phone": "9845556666",
                "donation_amount": 10000.0,
                "booking_type": "Advance",
                "preferred_date": d3_ago,
                "status": "Unavailable",
                "payment_status": "Paid",
                "priority": "Normal",
                "payment_ref": "TXN-VERMA-REFUND",
                "created_at": f"{d5_ago} 11:00:00",
            },
            [
                {"full_name": "Sunil Verma", "age": 38, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "5566"},
            ]
        ),
        # 5. Reddy Family - Booked, Paid, Missing ticket PDF
        (
            {
                "family_name": "Reddy Devotee Roster",
                "contact_name": "K. V. Reddy",
                "phone": "9849012345",
                "donation_amount": 20000.0,
                "booking_type": "Advance",
                "preferred_date": today_str,
                "status": "Booked",
                "payment_status": "Paid",
                "priority": "High",
                "payment_ref": "TXN-REDDY-9901",
                "booked_at": f"{today_str} 16:00:00",
                "created_at": f"{d3_ago} 08:00:00",
            },
            [
                {"full_name": "K. V. Reddy", "age": 55, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "7788"},
                {"full_name": "Padma Reddy", "age": 50, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "9900"},
            ]
        ),
        # 6. Joshi Trust - Pending, Urgent, date imminent (in 2 days), 100% docs ready
        (
            {
                "family_name": "Joshi Darshan Samithi",
                "contact_name": "Dinesh Joshi",
                "phone": "9823456789",
                "donation_amount": 50000.0,
                "booking_type": "Current",
                "preferred_date": (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
                "status": "Pending",
                "payment_status": "Paid",
                "priority": "Urgent",
                "payment_ref": "TXN-JOSHI-1122",
                "created_at": f"{yesterday_str} 15:30:00",
            },
            [
                {"full_name": "Dinesh Joshi", "age": 60, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "3321"},
                {"full_name": "Kavita Joshi", "age": 56, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "7765"},
                {"full_name": "Rohan Joshi", "age": 26, "gender": "Male", "id_proof_type": "Passport", "id_proof_last4": "T554"},
                {"full_name": "Neha Joshi", "age": 24, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "8812"},
                {"full_name": "Sarita Joshi", "age": 82, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "9934"},
            ]
        ),
        # 7. Iyer Family - Cancelled, Refunded
        (
            {
                "family_name": "Iyer Devotee Trust",
                "contact_name": "Subramanian Iyer",
                "phone": "9841023456",
                "donation_amount": 10000.0,
                "booking_type": "Advance",
                "preferred_date": d5_ago,
                "status": "Cancelled",
                "payment_status": "Refunded",
                "priority": "Low",
                "created_at": f"{d12_ago} 09:00:00",
            },
            [
                {"full_name": "Subramanian Iyer", "age": 67, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "5511"},
            ]
        ),
    ]

    for fam, pilg in records:
        fid = add_family_with_pilgrims(fam, pilg, db_path=db_file)
        with get_connection(db_file) as con:
            sets = []
            vals = []
            for col in ("booked_at", "payment_ref", "ticket_checksum", "ticket_pdf_path", "created_at"):
                if col in fam and fam[col]:
                    sets.append(f"{col} = ?")
                    vals.append(fam[col])
            if sets:
                vals.append(fid)
                con.execute(f"UPDATE families SET {', '.join(sets)} WHERE id = ?", vals)
                con.commit()


def capture_all_screenshots():
    """Run Tkinter GUI window and take PNG snapshots of each analytics view tab."""
    demo_db = REPO_ROOT / "data" / "demo_analytics.db"
    demo_db.parent.mkdir(parents=True, exist_ok=True)
    populate_demo_database(demo_db)

    root = tk.Tk()
    root.title("SRIVANI BOOKING MANAGER — Operational Analytics Suite")
    root.geometry("1100x720")
    root.minsize(1000, 680)

    # Controller mockup
    class DummyApp:
        def __init__(self, db):
            self.db_path = db

    app = DummyApp(demo_db)
    frame = AnalyticsDashboardFrame(root, app, db_path=demo_db)
    frame.pack(fill=tk.BOTH, expand=True)

    # Helper to capture window via native Windows GDI
    def grab_tab(filename: str, target_win=None):
        win = target_win or root
        win.update_idletasks()
        win.update()
        time.sleep(0.3)
        hwnd = win.winfo_id()
        w = win.winfo_width()
        h = win.winfo_height()

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        hdc = user32.GetWindowDC(hwnd)
        memdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        gdi32.SelectObject(memdc, bmp)

        # PrintWindow flag 2 = PW_RENDERFULLCONTENT
        user32.PrintWindow(hwnd, memdc, 2)

        # Build BITMAPINFO structure
        bi = (ctypes.c_byte * 40)()
        ctypes.cast(bi, ctypes.POINTER(ctypes.c_uint32))[0] = 40
        ctypes.cast(bi, ctypes.POINTER(ctypes.c_int32))[1] = w
        ctypes.cast(bi, ctypes.POINTER(ctypes.c_int32))[2] = -h  # top-down DIB
        ctypes.cast(bi, ctypes.POINTER(ctypes.c_uint16))[6] = 1   # planes
        ctypes.cast(bi, ctypes.POINTER(ctypes.c_uint16))[7] = 32  # 32 bpp

        buf = (ctypes.c_byte * (w * h * 4))()
        gdi32.GetDIBits(memdc, bmp, 0, h, buf, bi, 0)

        img = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1)
        dest = SCREENSHOTS_DIR / filename
        img.convert("RGB").save(dest)
        print(f"Captured: {dest} ({w}x{h})")

        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(hwnd, hdc)

    # 1. Performance Tab (Daily Mode)
    frame.notebook.select(frame.tab_performance)
    frame._set_chart_mode("daily")
    grab_tab("phase7_dashboard_daily_performance.png")

    # 2. Performance Tab (Outcomes Donut Mode)
    frame._set_chart_mode("outcomes")
    grab_tab("phase7_booking_outcomes_donut.png")

    # 3. Queue Intelligence Tab
    frame.notebook.select(frame.tab_queue)
    grab_tab("phase7_queue_intelligence.png")

    # 4. Family Analytics Tab
    frame.notebook.select(frame.tab_family)
    grab_tab("phase7_family_analytics.png")

    # 5. Payment Analytics Tab
    frame.notebook.select(frame.tab_payments)
    grab_tab("phase7_payment_analytics.png")

    # 6. Document Compliance Tab
    frame.notebook.select(frame.tab_documents)
    grab_tab("phase7_document_compliance.png")

    # 7. Operational Insights & Queue Order Tab
    frame.notebook.select(frame.tab_ops)
    grab_tab("phase7_operational_intelligence.png")

    # 8. Rule Configuration Dialog
    dialog = AnalyticsRuleConfigDialog(root, demo_db)
    grab_tab("phase7_rule_configuration_modal.png", target_win=dialog)
    dialog.destroy()

    root.destroy()
    print("All screenshots successfully captured!")


if __name__ == "__main__":
    capture_all_screenshots()
