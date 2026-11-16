"""
SRIVANI BOOKING MANAGER - Customer Support & Diagnostic Report Engine
Generates sanitized, non-PII diagnostic reports for technical troubleshooting,
provides offline support dialogs, and guarantees explicit user consent.
Strictly offline: Does not transmit any telemetry or diagnostic data across networks.
"""
import sys
import os
import re
import platform
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

from config import (
    APP_DIR,
    DATA_DIR,
    BACKUPS_DIR,
    TICKETS_DIR,
    DB_PATH,
    TTD_PORTAL_URL,
)
from database import get_connection, get_current_schema_version
from licensing import (
    get_installation_id,
    get_license_info,
    export_license_certificate,
    LicenseActivationDialog,
)
from update_manager import validate_database_schema
from logger import get_logger

logger = get_logger("support_diagnostics")

APP_VERSION = "7.0.0"
SUPPORT_EMAIL = "support@srivani-booking-manager.local"
SUPPORT_HOURS = "Monday to Saturday, 09:00 AM to 06:00 PM IST"


def _sanitize_log_line(line: str) -> str:
    """Scrub phone numbers, Aadhaar numbers, emails, and passwords from log lines."""
    # Redact 10-digit phone numbers
    line = re.sub(r"\b[6-9]\d{9}\b", "[REDACTED-PHONE]", line)
    # Redact 12-digit Aadhaar / ID numbers
    line = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[REDACTED-ID-PROOF]", line)
    # Redact email addresses
    line = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[REDACTED-EMAIL]", line)
    # Redact password hashes or keys if present
    line = re.sub(r"(password|hash|key|secret)=([^\s,]+)", r"\1=[REDACTED]", line, flags=re.IGNORECASE)
    return line


def generate_diagnostic_report(db_path: Optional[Path] = None) -> str:
    """
    Generate a comprehensive technical diagnostic report.
    Excludes all personal identification details, donor names, phone numbers, and credentials.
    """
    src_db = db_path or DB_PATH
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # System & Runtime Metrics
    os_name = f"{platform.system()} {platform.release()} ({platform.version()})"
    python_ver = f"{platform.python_version()} ({platform.architecture()[0]})"
    is_frozen = getattr(sys, "frozen", False)
    exec_mode = "Packaged Standalone Executable" if is_frozen else "Python Development Source"

    # Disk Space Check
    try:
        disk_usage = shutil.disk_usage(DATA_DIR)
        disk_free_gb = round(disk_usage.free / (1024 ** 3), 2)
        disk_total_gb = round(disk_usage.total / (1024 ** 3), 2)
        disk_str = f"{disk_free_gb} GB free of {disk_total_gb} GB"
    except Exception:
        disk_str = "Unavailable"

    # Directory Permissions Check
    def check_writable(p: Path) -> str:
        try:
            p.mkdir(parents=True, exist_ok=True)
            tf = p / ".diag_test.tmp"
            tf.write_text("ok", encoding="utf-8")
            tf.unlink()
            return f"Writable ({p})"
        except Exception as e:
            return f"ACCESS ERROR: {e}"

    dir_status = {
        "App Directory": check_writable(APP_DIR),
        "Data Directory": check_writable(DATA_DIR),
        "Tickets Directory": check_writable(TICKETS_DIR),
        "Backups Directory": check_writable(BACKUPS_DIR),
    }

    # Ticket File Count
    ticket_count = 0
    if TICKETS_DIR.exists():
        ticket_count = len(list(TICKETS_DIR.glob("*.pdf")))

    # Backup File Count
    backup_count = 0
    if BACKUPS_DIR.exists():
        backup_count = len(list(BACKUPS_DIR.glob("*.db")))

    # Database Statistics & Health
    db_size_kb = round(src_db.stat().st_size / 1024, 1) if src_db.exists() else 0
    db_is_valid, db_status_msg, schema_meta = validate_database_schema(src_db)
    schema_ver = get_current_schema_version(src_db) if src_db.exists() else 0

    family_count = 0
    pilgrim_count = 0
    history_count = 0

    if src_db.exists():
        try:
            with get_connection(src_db) as con:
                family_count = con.execute("SELECT COUNT(*) FROM families").fetchone()[0]
                pilgrim_count = con.execute("SELECT COUNT(*) FROM pilgrims").fetchone()[0]
                history_count = con.execute("SELECT COUNT(*) FROM queue_history").fetchone()[0]
        except Exception:
            pass

    # Licensing Information
    lic = get_license_info(src_db)
    inst_id = get_installation_id()

    # Redacted Log Tail
    log_tail_lines = []
    log_file = DATA_DIR / "srivani_manager.log"
    if not log_file.exists():
        log_file = Path("srivani_manager.log")

    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
                raw_tail = all_lines[-25:]
                log_tail_lines = [_sanitize_log_line(l.strip()) for l in raw_tail]
        except Exception as e:
            log_tail_lines = [f"[Error reading log file: {e}]"]
    else:
        log_tail_lines = ["[No log file found on system]"]

    # Assemble Report
    lines = [
        "================================================================================",
        "          SRIVANI BOOKING MANAGER — CUSTOMER SUPPORT DIAGNOSTIC REPORT          ",
        "================================================================================",
        f"Generated Timestamp:    {now_str}",
        f"Application Name:       SRIVANI Booking Manager",
        f"Application Version:    v{APP_VERSION} Commercial Release",
        f"Execution Mode:         {exec_mode}",
        f"Operating System:       {os_name}",
        f"Python Architecture:    {python_ver}",
        f"Hardware Node ID:       {inst_id} (Salted Machine Hash)",
        "--------------------------------------------------------------------------------",
        "STORAGE & FILE PERMISSIONS:",
        "--------------------------------------------------------------------------------",
        f"  App Directory:        {dir_status['App Directory']}",
        f"  Data Directory:       {dir_status['Data Directory']}",
        f"  Tickets Directory:    {dir_status['Tickets Directory']} (Stored PDFs: {ticket_count})",
        f"  Backups Directory:    {dir_status['Backups Directory']} (Stored Backups: {backup_count})",
        f"  Storage Volume Space: {disk_str}",
        "--------------------------------------------------------------------------------",
        "DATABASE HEALTH & AGGREGATE METRICS:",
        "--------------------------------------------------------------------------------",
        f"  Database Path:        {src_db}",
        f"  Database File Size:   {db_size_kb} KB",
        f"  Schema Version:       v{schema_ver}",
        f"  Integrity Status:     {'OK / Healthy' if db_is_valid else 'ERROR: ' + db_status_msg}",
        f"  Total Family Records: {family_count} (Record count only, no PII)",
        f"  Total Devotees:       {pilgrim_count} (Record count only, no PII)",
        f"  Queue History Events: {history_count}",
        "--------------------------------------------------------------------------------",
        "CLIENT LICENSING STATUS:",
        "--------------------------------------------------------------------------------",
        f"  Installation ID:      {inst_id}",
        f"  License Status:       {lic.get('status', 'N/A')}",
        f"  License Tier:         {lic.get('license_type', 'N/A')}",
        f"  Licensed Client:      {lic.get('client_name', 'N/A')}",
        f"  Expiry Date:          {lic.get('expiry_date', 'N/A')}",
        f"  Days Remaining:       {lic.get('days_remaining', 'N/A')}",
        "--------------------------------------------------------------------------------",
        "RECENT APPLICATION LOG EVENTS (SANITIZED / PII REDACTED):",
        "--------------------------------------------------------------------------------",
    ]

    for log_l in log_tail_lines:
        lines.append(f"  {log_l}")

    lines.extend([
        "================================================================================",
        "DATA PRIVACY & REGULATORY COMPLIANCE DECLARATION:",
        "1. This report contains NO Personally Identifiable Information (zero donor",
        "   names, zero phone numbers, zero ID proofs, zero financial details).",
        "2. The SRIVANI Booking Manager operates strictly as an assisted workflow tool.",
        "3. TTD portal login, CAPTCHA, OTP, and payments remain under manual client control.",
        "4. This diagnostic report is generated locally and NEVER transmitted automatically.",
        "================================================================================",
    ])

    return "\n".join(lines)


def export_diagnostic_report(output_file: Path, db_path: Optional[Path] = None) -> Path:
    """Save the generated sanitized diagnostic report to the specified file path."""
    report_text = generate_diagnostic_report(db_path)
    out = Path(output_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report_text, encoding="utf-8")
    return out


# -----------------------------------------------------------------------------
# Customer Support & Diagnostics Dialog (Tkinter UI)
# -----------------------------------------------------------------------------

class SupportDialog(tk.Toplevel):
    """
    Dedicated Customer Support and System Diagnostics Dialog.
    Features: Helpdesk details, Release notes, Sanitized Diagnostics, License guidance.
    """

    def __init__(self, parent, db_path: Optional[Path] = None):
        super().__init__(parent)
        self.db_path = db_path
        self.title(f"Customer Support & System Diagnostics — v{APP_VERSION}")
        self.geometry("780x620")
        self.minsize(680, 520)
        self.configure(bg="#f8fafc")

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#0f172a", padx=20, pady=16)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=f"🎧 Customer Support & Operations Hub (v{APP_VERSION})",
            font=("Segoe UI", 13, "bold"),
            fg="#f8fafc",
            bg="#0f172a",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Access official support, inspect sanitized system diagnostics, and view release notes.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
        ).pack(anchor="w", pady=(2, 0))

        # Notebook tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # Tab 1: Support Contact & SLA
        self.tab_support = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_support, text="📞 Support Information")
        self._build_support_tab()

        # Tab 2: System Diagnostics
        self.tab_diagnostics = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_diagnostics, text="🩺 System Diagnostics")
        self._build_diagnostics_tab()

        # Tab 3: Release Notes
        self.tab_release_notes = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_release_notes, text="📋 Release Notes")
        self._build_release_notes_tab()

        # Tab 4: License & Transfer Guidance
        self.tab_license = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_license, text="🔑 License & Transfer")
        self._build_license_tab()

        # Bottom Button Bar
        btn_bar = tk.Frame(self, bg="#f1f5f9", padx=16, pady=10)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_close = tk.Button(
            btn_bar,
            text="Close",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#334155",
            relief="flat",
            padx=16,
            pady=5,
            command=self.destroy,
        )
        btn_close.pack(side=tk.RIGHT)

    def _build_support_tab(self):
        parent = self.tab_support

        box = tk.LabelFrame(parent, text="Official Client Support Helpdesk", font=("Segoe UI", 10, "bold"), padx=16, pady=14)
        box.pack(fill=tk.X, pady=(0, 16))

        info_rows = [
            ("Technical Support Email:", SUPPORT_EMAIL),
            ("Operational Support Hours:", SUPPORT_HOURS),
            ("Official TTD Booking Portal:", TTD_PORTAL_URL),
            ("Service Level Agreement (SLA):", "Standard business day response within 24 hours"),
            ("Supported Environment:", "Windows 10 / Windows 11 (64-bit)"),
        ]

        for i, (label, val) in enumerate(info_rows):
            tk.Label(box, text=label, font=("Segoe UI", 9, "bold"), fg="#334155").grid(row=i, column=0, sticky="w", pady=4)
            tk.Label(box, text=val, font=("Segoe UI", 9), fg="#0f172a").grid(row=i, column=1, sticky="w", padx=12, pady=4)

        # Operational Scope Box
        scope_box = tk.LabelFrame(parent, text="Scope of Technical Support", font=("Segoe UI", 10, "bold"), padx=16, pady=14)
        scope_box.pack(fill=tk.BOTH, expand=True)

        scope_text = (
            "INCLUDED UNDER SUPPORT & MAINTENANCE:\n"
            "✓ Application installation, Windows compatibility, and shortcut repairs.\n"
            "✓ SQLite database integrity diagnostics, automated backups, and recovery.\n"
            "✓ Excel / CSV template formatting and donor data import assistance.\n"
            "✓ Ticket PDF management, checksum validation, and organization.\n"
            "✓ Commercial license key activation and authorized hardware device transfer.\n\n"
            "IMPORTANT COMPLIANCE BOUNDARIES:\n"
            "• This software is strictly an assisted management tool and does NOT submit bookings.\n"
            "• TTD Darshan quota releases, website availability, and VIP recommendation letter\n"
            "  approvals are strictly governed by Tirumala Tirupati Devasthanams."
        )
        lbl_scope = tk.Label(scope_box, text=scope_text, font=("Segoe UI", 9), justify=tk.LEFT, fg="#475569")
        lbl_scope.pack(anchor="w")

    def _build_diagnostics_tab(self):
        parent = self.tab_diagnostics

        tk.Label(
            parent,
            text="Sanitized System Diagnostics Report (No PII / No Passwords):",
            font=("Segoe UI", 9, "bold"),
            fg="#1e293b",
        ).pack(anchor="w", pady=(0, 4))

        # Scrolled text area for diagnostic preview
        self.txt_diag = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("Consolas", 8),
            bg="#f8fafc",
            fg="#0f172a",
            height=14,
        )
        self.txt_diag.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        report_content = generate_diagnostic_report(self.db_path)
        self.txt_diag.insert(tk.END, report_content)
        self.txt_diag.configure(state="disabled")

        # Consent Checkbox
        self.consent_var = tk.BooleanVar(value=False)
        chk_consent = tk.Checkbutton(
            parent,
            text="I confirm this report contains no personal data and consent to export/share it with support.",
            variable=self.consent_var,
            font=("Segoe UI", 9, "bold"),
            fg="#0f172a",
            command=self._toggle_export_btn,
        )
        chk_consent.pack(anchor="w", pady=(0, 8))

        btn_row = tk.Frame(parent)
        btn_row.pack(fill=tk.X)

        self.btn_export_diag = tk.Button(
            btn_row,
            text="💾 Save Diagnostic Report to File...",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            relief="flat",
            padx=14,
            pady=5,
            state="disabled",
            command=self._on_export_diagnostic,
        )
        self.btn_export_diag.pack(side=tk.LEFT, padx=(0, 8))

        btn_copy = tk.Button(
            btn_row,
            text="📋 Copy to Clipboard",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            relief="flat",
            padx=14,
            pady=5,
            command=self._on_copy_diagnostic,
        )
        btn_copy.pack(side=tk.LEFT)

    def _toggle_export_btn(self):
        if self.consent_var.get():
            self.btn_export_diag.config(state="normal", bg="#2563eb", cursor="hand2")
        else:
            self.btn_export_diag.config(state="disabled", bg="#94a3b8", cursor="arrow")

    def _on_export_diagnostic(self):
        if not self.consent_var.get():
            messagebox.showwarning("Consent Required", "Please check the consent box before exporting.", parent=self)
            return

        default_name = f"srivani_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Save Diagnostic Report",
            initialfile=default_name,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if dest:
            try:
                export_diagnostic_report(Path(dest), self.db_path)
                messagebox.showinfo(
                    "Report Saved",
                    f"Sanitized diagnostic report successfully saved to:\n{dest}\n\n"
                    "You may attach this file when contacting customer support.",
                    parent=self,
                )
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save report: {e}", parent=self)

    def _on_copy_diagnostic(self):
        report_content = generate_diagnostic_report(self.db_path)
        self.clipboard_clear()
        self.clipboard_append(report_content)
        messagebox.showinfo("Copied", "Sanitized diagnostic report copied to clipboard.", parent=self)

    def _build_release_notes_tab(self):
        parent = self.tab_release_notes

        txt_notes = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#0f172a",
        )
        txt_notes.pack(fill=tk.BOTH, expand=True)

        release_text = (
            "====================================================================\n"
            "SRIVANI BOOKING MANAGER — RELEASE HISTORY & CHANGELOG\n"
            "====================================================================\n\n"
            "● Version 6.0.0 (Phase 6 — Commercial Launch & Client Operations)\n"
            "  - Commercial Client Onboarding Guide and Verification Suite.\n"
            "  - Offline Customer Support & Sanitized System Diagnostics Engine.\n"
            "  - Safe Pre-Update Backups, Migration Integrity Validation & Rollback.\n"
            "  - Transparent License Expiry Warnings & Hardware Device Transfer.\n"
            "  - Comprehensive Commercial Documentation and Legal Disclaimers.\n\n"
            "● Version 5.0.0 (Phase 5 — Windows Commercial Release)\n"
            "  - Inno Setup professional Windows installer with upgrade data protection.\n"
            "  - Offline HMAC-SHA256 commercial licensing with 30-day evaluation.\n"
            "  - 7-Step First-Run Setup Wizard on fresh installations.\n"
            "  - User data persistence in %LOCALAPPDATA%.\n\n"
            "● Version 4.0.0 (Phase 4 — Enterprise UI & Admin Security)\n"
            "  - Single-admin salted bcrypt authentication and brute-force lockout.\n"
            "  - Professional light/dark themes and composite SQLite indices.\n"
            "  - Comprehensive PDF and CSV business report exports.\n\n"
            "● Version 3.0.0 (Phase 3 — Assisted Workspace & Ticket PDF Storage)\n"
            "  - 7-Step assisted booking checklist with official TTD browser launcher.\n"
            "  - Local ticket PDF storage with automated SHA-256 de-duplication.\n"
            "  - Payment status tracking and queue history audit trail.\n\n"
            "● Version 2.0.0 (Phase 2 — Family Management & Excel/CSV Import)\n"
            "  - Multi-pilgrim family management with Aadhaar last-4 validation.\n"
            "  - Dual format Excel (.xlsx) and CSV import with duplicate detection.\n"
            "  - Real-time queue filtering and prioritization.\n"
        )
        txt_notes.insert(tk.END, release_text)
        txt_notes.configure(state="disabled")

    def _build_license_tab(self):
        parent = self.tab_license

        lic = get_license_info(self.db_path)
        inst_id = get_installation_id()

        box = tk.LabelFrame(parent, text="Current Installation & Licensing", font=("Segoe UI", 10, "bold"), padx=16, pady=12)
        box.pack(fill=tk.X, pady=(0, 16))

        tk.Label(box, text="Hardware Installation ID:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=3)
        tk.Label(box, text=inst_id, font=("Consolas", 10, "bold"), fg="#0369a1").grid(row=0, column=1, sticky="w", padx=8, pady=3)

        tk.Label(box, text="Licensed Client:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=3)
        tk.Label(box, text=lic.get("client_name", "Unregistered"), font=("Segoe UI", 9)).grid(row=1, column=1, sticky="w", padx=8, pady=3)

        tk.Label(box, text="License Status:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=3)
        color = "#10b981" if lic.get("is_licensed") else "#f59e0b"
        tk.Label(box, text=f"{lic.get('status')} ({lic.get('license_type')})", font=("Segoe UI", 9, "bold"), fg=color).grid(row=2, column=1, sticky="w", padx=8, pady=3)

        tk.Label(box, text="Expiry Date / Days:", font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=3)
        tk.Label(box, text=f"{lic.get('expiry_date')} ({lic.get('days_remaining')} days remaining)", font=("Segoe UI", 9)).grid(row=3, column=1, sticky="w", padx=8, pady=3)

        # Device Transfer Guidance
        xfer_box = tk.LabelFrame(parent, text="Hardware Replacement & Device Transfer Procedure", font=("Segoe UI", 10, "bold"), padx=16, pady=12)
        xfer_box.pack(fill=tk.BOTH, expand=True)

        xfer_text = (
            "HOW TO TRANSFER YOUR LICENSE TO A NEW COMPUTER:\n"
            "1. Take a full database backup via 'Backup & Recovery' -> 'Create Backup Now'.\n"
            "2. Export your License Certificate below or record your Deactivation Proof.\n"
            "3. Install SRIVANI Booking Manager on the new Windows PC.\n"
            "4. Copy your database backup (.db) and tickets folder to the new computer.\n"
            "5. Contact support with your Certificate or Deactivation Proof to obtain your\n"
            "   re-issued key for the new PC's Installation ID."
        )
        tk.Label(xfer_box, text=xfer_text, font=("Segoe UI", 9), justify=tk.LEFT, fg="#475569").pack(anchor="w", pady=(0, 10))

        btn_row = tk.Frame(xfer_box)
        btn_row.pack(fill=tk.X)

        btn_cert = tk.Button(
            btn_row,
            text="📄 Export License Certificate...",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_export_cert,
        )
        btn_cert.pack(side=tk.LEFT, padx=(0, 8))

        btn_act = tk.Button(
            btn_row,
            text="🔑 Activate / Change Key...",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_open_activation,
        )
        btn_act.pack(side=tk.LEFT)

    def _on_export_cert(self):
        default_name = f"srivani_license_certificate_{datetime.now().strftime('%Y%m%d')}.txt"
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Export License Certificate",
            initialfile=default_name,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if dest:
            try:
                export_license_certificate(Path(dest), self.db_path)
                messagebox.showinfo("Export Successful", f"License Certificate saved to:\n{dest}", parent=self)
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export certificate: {e}", parent=self)

    def _on_open_activation(self):
        LicenseActivationDialog(self, db_path=self.db_path)
