"""
SRIVANI BOOKING MANAGER — Dashboard Data Import Feature Screenshots Capture
Captures:
1. Modified Dashboard showing the new "📥 Import Dataset" button in top header area near Reports & Export,
   the 6 updated statistics cards, and toolbar button.
2. The dedicated "DatasetImportDialog" modal opened with sample file preview, column mapping,
   validation breakdown, and duplicate options.
"""
import os
import sys
import time
import ctypes
from pathlib import Path
from PIL import Image
import tkinter as tk

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import App
from data_import_view import DatasetImportDialog

SCREENSHOTS_DIR = REPO_ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR = Path(r"C:\Users\nagas\.gemini\antigravity\brain\a463c67c-ba1b-42be-83f5-24188fe4dae5")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def grab_window(win, dest_path: Path):
    """Capture native Windows window using PrintWindow GDI."""
    win.update_idletasks()
    win.update()
    time.sleep(0.4)
    hwnd = win.winfo_id()
    w = max(win.winfo_width(), 1100)
    h = max(win.winfo_height(), 720)

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    hdc = user32.GetWindowDC(hwnd)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(memdc, bmp)

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
    rgb_img = img.convert("RGB")
    rgb_img.save(dest_path)
    # Also copy to artifacts dir
    artifact_copy = ARTIFACTS_DIR / dest_path.name
    rgb_img.save(artifact_copy)
    print(f"Captured & saved: {dest_path.name} ({w}x{h})")

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(hwnd, hdc)


def main():
    app = App(require_auth=False)
    app.geometry("1280x820+40+40")
    app.update()

    # 1. Capture Modified Dashboard with "📥 Import Dataset" button in header & toolbar
    app.on_nav_click("dashboard")
    app.refresh()
    time.sleep(0.6)
    grab_window(app, SCREENSHOTS_DIR / "dashboard_with_import_button.png")

    # Create a realistic sample dataset file to display inside the modal
    sample_csv = REPO_ROOT / "data" / "sample_preview_devotees.csv"
    sample_csv.write_text(
        "Family ID,Family Name,Pilgrim Name,Mobile Number,Age,Gender,City,Donation Amount,Preferred Date\n"
        "FAM-SRI01,Srinivasa Nilayam,Venkateswarlu Naidu,9848011223,54,Male,Tirupati,20000,2026-06-15\n"
        "FAM-SRI01,Srinivasa Nilayam,Padmavati Naidu,9848011223,48,Female,Tirupati,20000,2026-06-15\n"
        "FAM-SRI02,Kalyan Kutumbam,Kalyan Chakravarthy,9849033445,42,Male,Hyderabad,10000,2026-06-18\n"
        "FAM-SRI03,Govinda Bhaktas,Govinda Rao,9840012345,60,Male,Chennai,10000,2026-06-20\n"
        "FAM-SRI04,Anand Trust,Anand Kumar,9888877777,35,Male,Bengaluru,10000,2026-06-22\n",
        encoding="utf-8",
    )

    # 2. Open Dedicated Import Modal with pre-loaded dataset
    modal = DatasetImportDialog(app, on_success_callback=app.refresh, file_path=sample_csv)
    modal.geometry("1080x740+140+80")
    modal.update_idletasks()
    modal.update()
    time.sleep(0.6)
    grab_window(modal, SCREENSHOTS_DIR / "dashboard_dataset_import_modal.png")

    modal.destroy()
    if sample_csv.exists():
        sample_csv.unlink()

    app.destroy()
    print("Dashboard data import screenshots captured successfully!")


if __name__ == "__main__":
    main()
