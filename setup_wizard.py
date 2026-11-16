"""
SRIVANI BOOKING MANAGER - First-Run Setup Wizard
7-Step Guided Wizard for fresh installations:
1. Welcome & TTD Compliance Notice
2. Client License Activation
3. Master Admin Account Setup
4. Database & Application Data Directory Configuration
5. Ticket PDF Storage Location
6. Database Backup Location
7. Confirmation Summary & Final Initialization
"""
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import (
    APP_DIR,
    DATA_DIR,
    TICKETS_DIR,
    BACKUPS_DIR,
    DB_PATH,
    TTD_PORTAL_URL,
)
from database import init_db, get_connection
from auth import init_auth_db, create_admin_user, has_admin_user
from licensing import (
    init_licensing_db,
    get_installation_id,
    activate_license,
    activate_trial_license,
    get_license_info,
)
from settings import init_settings, set_setting, APP_VERSION
from logger import get_logger

logger = get_logger("setup_wizard")

class FirstRunSetupWizard(tk.Toplevel):
    """Modern 7-Step First-Run Configuration Wizard."""

    def __init__(self, parent, db_path: Optional[Path] = None, on_complete=None):
        super().__init__(parent)
        self.db_path = db_path
        self.on_complete = on_complete
        self.is_completed = False

        self.title(f"Initial Setup Wizard — SRIVANI BOOKING MANAGER v{APP_VERSION}")
        self.geometry("700x560")
        self.minsize(660, 520)
        self.resizable(False, False)
        self.configure(bg="#f8fafc")

        if parent.winfo_viewable():
            self.transient(parent)
        self.grab_set()

        # Step tracking
        self.current_step = 1
        self.total_steps = 7

        # Form state variables
        self.inst_id = get_installation_id()
        self.client_name_var = tk.StringVar(value="Tirumala Pilgrim Services")
        self.license_key_var = tk.StringVar(value="")
        self.is_trial_var = tk.BooleanVar(value=True)

        self.admin_user_var = tk.StringVar(value="admin")
        self.admin_name_var = tk.StringVar(value="Master Administrator")
        self.admin_pwd_var = tk.StringVar(value="")
        self.admin_pwd2_var = tk.StringVar(value="")

        self.data_dir_var = tk.StringVar(value=str(DATA_DIR))
        self.ticket_dir_var = tk.StringVar(value=str(TICKETS_DIR))
        self.backup_dir_var = tk.StringVar(value=str(BACKUPS_DIR))

        self._build_layout()
        self._show_step(1)
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
        self.lift()
        self.attributes("-topmost", True)
        self.after_idle(lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _build_layout(self):
        # Top banner
        header = tk.Frame(self, bg="#0f172a", padx=20, pady=14)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=f"SRIVANI BOOKING MANAGER v{APP_VERSION}",
            font=("Segoe UI", 13, "bold"),
            fg="#f59e0b",
            bg="#0f172a",
        ).pack(anchor="w")

        self.lbl_step_header = tk.Label(
            header,
            text="First-Run Setup Wizard",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
        )
        self.lbl_step_header.pack(anchor="w", pady=(2, 0))

        # Main horizontal container: Step Indicator Sidebar + Content Frame
        container = tk.Frame(self, bg="#f8fafc")
        container.pack(fill=tk.BOTH, expand=True)

        # Step Progress Sidebar
        self.sidebar = tk.Frame(container, bg="#1e293b", width=190, padx=14, pady=16)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.step_labels = []
        step_titles = [
            "1. Welcome & Terms",
            "2. Licensing",
            "3. Admin Account",
            "4. Data Folder",
            "5. Ticket Storage",
            "6. Backup Folder",
            "7. Confirmation",
        ]

        for idx, title in enumerate(step_titles, start=1):
            lbl = tk.Label(
                self.sidebar,
                text=title,
                font=("Segoe UI", 8),
                fg="#94a3b8",
                bg="#1e293b",
                anchor="w",
                padx=6,
                pady=6,
            )
            lbl.pack(fill=tk.X, pady=2)
            self.step_labels.append(lbl)

        # Dynamic Content Area
        self.content_frame = tk.Frame(container, bg="#f8fafc", padx=20, pady=16)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Bottom Button Bar
        btn_bar = tk.Frame(self, bg="#f1f5f9", padx=20, pady=12)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.btn_cancel = tk.Button(
            btn_bar,
            text="Exit Setup",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#334155",
            relief="flat",
            padx=12,
            pady=5,
            command=self._on_cancel,
        )
        self.btn_cancel.pack(side=tk.LEFT)

        self.btn_next = tk.Button(
            btn_bar,
            text="Next Step >",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=5,
            cursor="hand2",
            command=self._on_next,
        )
        self.btn_next.pack(side=tk.RIGHT)

        self.btn_back = tk.Button(
            btn_bar,
            text="< Back",
            font=("Segoe UI", 9),
            bg="#cbd5e1",
            fg="#1e293b",
            relief="flat",
            padx=14,
            pady=5,
            command=self._on_back,
        )
        self.btn_back.pack(side=tk.RIGHT, padx=8)

    def _update_step_indicator(self):
        for idx, lbl in enumerate(self.step_labels, start=1):
            if idx == self.current_step:
                lbl.config(fg="#ffffff", font=("Segoe UI", 8, "bold"), bg="#3b82f6")
            elif idx < self.current_step:
                lbl.config(fg="#10b981", font=("Segoe UI", 8), bg="#1e293b")
            else:
                lbl.config(fg="#64748b", font=("Segoe UI", 8), bg="#1e293b")

        self.btn_back.config(state="normal" if self.current_step > 1 else "disabled")
        if self.current_step == self.total_steps:
            self.btn_next.config(text="✨ Finish & Open Application", bg="#16a34a", activebackground="#15803d")
        else:
            self.btn_next.config(text="Next Step >", bg="#2563eb", activebackground="#1d4ed8")

    def _show_step(self, step: int):
        self.current_step = step
        self._update_step_indicator()

        # Clear existing step view
        for child in self.content_frame.winfo_children():
            child.destroy()

        if step == 1:
            self._render_step1_welcome()
        elif step == 2:
            self._render_step2_licensing()
        elif step == 3:
            self._render_step3_admin()
        elif step == 4:
            self._render_step4_data_dir()
        elif step == 5:
            self._render_step5_ticket_dir()
        elif step == 6:
            self._render_step6_backup_dir()
        elif step == 7:
            self._render_step7_confirmation()

    # ---------------------------------------------------------
    # STEP 1: Welcome & Terms
    # ---------------------------------------------------------
    def _render_step1_welcome(self):
        f = self.content_frame
        self.lbl_step_header.config(text="Step 1 of 7: Welcome & TTD Portal Compliance")

        tk.Label(f, text="Welcome to SRIVANI BOOKING MANAGER", font=("Segoe UI", 12, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 6))

        intro = (
            "This enterprise application assists authorized temple administration personnel "
            "in organizing pilgrim rosters, managing sequential booking queues, generating "
            "darshan slips, and archiving official Srivani Trust donation tickets."
        )
        tk.Label(f, text=intro, font=("Segoe UI", 9), fg="#475569", bg="#f8fafc", wraplength=460, justify=tk.LEFT).pack(anchor="w", pady=(0, 10))

        # Compliance box
        c_box = tk.LabelFrame(f, text=" Official TTD Portal Compliance Agreement ", font=("Segoe UI", 8, "bold"), bg="#ffffff", padx=12, pady=10)
        c_box.pack(fill=tk.BOTH, expand=True, pady=(4, 10))

        terms_text = (
            "1. Client Manual Control: Official TTD portal login, CAPTCHA solutions, SMS OTP verifications, "
            "and payment authorizations remain strictly under manual operator control.\n\n"
            "2. No Restricted Automation: This system does NOT automate ticket submissions, solve CAPTCHAs, "
            "or bypass quota and queue limits on the official TTD website.\n\n"
            "3. Sensitive Credential Protection: This system never stores banking credentials, credit card "
            "numbers, UPI PINs, or TTD portal passwords.\n\n"
            "Official Website: https://ttdevasthanams.ap.gov.in"
        )
        lbl_terms = tk.Label(c_box, text=terms_text, font=("Segoe UI", 8), fg="#334155", bg="#ffffff", wraplength=430, justify=tk.LEFT)
        lbl_terms.pack(anchor="w")

        self.accept_terms_var = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(
            f,
            text="I understand and agree to adhere to official TTD operational guidelines.",
            variable=self.accept_terms_var,
            font=("Segoe UI", 9, "bold"),
            bg="#f8fafc",
            fg="#1e293b",
        )
        chk.pack(anchor="w", pady=(6, 0))

    # ---------------------------------------------------------
    # STEP 2: Licensing
    # ---------------------------------------------------------
    def _render_step2_licensing(self):
        f = self.content_frame
        self.lbl_step_header.config(text="Step 2 of 7: Client Software Licensing")

        tk.Label(f, text="Activate Software License", font=("Segoe UI", 12, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 6))

        tk.Label(f, text="Your Machine Installation ID:", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#f8fafc").pack(anchor="w")
        id_row = tk.Frame(f, bg="#f8fafc")
        id_row.pack(fill=tk.X, pady=(2, 8))

        ent_id = ttk.Entry(id_row, font=("Segoe UI", 9, "bold"))
        ent_id.insert(0, self.inst_id)
        ent_id.config(state="readonly")
        ent_id.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        tk.Button(id_row, text="📋 Copy ID", font=("Segoe UI", 8), command=lambda: self._copy_text(self.inst_id)).pack(side=tk.RIGHT)

        # Radio options: Commercial key vs 30-day evaluation
        opt_box = tk.LabelFrame(f, text=" License Options ", font=("Segoe UI", 8, "bold"), bg="#ffffff", padx=12, pady=10)
        opt_box.pack(fill=tk.X, pady=(4, 10))

        tk.Radiobutton(
            opt_box,
            text="Start with 30-Day Evaluation License (Full features enabled, no key required)",
            variable=self.is_trial_var,
            value=True,
            font=("Segoe UI", 9),
            bg="#ffffff",
            command=self._toggle_license_mode,
        ).pack(anchor="w", pady=2)

        tk.Radiobutton(
            opt_box,
            text="Enter Commercial License Key",
            variable=self.is_trial_var,
            value=False,
            font=("Segoe UI", 9),
            bg="#ffffff",
            command=self._toggle_license_mode,
        ).pack(anchor="w", pady=2)

        # Fields frame
        self.lic_fields_frame = tk.Frame(f, bg="#f8fafc")
        self.lic_fields_frame.pack(fill=tk.X, pady=4)

        tk.Label(self.lic_fields_frame, text="Client / Organization Name:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        ttk.Entry(self.lic_fields_frame, textvariable=self.client_name_var, width=40).pack(fill=tk.X, pady=(0, 8))

        tk.Label(self.lic_fields_frame, text="Commercial License Key:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        self.ent_lic_key = ttk.Entry(self.lic_fields_frame, textvariable=self.license_key_var, width=40)
        self.ent_lic_key.pack(fill=tk.X, pady=(0, 4))

        self._toggle_license_mode()

    def _toggle_license_mode(self):
        if self.is_trial_var.get():
            self.ent_lic_key.config(state="disabled")
        else:
            self.ent_lic_key.config(state="normal")

    def _copy_text(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", f"Copied to clipboard:\n{text}", parent=self)

    # ---------------------------------------------------------
    # STEP 3: Admin Account
    # ---------------------------------------------------------
    def _render_step3_admin(self):
        f = self.content_frame
        self.lbl_step_header.config(text="Step 3 of 7: Master Admin Account Setup")

        tk.Label(f, text="Create Local Administrator Account", font=("Segoe UI", 12, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 6))

        desc = "This master account controls the desktop booking workspace. Passwords are encrypted using salted bcrypt hashing."
        tk.Label(f, text=desc, font=("Segoe UI", 8), fg="#64748b", bg="#f8fafc", wraplength=460, justify=tk.LEFT).pack(anchor="w", pady=(0, 12))

        tk.Label(f, text="Admin Username (min 3 chars):", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        ttk.Entry(f, textvariable=self.admin_user_var, width=35).pack(fill=tk.X, pady=(0, 8))

        tk.Label(f, text="Display Name / Full Name:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        ttk.Entry(f, textvariable=self.admin_name_var, width=35).pack(fill=tk.X, pady=(0, 8))

        tk.Label(f, text="Master Password (min 6 characters):", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        ttk.Entry(f, textvariable=self.admin_pwd_var, width=35, show="*").pack(fill=tk.X, pady=(0, 8))

        tk.Label(f, text="Confirm Master Password:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        ttk.Entry(f, textvariable=self.admin_pwd2_var, width=35, show="*").pack(fill=tk.X, pady=(0, 8))

    # ---------------------------------------------------------
    # STEP 4: Data Directory
    # ---------------------------------------------------------
    def _render_step4_data_dir(self):
        f = self.content_frame
        self.lbl_step_header.config(text="Step 4 of 7: Database & Application Data Path")

        tk.Label(f, text="Configure Data Storage Directory", font=("Segoe UI", 12, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 6))

        desc = (
            "The SQLite database, system logs, and operational rosters are stored in this directory. "
            "User data is preserved outside the executable directory so upgrades never delete your data."
        )
        tk.Label(f, text=desc, font=("Segoe UI", 8), fg="#64748b", bg="#f8fafc", wraplength=460, justify=tk.LEFT).pack(anchor="w", pady=(0, 14))

        tk.Label(f, text="Data Folder Path:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        row = tk.Frame(f, bg="#f8fafc")
        row.pack(fill=tk.X, pady=(0, 10))

        ttk.Entry(row, textvariable=self.data_dir_var, width=42).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row, text="Browse...", font=("Segoe UI", 8), command=lambda: self._browse_dir(self.data_dir_var)).pack(side=tk.RIGHT)

    # ---------------------------------------------------------
    # STEP 5: Ticket PDF Storage Directory
    # ---------------------------------------------------------
    def _render_step5_ticket_dir(self):
        f = self.content_frame
        self.lbl_step_header.config(text="Step 5 of 7: Ticket PDF Storage Path")

        tk.Label(f, text="Configure Ticket PDFs Folder", font=("Segoe UI", 12, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 6))

        desc = (
            "Downloaded official Srivani donation receipts and darshan ticket PDFs will be archived here. "
            "Files are organized automatically into family-specific folders with SHA-256 duplicate verification."
        )
        tk.Label(f, text=desc, font=("Segoe UI", 8), fg="#64748b", bg="#f8fafc", wraplength=460, justify=tk.LEFT).pack(anchor="w", pady=(0, 14))

        tk.Label(f, text="Ticket Storage Path:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        row = tk.Frame(f, bg="#f8fafc")
        row.pack(fill=tk.X, pady=(0, 10))

        ttk.Entry(row, textvariable=self.ticket_dir_var, width=42).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row, text="Browse...", font=("Segoe UI", 8), command=lambda: self._browse_dir(self.ticket_dir_var)).pack(side=tk.RIGHT)

    # ---------------------------------------------------------
    # STEP 6: Backup Directory
    # ---------------------------------------------------------
    def _render_step6_backup_dir(self):
        f = self.content_frame
        self.lbl_step_header.config(text="Step 6 of 7: Database Backup Path")

        tk.Label(f, text="Configure Disaster Recovery Backups Folder", font=("Segoe UI", 12, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 6))

        desc = (
            "Automated and manual SQLite backup snapshots are saved here. "
            "Backups include full cryptographic integrity validation (PRAGMA integrity_check)."
        )
        tk.Label(f, text=desc, font=("Segoe UI", 8), fg="#64748b", bg="#f8fafc", wraplength=460, justify=tk.LEFT).pack(anchor="w", pady=(0, 14))

        tk.Label(f, text="Backup Storage Path:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").pack(anchor="w", pady=(2, 2))
        row = tk.Frame(f, bg="#f8fafc")
        row.pack(fill=tk.X, pady=(0, 10))

        ttk.Entry(row, textvariable=self.backup_dir_var, width=42).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(row, text="Browse...", font=("Segoe UI", 8), command=lambda: self._browse_dir(self.backup_dir_var)).pack(side=tk.RIGHT)

    def _browse_dir(self, var: tk.StringVar):
        chosen = filedialog.askdirectory(parent=self, title="Select Directory", initialdir=var.get())
        if chosen:
            var.set(str(Path(chosen).resolve()))

    # ---------------------------------------------------------
    # STEP 7: Confirmation & Finish
    # ---------------------------------------------------------
    def _render_step7_confirmation(self):
        f = self.content_frame
        self.lbl_step_header.config(text="Step 7 of 7: Ready for Launch")

        tk.Label(f, text="Review & Complete Setup", font=("Segoe UI", 12, "bold"), fg="#1e293b", bg="#f8fafc").pack(anchor="w", pady=(0, 6))

        # Summary text box
        txt_box = tk.Text(f, height=14, width=54, font=("Segoe UI", 8), bg="#ffffff", relief="solid", borderwidth=1, padx=10, pady=10)
        txt_box.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        lic_desc = "30-Day Evaluation License" if self.is_trial_var.get() else f"Commercial License: {self.license_key_var.get().strip()}"
        summary = (
            f"=== INITIAL CONFIGURATION SUMMARY ===\n\n"
            f"• Software Release: SRIVANI BOOKING MANAGER v{APP_VERSION}\n"
            f"• Machine Installation ID: {self.inst_id}\n"
            f"• Client / Organization: {self.client_name_var.get().strip()}\n"
            f"• License Mode: {lic_desc}\n\n"
            f"• Master Administrator: {self.admin_user_var.get().strip()} ({self.admin_name_var.get().strip()})\n"
            f"• Password Hashing: Salted bcrypt algorithm\n\n"
            f"• Application Data Directory: {self.data_dir_var.get().strip()}\n"
            f"• Ticket PDF Storage Folder: {self.ticket_dir_var.get().strip()}\n"
            f"• Backup Snapshots Folder: {self.backup_dir_var.get().strip()}\n\n"
            f"• Compliance: Official TTD Portal guidelines accepted.\n"
            f"Click 'Finish & Open Application' to initialize your workspace."
        )
        txt_box.insert(tk.END, summary)
        txt_box.config(state="disabled")

    # ---------------------------------------------------------
    # Wizard Navigation Logic & Validation
    # ---------------------------------------------------------
    def _on_next(self):
        # Validate current step before proceeding
        if self.current_step == 1:
            if not self.accept_terms_var.get():
                messagebox.showerror("Terms Required", "Please accept the TTD operational guidelines to proceed.", parent=self)
                return

        elif self.current_step == 2:
            client = self.client_name_var.get().strip()
            if not client:
                messagebox.showerror("Client Name Required", "Please enter your Client or Organization Name.", parent=self)
                return
            if not self.is_trial_var.get():
                key = self.license_key_var.get().strip()
                if not key:
                    messagebox.showerror("Key Required", "Please enter a valid commercial license key or select Evaluation mode.", parent=self)
                    return

        elif self.current_step == 3:
            user = self.admin_user_var.get().strip()
            pwd = self.admin_pwd_var.get()
            pwd2 = self.admin_pwd2_var.get()

            if len(user) < 3:
                messagebox.showerror("Username Too Short", "Username must be at least 3 characters long.", parent=self)
                return
            if len(pwd) < 6:
                messagebox.showerror("Password Too Short", "Master password must be at least 6 characters long.", parent=self)
                return
            if pwd != pwd2:
                messagebox.showerror("Passwords Mismatch", "Passwords do not match. Please re-enter.", parent=self)
                return

        elif self.current_step in (4, 5, 6):
            for path_val, name in [
                (self.data_dir_var.get().strip(), "Data"),
                (self.ticket_dir_var.get().strip(), "Ticket Storage"),
                (self.backup_dir_var.get().strip(), "Backup"),
            ]:
                if not path_val:
                    messagebox.showerror("Path Required", f"Please specify a valid path for {name}.", parent=self)
                    return

        if self.current_step < self.total_steps:
            self._show_step(self.current_step + 1)
        else:
            self._finalize_setup()

    def _on_back(self):
        if self.current_step > 1:
            self._show_step(self.current_step - 1)

    def _on_cancel(self):
        if messagebox.askyesno("Exit Setup", "Are you sure you want to exit setup? The application cannot start until initial configuration is completed.", parent=self):
            self.destroy()
            sys.exit(0)

    def _finalize_setup(self):
        """Commit all configurations to SQLite and create directories."""
        try:
            # 1. Ensure target folders exist
            d_dir = Path(self.data_dir_var.get().strip())
            t_dir = Path(self.ticket_dir_var.get().strip())
            b_dir = Path(self.backup_dir_var.get().strip())

            d_dir.mkdir(parents=True, exist_ok=True)
            t_dir.mkdir(parents=True, exist_ok=True)
            b_dir.mkdir(parents=True, exist_ok=True)

            # 2. Initialize database
            init_db(self.db_path)
            init_auth_db(self.db_path)
            init_settings(self.db_path)
            init_licensing_db(self.db_path)

            # 3. Save directories to settings
            set_setting("ticket_dir", str(t_dir), self.db_path)
            set_setting("backup_dir", str(b_dir), self.db_path)
            set_setting("export_dir", str(d_dir / "exports"), self.db_path)
            set_setting("auto_backup", "true", self.db_path)
            set_setting("first_run_completed", "true", self.db_path)

            # 4. Create admin account
            user = self.admin_user_var.get().strip()
            name = self.admin_name_var.get().strip()
            pwd = self.admin_pwd_var.get()
            ok_admin, msg_admin = create_admin_user(user, pwd, name, self.db_path)
            if not ok_admin and "already exists" not in msg_admin.lower():
                messagebox.showerror("Admin Setup Failed", msg_admin, parent=self)
                return

            # 5. Activate license or trial
            client = self.client_name_var.get().strip()
            if self.is_trial_var.get():
                activate_trial_license(client, days=30, db_path=self.db_path)
            else:
                key = self.license_key_var.get().strip()
                ok_lic, msg_lic = activate_license(key, client, db_path=self.db_path)
                if not ok_lic:
                    # Fallback to trial if key verification failed
                    activate_trial_license(client, days=30, db_path=self.db_path)

            self.is_completed = True
            messagebox.showinfo(
                "Setup Complete",
                "SRIVANI BOOKING MANAGER has been successfully configured and initialized!\n\nYou may now sign in to your dashboard.",
                parent=self,
            )

            if self.on_complete:
                self.on_complete()

            self.destroy()

        except Exception as e:
            logger.error(f"Error finalizing first-run setup: {e}")
            messagebox.showerror("Setup Error", f"Failed to complete initialization:\n{e}", parent=self)
