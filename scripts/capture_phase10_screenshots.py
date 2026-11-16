"""
SRIVANI BOOKING MANAGER - Data Cleanup & Dataset Import Screenshots Capture Utility
Captures high-resolution PNG screenshots of:
1. Clean Empty Dashboard (Zero stats, onboarding guide, Add Family / Import shortcuts)
2. Data Import View (File drop zone, column mapping, validation breakdown, duplicate policies)
3. Mock Data Cleanup Modal (Safe scanner & audit trail)
"""
import os
import sys
import time
import ctypes
from pathlib import Path
import tkinter as tk
from PIL import Image

# Ensure repo root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import config
from app import App
from data_import_view import DataImportView
from data_cleanup import DataCleanupDialog

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
    app.geometry("1280x800+40+40")
    app.update()

    # 1. Capture Clean Empty Dashboard (with zero stats and onboarding actions)
    app.show_view("dashboard")
    app.refresh()
    time.sleep(0.5)
    grab_window(app, SCREENSHOTS_DIR / "phase10_clean_dashboard.png")

    # 2. Capture Data Import Wizard View
    app.show_view("data_import")
    app.refresh()
    time.sleep(0.5)
    grab_window(app, SCREENSHOTS_DIR / "phase10_data_import_wizard.png")

    # 3. Capture Fast Booking Preparation Clean Dashboard
    app.show_view("preparation_dashboard")
    app.refresh()
    time.sleep(0.5)
    grab_window(app, SCREENSHOTS_DIR / "phase10_preparation_clean_dashboard.png")

    app.destroy()
    print("All Phase 10 screenshots captured successfully!")


if __name__ == "__main__":
    main()
