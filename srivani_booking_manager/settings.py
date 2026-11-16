"""
SRIVANI BOOKING MANAGER - Application Settings Management
Provides persistent configuration in SQLite, custom storage locations,
theming choices, and a comprehensive Settings modal dialog.
"""
import sys
import os
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import (
    APP_DIR,
    DATA_DIR,
    BACKUPS_DIR,
    TICKETS_DIR,
    DB_PATH,
    TTD_PORTAL_URL,
)
from database import get_connection
from logger import get_logger
from auth import session, change_admin_password, update_admin_profile
from themes import apply_theme, get_theme_palette, get_current_theme_name
from licensing import (
    get_installation_id,
    get_license_info,
    LicenseActivationDialog,
    activate_trial_license,
    export_license_certificate,
    deactivate_license_for_transfer,
)
from support_diagnostics import SupportDialog
from client_verification import run_full_client_verification, format_verification_report

logger = get_logger("settings")

APP_VERSION = "7.0.0"

DEFAULT_SETTINGS = {
    "theme": "light",
    "backup_dir": str(BACKUPS_DIR),
    "ticket_dir": str(TICKETS_DIR),
    "export_dir": str(DATA_DIR / "exports"),
    "auto_backup": "true",
    "session_lock_minutes": "30",
}

def init_settings(db_path: Optional[Path] = None):
    """Ensure the app_settings table exists and default keys are populated."""
    with get_connection(db_path) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for key, val in DEFAULT_SETTINGS.items():
            con.execute("""
            INSERT OR IGNORE INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """, (key, val, now_str))
        con.commit()

def get_setting(key: str, default: Optional[str] = None, db_path: Optional[Path] = None) -> str:
    """Retrieve a setting string value by key."""
    init_settings(db_path)
    fallback = default if default is not None else DEFAULT_SETTINGS.get(key, "")
    try:
        with get_connection(db_path) as con:
            row = con.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            if row:
                return row["value"]
    except Exception as e:
        logger.error(f"Error fetching setting '{key}': {e}")
    return fallback

def set_setting(key: str, value: str, db_path: Optional[Path] = None) -> bool:
    """Insert or update a setting value."""
    init_settings(db_path)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_connection(db_path) as con:
            con.execute("""
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (key, str(value), now_str))
            con.commit()
        logger.info(f"Setting updated: {key} = {value}")
        return True
    except Exception as e:
        logger.error(f"Error saving setting '{key}': {e}")
        return False

def get_all_settings(db_path: Optional[Path] = None) -> Dict[str, str]:
    """Retrieve all current application settings."""
    init_settings(db_path)
    result = dict(DEFAULT_SETTINGS)
    try:
        with get_connection(db_path) as con:
            rows = con.execute("SELECT key, value FROM app_settings").fetchall()
            for row in rows:
                result[row["key"]] = row["value"]
    except Exception as e:
        logger.error(f"Error retrieving all settings: {e}")
    return result

# ---------------------------------------------------------
# Settings Dialog (Tkinter)
# ---------------------------------------------------------

class SettingsDialog(tk.Toplevel):
    """Comprehensive Tabbed Settings dialog for Admin Profile, Storage, Themes, and About."""

    def __init__(self, parent, db_path: Optional[Path] = None, on_settings_saved=None):
        super().__init__(parent)
        self.db_path = db_path
        self.on_settings_saved = on_settings_saved
        self.parent = parent

        self.title("Application Settings & Preferences - SRIVANI BOOKING MANAGER")
        self.geometry("640x540")
        self.minsize(580, 480)
        self.configure(bg="#f8fafc")

        self.transient(parent)
        self.grab_set()

        self.settings = get_all_settings(self.db_path)
        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#1e293b", padx=20, pady=14)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="⚙️ Application Settings",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Manage appearance, custom storage paths, admin security, and system status.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(2, 0))

        # Notebook tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=12)

        # Tab 1: Appearance & General
        self.tab_appearance = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_appearance, text="🎨 Appearance & General")
        self._build_appearance_tab()

        # Tab 2: Storage & File Paths
        self.tab_storage = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_storage, text="📁 Storage & Paths")
        self._build_storage_tab()

        # Tab 3: Admin Security
        self.tab_security = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_security, text="🔒 Admin Security")
        self._build_security_tab()

        # Tab 4: Client Licensing
        self.tab_licensing = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_licensing, text="🔑 Client Licensing")
        self._build_licensing_tab()

        # Tab 5: About & Compliance
        self.tab_about = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(self.tab_about, text="ℹ️ About & Version")
        self._build_about_tab()

        # Bottom action buttons
        btn_bar = tk.Frame(self, bg="#f1f5f9", padx=16, pady=10)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_cancel = tk.Button(
            btn_bar,
            text="Close",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#334155",
            relief="flat",
            padx=14,
            pady=5,
            command=self.destroy,
        )
        btn_cancel.pack(side=tk.LEFT)

        btn_save = tk.Button(
            btn_bar,
            text="💾 Save Preferences",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=5,
            cursor="hand2",
            command=self._on_save,
        )
        btn_save.pack(side=tk.RIGHT)

    def _build_appearance_tab(self):
        parent = self.tab_appearance

        tk.Label(parent, text="Theme Mode:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 2))
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        
        theme_frame = tk.Frame(parent)
        theme_frame.grid(row=1, column=0, sticky="w", pady=(0, 14))

        tk.Radiobutton(theme_frame, text="☀️ Modern Light (Default)", variable=self.theme_var, value="light", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 16))
        tk.Radiobutton(theme_frame, text="🌙 Slate Dark", variable=self.theme_var, value="dark", font=("Segoe UI", 9)).pack(side=tk.LEFT)

        tk.Label(parent, text="Session Inactivity Timeout (minutes):", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(4, 2))
        self.timeout_var = tk.StringVar(value=self.settings.get("session_lock_minutes", "30"))
        spin_timeout = ttk.Spinbox(parent, from_=5, to=120, textvariable=self.timeout_var, width=10)
        spin_timeout.grid(row=3, column=0, sticky="w", pady=(0, 14))

        self.auto_backup_var = tk.BooleanVar(value=(self.settings.get("auto_backup", "true").lower() == "true"))
        chk_backup = tk.Checkbutton(
            parent,
            text="Automatically generate a local database backup before any restore or major change",
            variable=self.auto_backup_var,
            font=("Segoe UI", 9),
        )
        chk_backup.grid(row=4, column=0, sticky="w", pady=(4, 10))

    def _build_storage_tab(self):
        parent = self.tab_storage

        # Ticket PDFs Directory
        tk.Label(parent, text="Ticket PDFs Folder:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 2))
        row0 = tk.Frame(parent)
        row0.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.ent_ticket_dir = ttk.Entry(row0, width=50)
        self.ent_ticket_dir.insert(0, self.settings.get("ticket_dir", str(TICKETS_DIR)))
        self.ent_ticket_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row0, text="Browse...", font=("Segoe UI", 8), command=lambda: self._browse_dir(self.ent_ticket_dir)).pack(side=tk.RIGHT)

        # Database Backups Directory
        tk.Label(parent, text="Database Backups Folder:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(4, 2))
        row1 = tk.Frame(parent)
        row1.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.ent_backup_dir = ttk.Entry(row1, width=50)
        self.ent_backup_dir.insert(0, self.settings.get("backup_dir", str(BACKUPS_DIR)))
        self.ent_backup_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row1, text="Browse...", font=("Segoe UI", 8), command=lambda: self._browse_dir(self.ent_backup_dir)).pack(side=tk.RIGHT)

        # Reports Export Directory
        tk.Label(parent, text="Default CSV/PDF Exports Folder:", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, sticky="w", pady=(4, 2))
        row2 = tk.Frame(parent)
        row2.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        self.ent_export_dir = ttk.Entry(row2, width=50)
        self.ent_export_dir.insert(0, self.settings.get("export_dir", str(DATA_DIR / "exports")))
        self.ent_export_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row2, text="Browse...", font=("Segoe UI", 8), command=lambda: self._browse_dir(self.ent_export_dir)).pack(side=tk.RIGHT)

    def _browse_dir(self, entry_widget: ttk.Entry):
        chosen = filedialog.askdirectory(parent=self, title="Select Directory", initialdir=entry_widget.get())
        if chosen:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, str(Path(chosen).resolve()))

    def _build_security_tab(self):
        parent = self.tab_security

        tk.Label(parent, text="Current Admin Account:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 2))
        admin_name = session.username
        tk.Label(parent, text=f"Username: {admin_name}", font=("Segoe UI", 9), fg="#475569").grid(row=1, column=0, sticky="w", pady=(0, 6))

        tk.Label(parent, text="Display Name:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(4, 2))
        self.ent_disp_name = ttk.Entry(parent, width=32)
        self.ent_disp_name.insert(0, session.display_name)
        self.ent_disp_name.grid(row=3, column=0, sticky="w", pady=(0, 12))

        # Password change separator
        sep = ttk.Separator(parent, orient=tk.HORIZONTAL)
        sep.grid(row=4, column=0, sticky="ew", pady=(4, 12))

        tk.Label(parent, text="Change Admin Password (leave blank if unchanged):", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=(2, 6))

        tk.Label(parent, text="Current Password:", font=("Segoe UI", 8)).grid(row=6, column=0, sticky="w", pady=(2, 1))
        self.ent_old_pwd = ttk.Entry(parent, width=28, show="*")
        self.ent_old_pwd.grid(row=7, column=0, sticky="w", pady=(0, 6))

        tk.Label(parent, text="New Password (min 6 characters):", font=("Segoe UI", 8)).grid(row=8, column=0, sticky="w", pady=(2, 1))
        self.ent_new_pwd = ttk.Entry(parent, width=28, show="*")
        self.ent_new_pwd.grid(row=9, column=0, sticky="w", pady=(0, 6))

        tk.Label(parent, text="Confirm New Password:", font=("Segoe UI", 8)).grid(row=10, column=0, sticky="w", pady=(2, 1))
        self.ent_confirm_pwd = ttk.Entry(parent, width=28, show="*")
        self.ent_confirm_pwd.grid(row=11, column=0, sticky="w", pady=(0, 6))

    def _build_licensing_tab(self):
        parent = self.tab_licensing
        inst_id = get_installation_id()
        info = get_license_info(self.db_path)

        tk.Label(parent, text="Software License & Machine Activation", font=("Segoe UI", 11, "bold"), fg="#1e293b").pack(anchor="w", pady=(0, 6))

        tk.Label(parent, text="Machine Installation ID:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        row_id = tk.Frame(parent)
        row_id.pack(fill=tk.X, pady=(2, 8))

        ent_id = ttk.Entry(row_id, font=("Segoe UI", 9, "bold"))
        ent_id.insert(0, inst_id)
        ent_id.config(state="readonly")
        ent_id.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_copy = tk.Button(row_id, text="📋 Copy ID", font=("Segoe UI", 8), command=lambda: self._copy_id(inst_id))
        btn_copy.pack(side=tk.RIGHT)

        # Status Card Frame
        card = tk.LabelFrame(parent, text=" Current License Status ", font=("Segoe UI", 9, "bold"), padx=12, pady=10)
        card.pack(fill=tk.BOTH, expand=True, pady=(6, 10))

        status_fg = "#16a34a" if info["status"] == "ACTIVE" else "#dc2626"
        tk.Label(card, text=f"• License State: {info['status']}", font=("Segoe UI", 9, "bold"), fg=status_fg).pack(anchor="w", pady=2)
        tk.Label(card, text=f"• Registered Client: {info['client_name']}", font=("Segoe UI", 9)).pack(anchor="w", pady=2)
        tk.Label(card, text=f"• License Tier: {info['license_type']}", font=("Segoe UI", 9)).pack(anchor="w", pady=2)
        tk.Label(card, text=f"• Expiry Date: {info['expiry_date']}", font=("Segoe UI", 9)).pack(anchor="w", pady=2)
        if info["license_type"] == "TRIAL" or info.get("days_remaining", 9999) <= 30:
            rem_fg = "#d97706" if info.get("days_remaining", 0) <= 14 else "#475569"
            tk.Label(card, text=f"• Days Remaining: {info['days_remaining']} day(s)", font=("Segoe UI", 9, "bold"), fg=rem_fg).pack(anchor="w", pady=2)

        if info.get("warning_message"):
            warn_lbl = tk.Label(
                card,
                text=f"⚠️ {info['warning_message']}",
                font=("Segoe UI", 8, "italic"),
                fg="#b45309",
                wraplength=480,
                justify=tk.LEFT,
            )
            warn_lbl.pack(anchor="w", pady=(4, 0))

        # Action Buttons
        btn_box = tk.Frame(parent)
        btn_box.pack(fill=tk.X, pady=(0, 6))

        tk.Button(
            btn_box,
            text="✨ Enter / Activate Commercial Key...",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._open_license_dialog,
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            btn_box,
            text="📄 Export Certificate...",
            font=("Segoe UI", 8),
            bg="#e2e8f0",
            fg="#1e293b",
            relief="flat",
            padx=10,
            pady=5,
            command=self._export_certificate,
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            btn_box,
            text="🔄 Deactivate for Transfer...",
            font=("Segoe UI", 8),
            bg="#fef2f2",
            fg="#991b1b",
            relief="flat",
            padx=10,
            pady=5,
            command=self._deactivate_for_transfer,
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_box,
            text="⏱️ 30-Day Eval",
            font=("Segoe UI", 8),
            bg="#e2e8f0",
            fg="#334155",
            relief="flat",
            padx=10,
            pady=5,
            command=self._start_evaluation,
        ).pack(side=tk.RIGHT)

    def _export_certificate(self):
        default_name = f"srivani_license_certificate_{datetime.datetime.now().strftime('%Y%m%d')}.txt"
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Export License Certificate",
            initialfile=default_name,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if dest:
            try:
                export_license_certificate(Path(dest), self.db_path)
                messagebox.showinfo("Export Successful", f"License Certificate exported to:\n{dest}", parent=self)
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export certificate: {e}", parent=self)

    def _deactivate_for_transfer(self):
        confirm = messagebox.askyesno(
            "Confirm Device Deactivation",
            "Are you sure you want to deactivate the license on this device for transfer to another PC?\n\n"
            "• Your family records, devotees, and ticket files will remain 100% intact.\n"
            "• You will receive a signed Deactivation Proof code to provide to support.\n\n"
            "Proceed with deactivation?",
            parent=self,
        )
        if not confirm:
            return

        ok, msg, details = deactivate_license_for_transfer(self.db_path)
        if ok:
            messagebox.showinfo(
                "License Deactivated for Transfer",
                f"{msg}\n\n"
                f"Client: {details.get('client_name')}\n"
                f"Proof Code: {details.get('deactivation_proof')}\n\n"
                "Save this proof code. You can provide it to vendor support to re-issue "
                "a license key for your new computer.",
                parent=self,
            )
            self._on_license_updated()
        else:
            messagebox.showwarning("Deactivation", msg, parent=self)

    def _copy_id(self, inst_id: str):
        self.clipboard_clear()
        self.clipboard_append(inst_id)
        messagebox.showinfo("Copied", f"Installation ID copied to clipboard:\n{inst_id}", parent=self)

    def _open_license_dialog(self):
        LicenseActivationDialog(self, db_path=self.db_path, on_success=self._on_license_updated)

    def _start_evaluation(self):
        ok, msg = activate_trial_license("Evaluation Client", days=30, db_path=self.db_path)
        messagebox.showinfo("Evaluation Status", msg, parent=self)
        self._on_license_updated()

    def _on_license_updated(self):
        # Refresh current tab view
        for child in self.tab_licensing.winfo_children():
            child.destroy()
        self._build_licensing_tab()

    def _build_about_tab(self):
        parent = self.tab_about

        tk.Label(parent, text="SRIVANI BOOKING MANAGER", font=("Segoe UI", 12, "bold"), fg="#1e3a8a").pack(anchor="w", pady=(2, 2))
        tk.Label(parent, text=f"Version: {APP_VERSION} (Commercial Client Release)", font=("Segoe UI", 9, "bold"), fg="#475569").pack(anchor="w")

        info_box = tk.Text(parent, height=9, width=65, font=("Segoe UI", 8), bg="#f8fafc", relief="solid", borderwidth=1, padx=8, pady=6)
        info_box.pack(fill=tk.BOTH, expand=True, pady=(6, 8))

        about_text = (
            f"Software: SRIVANI BOOKING MANAGER Commercial Suite\n"
            f"Target OS: Microsoft Windows 10 / 11 (64-bit)\n"
            f"Architecture: Python backend + SQLite Database + Tkinter GUI\n"
            f"Python Runtime: {sys.version.split()[0]} ({sys.platform})\n"
            f"Application Directory: {APP_DIR}\n"
            f"Local Data Directory: {DATA_DIR}\n\n"
            f"--- OFFICIAL TTD PORTAL COMPLIANCE NOTICE ---\n"
            f"Official Website: {TTD_PORTAL_URL}\n"
            f"1. This software is an administrative assistant for managing pilgrim rosters.\n"
            f"2. All TTD login sessions, CAPTCHA solutions, SMS OTP verifications, and payment "
            f"authorizations must be manually completed by the client.\n"
            f"3. This system never stores banking credentials, passwords, OTPs, or UPI PINs.\n"
            f"4. This system does not bypass quotas, queues, or website protection mechanisms.\n"
        )
        info_box.insert(tk.END, about_text)
        info_box.config(state="disabled")

        # Operations & Diagnostic Tools Box
        ops_box = tk.Frame(parent)
        ops_box.pack(fill=tk.X)

        tk.Button(
            ops_box,
            text="🎧 Support & Helpdesk Hub...",
            font=("Segoe UI", 9, "bold"),
            bg="#0369a1",
            fg="white",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._open_support_dialog,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            ops_box,
            text="🔍 Run Environment Audit",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._run_env_audit,
        ).pack(side=tk.LEFT)

    def _open_support_dialog(self):
        SupportDialog(self, db_path=self.db_path)

    def _run_env_audit(self):
        res = run_full_client_verification(db_path=self.db_path)
        report = format_verification_report(res)
        
        dlg = tk.Toplevel(self)
        dlg.title("Environment Verification Report")
        dlg.geometry("640x480")
        dlg.transient(self)
        dlg.grab_set()

        txt = tk.Text(dlg, font=("Consolas", 8), bg="#f8fafc", padx=10, pady=10)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, report)
        txt.config(state="disabled")

        btn_close = tk.Button(dlg, text="Close", command=dlg.destroy, padx=12, pady=4)
        btn_close.pack(pady=8)

    def _on_save(self):
        # 1. Theme
        new_theme = self.theme_var.get()
        set_setting("theme", new_theme, self.db_path)

        # 2. Timeout & Auto backup
        timeout_val = self.timeout_var.get().strip() or "30"
        set_setting("session_lock_minutes", timeout_val, self.db_path)
        set_setting("auto_backup", "true" if self.auto_backup_var.get() else "false", self.db_path)

        # 3. Paths
        t_dir = self.ent_ticket_dir.get().strip()
        b_dir = self.ent_backup_dir.get().strip()
        e_dir = self.ent_export_dir.get().strip()

        if t_dir:
            Path(t_dir).mkdir(parents=True, exist_ok=True)
            set_setting("ticket_dir", t_dir, self.db_path)
        if b_dir:
            Path(b_dir).mkdir(parents=True, exist_ok=True)
            set_setting("backup_dir", b_dir, self.db_path)
        if e_dir:
            Path(e_dir).mkdir(parents=True, exist_ok=True)
            set_setting("export_dir", e_dir, self.db_path)

        # 4. Admin profile & password
        new_disp_name = self.ent_disp_name.get().strip()
        if new_disp_name:
            update_admin_profile(session.username, new_disp_name, self.db_path)
            if session.current_user:
                session.current_user["display_name"] = new_disp_name

        old_pwd = self.ent_old_pwd.get()
        new_pwd = self.ent_new_pwd.get()
        cnf_pwd = self.ent_confirm_pwd.get()

        if new_pwd:
            if not old_pwd:
                messagebox.showerror("Password Change", "Please enter your current password to set a new password.", parent=self)
                return
            if new_pwd != cnf_pwd:
                messagebox.showerror("Password Change", "New passwords do not match. Please re-enter.", parent=self)
                return
            ok, msg = change_admin_password(session.username, old_pwd, new_pwd, self.db_path)
            if not ok:
                messagebox.showerror("Password Change Failed", msg, parent=self)
                return

        messagebox.showinfo("Settings Saved", "Application settings have been updated successfully.", parent=self)

        if self.on_settings_saved:
            self.on_settings_saved(new_theme)

        self.destroy()
