"""
SRIVANI BOOKING MANAGER — Phase 2 Professional Desktop Suite
High-Performance Family & Devotee Booking Management Application
"""
import os
import sys
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
from typing import Optional

# Local modules
import config
from database import (
    init_db,
    get_connection,
    get_stats,
    get_all_families,
    get_family,
    get_family_pilgrims,
    delete_family,
    set_priority,
    shift_queue_order,
    get_queue_history,
    get_family_booking_history,
    check_database_integrity,
    get_current_schema_version,
)
from import_export import (
    import_records,
    analyze_import_file,
    commit_import_from_analysis,
    export_to_csv,
    export_to_excel,
    create_sample_excel_template,
    ImportPreviewDialog,
)
from ticket_manager import open_ticket_pdf, generate_booking_slip_pdf
from family_dialogs import (
    AddFamilyDialog,
    EditFamilyDialog,
    UpdateStatusDialog,
    TicketPDFDialog,
    QueueHistoryDialog,
)
from assisted_booking import AssistedBookingAssistant
from booking_workspace import BookingWorkspaceDialog
from backup_manager import (
    create_database_backup,
    list_backups,
    restore_database_backup,
    BackupRestoreDialog,
)
from reports import (
    get_daily_completed_report,
    get_weekly_report,
    get_monthly_report,
    get_booking_status_summary_report,
    get_pending_families_report,
    get_failed_or_unavailable_report,
    get_payment_status_report,
    get_total_pilgrims_report,
    validate_report_totals,
    export_report_to_csv,
    generate_printable_pdf_report,
)
from auth import (
    init_auth_db,
    has_admin_user,
    session,
    AdminSetupDialog,
    LoginDialog,
)
from settings import (
    init_settings,
    get_setting,
    set_setting,
    SettingsDialog,
    APP_VERSION,
)
from themes import (
    apply_theme,
    get_theme_palette,
    get_current_theme_name,
)
from licensing import (
    init_licensing_db,
    get_license_info,
    is_licensed,
    LicenseActivationDialog,
)
from setup_wizard import FirstRunSetupWizard
from support_diagnostics import SupportDialog
from analytics_view import AnalyticsDashboardFrame
from preparation_workspace import (
    FastBookingDashboardView,
    ManualBookingWorkspaceDialog,
    DocumentManagementDialog,
    BookingReadinessInspectorDialog,
    BookingHistoryFrame,
)
from data_import_view import DataImportView
from data_cleanup import DataCleanupDialog, scan_for_mock_data

# Legacy compatibility exports
def connect():
    return get_connection()

def import_csv(path):
    imported, skipped, _ = import_records(path)
    return imported, skipped

class App(tk.Tk):
    def __init__(self, require_auth: bool = False):
        super().__init__()
        self.title(f"SRIVANI BOOKING MANAGER v{APP_VERSION} — Production Desktop Suite")
        self.geometry("1340x820")
        self.minsize(1080, 680)

        # Initialize SQLite database, auth, settings and licensing
        init_db()
        init_auth_db()
        init_settings()
        init_licensing_db()

        # Load and apply active theme
        self.active_theme = get_setting("theme", "light")
        self.palette = apply_theme(self, self.active_theme)
        self.configure(bg=self.palette["bg_app"])

        # Authenticate if required
        if require_auth:
            self._ensure_authenticated()

        self.current_view_name = "dashboard"
        self._init_styles()
        self._build_layout()
        self.show_view("dashboard")
        self.refresh()

    def _ensure_authenticated(self):
        """Prompt for first-run setup wizard on fresh installs, and login on startup."""
        self.withdraw()
        if not has_admin_user() or get_setting("first_run_completed") != "true":
            wizard = FirstRunSetupWizard(self)
            self.wait_window(wizard)
            if not has_admin_user():
                self.destroy()
                sys.exit(0)

        login_dlg = LoginDialog(self)
        self.wait_window(login_dlg)
        if not login_dlg.authenticated_user:
            self.destroy()
            sys.exit(0)

        session.login(login_dlg.authenticated_user)
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after_idle(lambda: self.attributes("-topmost", False))
        self.focus_force()

        # Non-destructive license check
        lic = get_license_info()
        if lic.get("is_expired", False):
            messagebox.showwarning(
                "Evaluation Notice",
                "Your 30-day software evaluation period has ended.\n\n"
                "The application will continue operating safely. You can activate "
                "your commercial license anytime under 'Preferences & About' -> 'Client Licensing'.",
                parent=self,
            )

    def _init_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        font_family = "Segoe UI"
        primary_color = "#1B365D"

        # Treeview styling
        style.configure("Treeview", rowheight=30, font=(font_family, 10))
        style.configure("Treeview.Heading", font=(font_family, 10, "bold"), background="#E2E8F0", foreground="#1E293B")
        style.map("Treeview", background=[("selected", "#0D5C75")], foreground=[("selected", "#FFFFFF")])

        # Button styling
        style.configure("TButton", font=(font_family, 9), padding=(8, 5))
        style.configure("Primary.TButton", font=(font_family, 9, "bold"), padding=(10, 6), background="#0D5C75", foreground="#FFFFFF")
        style.configure("Action.TButton", font=(font_family, 9), padding=(6, 4))

        # Typography
        style.configure("Header.TLabel", font=(font_family, 16, "bold"), background="#F8FAFC", foreground=primary_color)
        style.configure("Sub.TLabel", font=(font_family, 9), background="#F8FAFC", foreground="#64748B")
        style.configure("StatValue.TLabel", font=(font_family, 15, "bold"), foreground="#0F172A", background="#FFFFFF")
        style.configure("StatLabel.TLabel", font=(font_family, 8, "bold"), foreground="#64748B", background="#FFFFFF")

    def _build_layout(self):
        # Master horizontal layout: Left Sidebar + Right Content View
        self.sidebar_frame = tk.Frame(self, bg="#0F172A", width=220)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        self.content_frame = tk.Frame(self, bg="#F8FAFC")
        self.content_frame.pack(side="right", fill="both", expand=True)

        self._build_sidebar()
        self._build_views()

    def _build_sidebar(self):
        sb = self.sidebar_frame

        # Brand / Logo Header
        brand_box = tk.Frame(sb, bg="#0F172A", padx=16, pady=20)
        brand_box.pack(fill="x")

        lbl_srivani = tk.Label(brand_box, text="SRIVANI", font=("Segoe UI", 16, "bold"), fg="#F59E0B", bg="#0F172A")
        lbl_srivani.pack(anchor="w")
        lbl_mgr = tk.Label(brand_box, text="BOOKING MANAGER", font=("Segoe UI", 10, "bold"), fg="#E2E8F0", bg="#0F172A")
        lbl_mgr.pack(anchor="w")
        lbl_phase = tk.Label(brand_box, text="Phase 9 • Fast Booking Engine", font=("Segoe UI", 8), fg="#94A3B8", bg="#0F172A")
        lbl_phase.pack(anchor="w", pady=(2, 0))

        # Divider
        tk.Frame(sb, bg="#1E293B", height=1).pack(fill="x", padx=12, pady=(0, 16))

        # Navigation Menu Buttons
        self.nav_buttons = {}
        nav_items = [
            ("fast_dashboard", "🎯 Fast Preparation"),
            ("workspace", "⚡ Booking Workspace"),
            ("dashboard", "📊 Queue & Status"),
            ("data_import", "📥 DATA IMPORT"),
            ("families", "👥 Families & Devotees"),
            ("documents", "📁 Document Manager"),
            ("history", "📜 Booking History"),
            ("analytics", "📈 Advanced Analytics"),
            ("reports", "📑 Standard Reports"),
            ("import_export", "📤 Export Center"),
            ("settings", "⚙️ Preferences & Rules"),
            ("backup", "💾 Backup & Recovery"),
        ]

        for key, label in nav_items:
            btn = tk.Button(
                sb,
                text=label,
                font=("Segoe UI", 10),
                anchor="w",
                padx=16,
                pady=9,
                bd=0,
                cursor="hand2",
                fg="#E2E8F0",
                bg="#0F172A",
                activebackground="#1E293B",
                activeforeground="#FFFFFF",
                command=lambda k=key: self.on_nav_click(k),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[key] = btn

        # Spacer
        tk.Frame(sb, bg="#0F172A").pack(fill="both", expand=True)

        # Bottom Sidebar Controls & Status
        bottom_box = tk.Frame(sb, bg="#0F172A", padx=12, pady=12)
        bottom_box.pack(fill="x")

        # Admin User Label
        admin_name = session.display_name if session.is_authenticated else "Administrator"
        self.lbl_admin_user = tk.Label(
            bottom_box,
            text=f"👤 {admin_name}",
            font=("Segoe UI", 8, "bold"),
            fg="#94A3B8",
            bg="#0F172A",
        )
        self.lbl_admin_user.pack(anchor="w", pady=(0, 4))

        # Lock Session Button
        btn_lock = tk.Button(
            bottom_box,
            text="🔒 Lock Session",
            font=("Segoe UI", 8, "bold"),
            bg="#334155",
            fg="#F8FAFC",
            bd=0,
            pady=4,
            cursor="hand2",
            command=self.lock_session,
        )
        btn_lock.pack(fill="x", pady=2)

        # Settings Dialog Button
        btn_settings = tk.Button(
            bottom_box,
            text="⚙️ Preferences & About",
            font=("Segoe UI", 8),
            bg="#1E293B",
            fg="#CBD5E1",
            bd=0,
            pady=4,
            cursor="hand2",
            command=self.open_settings,
        )
        btn_settings.pack(fill="x", pady=2)

        # Support & Helpdesk Hub Button
        btn_support = tk.Button(
            bottom_box,
            text="🎧 Support & Diagnostics",
            font=("Segoe UI", 8),
            bg="#1E293B",
            fg="#CBD5E1",
            bd=0,
            pady=4,
            cursor="hand2",
            command=self.open_support,
        )
        btn_support.pack(fill="x", pady=2)

        # Theme Switcher Button
        self.btn_theme_toggle = tk.Button(
            bottom_box,
            text="🌓 Switch Theme",
            font=("Segoe UI", 8),
            bg="#1E293B",
            fg="#CBD5E1",
            bd=0,
            pady=4,
            cursor="hand2",
            command=self.toggle_theme,
        )
        self.btn_theme_toggle.pack(fill="x", pady=2)

        # Official Portal Link
        btn_portal = tk.Button(
            bottom_box,
            text="🌐 Open TTD Portal",
            font=("Segoe UI", 8, "bold"),
            bg="#0369A1",
            fg="#FFFFFF",
            bd=0,
            pady=5,
            cursor="hand2",
            command=lambda: webbrowser.open(config.TTD_PORTAL_URL),
        )
        btn_portal.pack(fill="x", pady=(6, 4))

        ver = get_current_schema_version()
        lbl_status = tk.Label(bottom_box, text=f"● SQLite DB v{ver} OK", font=("Segoe UI", 8), fg="#10B981", bg="#0F172A")
        lbl_status.pack(anchor="w")

        lic = get_license_info()
        lic_txt = f"● License: {lic['status']} ({lic['license_type']})"
        lic_color = "#10B981" if lic["is_licensed"] else "#F59E0B"
        lbl_lic = tk.Label(bottom_box, text=lic_txt, font=("Segoe UI", 8), fg=lic_color, bg="#0F172A")
        lbl_lic.pack(anchor="w")

    def lock_session(self):
        """Lock current session until authenticated admin password is provided."""
        session.lock()
        self.withdraw()
        unlock_dlg = LoginDialog(self, is_unlock=True, locked_username=session.username)
        self.wait_window(unlock_dlg)
        if unlock_dlg.authenticated_user:
            session.unlock(unlock_dlg.authenticated_user)
            self.lbl_admin_user.config(text=f"👤 {session.display_name}")
            self.deiconify()
        else:
            self.destroy()
            sys.exit(0)

    def open_settings(self):
        """Open Application Preferences and System Dialog."""
        SettingsDialog(self, on_settings_saved=self._on_settings_saved)

    def open_support(self):
        """Open Customer Support and System Diagnostics Dialog."""
        SupportDialog(self)

    def _open_license_dialog(self):
        """Open License Activation modal dialog."""
        LicenseActivationDialog(self, on_success=self.refresh)

    def _on_settings_saved(self, new_theme: str):
        self.apply_theme_mode(new_theme)

    def toggle_theme(self):
        """Toggle between light and slate dark color themes."""
        curr = get_current_theme_name()
        new_t = "dark" if curr == "light" else "light"
        set_setting("theme", new_t)
        self.apply_theme_mode(new_t)

    def apply_theme_mode(self, theme_name: str):
        self.active_theme = theme_name
        self.palette = apply_theme(self, theme_name)
        self.configure(bg=self.palette["bg_app"])
        self.sidebar_frame.configure(bg=self.palette["bg_sidebar"])
        self.content_frame.configure(bg=self.palette["bg_app"])
        self.refresh()

    def on_nav_click(self, view_name: str):
        if view_name == "workspace":
            self.open_family_workspace()
            return
        elif view_name == "documents":
            fid = self.selected_id()
            if fid is None:
                queue_rows = get_all_families(sort_by="queue")
                if queue_rows:
                    fid = queue_rows[0]["id"]
            if fid:
                DocumentManagementDialog(self, fid, on_update_callback=self.refresh)
            else:
                messagebox.showinfo("Documents", "No family records available.", parent=self)
            return
        elif view_name == "backup":
            BackupRestoreDialog(self, on_restore_callback=self.refresh)
            return
        elif view_name == "settings":
            self.open_settings()
            return
        self.show_view(view_name)

    def show_view(self, view_name: str):
        self.current_view_name = view_name

        # Update sidebar button highlight
        for k, btn in self.nav_buttons.items():
            if k == view_name:
                btn.config(bg="#1E293B", fg="#38BDF8", font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg="#0F172A", fg="#E2E8F0", font=("Segoe UI", 10))

        # Show target view frame
        for k, frame in self.views.items():
            if k == view_name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        if view_name == "history":
            if hasattr(self.views["history"], "filter_history"):
                self.views["history"].filter_history()
            else:
                self._refresh_history_view()
        elif view_name == "fast_dashboard":
            if hasattr(self.views["fast_dashboard"], "refresh_dashboard"):
                self.views["fast_dashboard"].refresh_dashboard()
        elif view_name == "data_import":
            if hasattr(self.views["data_import"], "refresh_history"):
                self.views["data_import"].refresh_history()
        elif view_name == "reports":
            self._refresh_reports_view()
        elif view_name == "analytics":
            if "analytics" in self.views and hasattr(self.views["analytics"], "refresh_analytics"):
                self.views["analytics"].refresh_analytics()
        else:
            self.refresh()

    def _build_views(self):
        self.views = {
            "fast_dashboard": FastBookingDashboardView(self.content_frame, self),
            "dashboard": tk.Frame(self.content_frame, bg="#F8FAFC"),
            "data_import": DataImportView(self.content_frame, self),
            "analytics": AnalyticsDashboardFrame(self.content_frame, self),
            "families": tk.Frame(self.content_frame, bg="#F8FAFC"),
            "import_export": tk.Frame(self.content_frame, bg="#F8FAFC"),
            "reports": tk.Frame(self.content_frame, bg="#F8FAFC"),
            "history": BookingHistoryFrame(self.content_frame, self),
        }

        self._build_dashboard_view(self.views["dashboard"])
        self._build_families_view(self.views["families"])
        self._build_import_export_view(self.views["import_export"])
        self._build_reports_view(self.views["reports"])

    # ---------------------------------------------------------
    # VIEW 1: Dashboard & Queue
    # ---------------------------------------------------------
    def _build_dashboard_view(self, parent):
        # 1. Top Header
        top_header = ttk.Frame(parent, padding=(20, 14, 20, 6))
        top_header.pack(fill="x")

        h_left = ttk.Frame(top_header)
        h_left.pack(side="left")
        ttk.Label(h_left, text="SRIVANI BOOKING MANAGER", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            h_left,
            text="Sequential Family Booking Queue • Operational Intelligence • Phase 7",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        h_right = ttk.Frame(top_header)
        h_right.pack(side="right")
        ttk.Button(
            h_right,
            text="⚡ Start Assisted Booking Assistant",
            style="Primary.TButton",
            command=self.open_assisted_booking,
        ).pack(side="right")

        # License Expiry & Notice Banner
        self.license_banner = tk.Frame(parent, bg="#FEF3C7", padx=16, pady=6)
        self.lbl_lic_banner = tk.Label(self.license_banner, text="", font=("Segoe UI", 9, "bold"), fg="#92400E", bg="#FEF3C7")
        self.lbl_lic_banner.pack(side="left")
        self.btn_lic_banner = tk.Button(
            self.license_banner,
            text="🔑 Activate / Renew Key",
            font=("Segoe UI", 8, "bold"),
            bg="#D97706",
            fg="white",
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._open_license_dialog,
        )
        self.btn_lic_banner.pack(side="right")

        # 2. Six Required Dashboard Summary Cards:
        # Total Families, Total Pilgrims, Pending Families, In Progress, Booked, Cancelled
        self.stats_frame = ttk.Frame(parent, padding=(20, 6, 20, 8))
        self.stats_frame.pack(fill="x")
        stats_frame = self.stats_frame

        self.cards = {}
        metric_configs = [
            ("total_families", "TOTAL FAMILIES", "0", "#1B365D"),
            ("total_pilgrims", "TOTAL PILGRIMS", "0", "#4338CA"),
            ("pending_families", "PENDING FAMILIES", "0", "#B45309"),
            ("in_progress", "IN PROGRESS", "0", "#0369A1"),
            ("booked", "BOOKED", "0", "#15803D"),
            ("cancelled", "CANCELLED", "0", "#DC2626"),
        ]

        for idx, (key, label, default_val, color) in enumerate(metric_configs):
            card = tk.Frame(stats_frame, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1, padx=12, pady=6)
            card.pack(side="left", expand=True, fill="x", padx=(0 if idx == 0 else 6, 0))
            lbl_title = ttk.Label(card, text=label, style="StatLabel.TLabel")
            lbl_title.pack(anchor="w")
            lbl_val = ttk.Label(card, text=default_val, style="StatValue.TLabel", foreground=color)
            lbl_val.pack(anchor="w")
            self.cards[key] = lbl_val

        # Empty State Welcome & Getting Started Banner
        self.empty_state_frame = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", padx=20, pady=16)

        lbl_empty_title = tk.Label(
            self.empty_state_frame,
            text="✨ Welcome to SRIVANI BOOKING MANAGER",
            font=("Segoe UI", 13, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        lbl_empty_title.pack(anchor="w")

        lbl_empty_desc = tk.Label(
            self.empty_state_frame,
            text=(
                "The database is clean and ready for your real devotee records. No artificial demo data is loaded.\n"
                "To get started, import your client dataset (.csv or .xlsx) or register your first family manually."
            ),
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#FFFFFF",
            justify="left",
        )
        lbl_empty_desc.pack(anchor="w", pady=(4, 12))

        btn_empty_box = tk.Frame(self.empty_state_frame, bg="#FFFFFF")
        btn_empty_box.pack(anchor="w")

        tk.Button(
            btn_empty_box,
            text="📥 Import Client Dataset (.csv / .xlsx)",
            font=("Segoe UI", 9, "bold"),
            bg="#0D5C75",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=lambda: self.on_nav_click("data_import"),
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            btn_empty_box,
            text="➕ Register First Family",
            font=("Segoe UI", 9, "bold"),
            bg="#15803D",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.add_family,
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            btn_empty_box,
            text="⬇️ Download Sample Import Template",
            command=self._download_sample_template,
        ).pack(side="left")

        # 3. Action Toolbar
        toolbar = ttk.Frame(parent, padding=(20, 4, 20, 4))
        toolbar.pack(fill="x")
        self.dashboard_toolbar = toolbar

        ttk.Button(toolbar, text="⚡ Workspace", style="Primary.TButton", command=self.open_family_workspace).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="+ Add Family", command=self.add_family).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="✏️ Edit Family", command=self.edit_selected_family).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="🔄 Update Status", command=self.update_status).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="📄 Ticket PDF / Slip", command=self.manage_ticket_pdf).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="📥 Import Excel/CSV", command=self.import_file).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="📤 Export", command=self.export_menu).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="🗑️ Delete", command=self.delete_selected_family).pack(side="left", padx=(0, 6))

        # Priority & Reordering
        ttk.Label(toolbar, text="| Priority:").pack(side="left", padx=(8, 4))
        self.cb_quick_priority = ttk.Combobox(toolbar, values=config.PRIORITIES, state="readonly", width=8)
        self.cb_quick_priority.set("Normal")
        self.cb_quick_priority.pack(side="left", padx=(0, 4))
        ttk.Button(toolbar, text="Set", width=4, command=self._set_quick_priority).pack(side="left", padx=(0, 6))

        ttk.Button(toolbar, text="⬆ Up", width=5, command=lambda: self._shift_queue("up")).pack(side="left", padx=(0, 4))
        ttk.Button(toolbar, text="⬇ Down", width=6, command=lambda: self._shift_queue("down")).pack(side="left", padx=(0, 6))

        ttk.Button(toolbar, text="🔄 Refresh", command=self.refresh).pack(side="right")

        # 4. Search & Filters Bar
        filter_bar = ttk.Frame(parent, padding=(20, 4, 20, 6))
        filter_bar.pack(fill="x")

        ttk.Label(filter_bar, text="🔍 Search:").pack(side="left", padx=(0, 4))
        self.ent_search = ttk.Entry(filter_bar, width=22)
        self.ent_search.pack(side="left", padx=(0, 10))
        self.ent_search.bind("<KeyRelease>", lambda e: self.apply_filters())

        ttk.Label(filter_bar, text="Booking Status:").pack(side="left", padx=(0, 4))
        self.filter_status = ttk.Combobox(filter_bar, values=["All"] + config.BOOKING_STATUSES, state="readonly", width=12)
        self.filter_status.set("All")
        self.filter_status.pack(side="left", padx=(0, 10))
        self.filter_status.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Label(filter_bar, text="Payment:").pack(side="left", padx=(0, 4))
        self.filter_payment = ttk.Combobox(filter_bar, values=["All"] + config.PAYMENT_STATUSES, state="readonly", width=12)
        self.filter_payment.set("All")
        self.filter_payment.pack(side="left", padx=(0, 10))
        self.filter_payment.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Label(filter_bar, text="Quota:").pack(side="left", padx=(0, 4))
        self.filter_quota = ttk.Combobox(filter_bar, values=["All"] + config.BOOKING_TYPES, state="readonly", width=9)
        self.filter_quota.set("All")
        self.filter_quota.pack(side="left", padx=(0, 10))
        self.filter_quota.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Label(filter_bar, text="Sort:").pack(side="left", padx=(0, 4))
        self.sort_option = ttk.Combobox(
            filter_bar,
            values=["Queue Priority", "Date (Asc)", "Date (Desc)", "Family Name", "Created Date"],
            state="readonly",
            width=14,
        )
        self.sort_option.set("Queue Priority")
        self.sort_option.pack(side="left", padx=(0, 10))
        self.sort_option.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Button(filter_bar, text="Reset", command=self.reset_filters).pack(side="left")

        # 5. Queue Treeview Table
        body = ttk.Frame(parent, padding=(20, 4, 20, 8))
        body.pack(fill="both", expand=True)

        cols = (
            "priority",
            "code",
            "family",
            "contact",
            "phone",
            "pilgrims",
            "donation",
            "booking",
            "date",
            "status",
            "payment",
            "ticket",
        )
        self.tree = ttk.Treeview(body, columns=cols, show="headings", selectmode="browse")

        headings = {
            "priority": "Priority",
            "code": "Family ID",
            "family": "Family Name",
            "contact": "Primary Contact",
            "phone": "Phone",
            "pilgrims": "Devotees",
            "donation": "Donation (₹)",
            "booking": "Quota",
            "date": "Preferred Date",
            "status": "Booking Status",
            "payment": "Payment Status",
            "ticket": "Ticket PDF",
        }
        widths = {
            "priority": 85,
            "code": 125,
            "family": 160,
            "contact": 135,
            "phone": 110,
            "pilgrims": 75,
            "donation": 105,
            "booking": 85,
            "date": 115,
            "status": 125,
            "payment": 125,
            "ticket": 100,
        }

        for c in cols:
            self.tree.heading(c, text=headings[c])
            align = "center" if c in ("priority", "pilgrims", "booking", "date", "ticket") else "w"
            if c == "donation":
                align = "e"
            self.tree.column(c, width=widths[c], anchor=align)

        y_scroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(body, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        # Tags
        self.tree.tag_configure("booked", background="#ECFDF5", foreground="#065F46")
        self.tree.tag_configure("in_progress", background="#F0F9FF", foreground="#0369A1")
        self.tree.tag_configure("cancelled", background="#FEF2F2", foreground="#991B1B")
        self.tree.tag_configure("urgent", background="#FFF1F2", foreground="#BE123C")

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="⚡ Open Family Booking Workspace", command=self.open_family_workspace)
        self.context_menu.add_command(label="⚡ Quick Assisted Booking Assistant", command=self.open_assisted_booking)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✏️ Edit Family & Devotees", command=self.edit_selected_family)
        self.context_menu.add_command(label="🔄 Update Status & Payment", command=self.update_status)
        self.context_menu.add_command(label="📄 Attach / Open Ticket PDF", command=self.manage_ticket_pdf)
        self.context_menu.add_command(label="📜 View Family Queue History", command=self.show_family_history)
        self.context_menu.add_command(label="🖨️ Generate Devotee Summary Slip", command=self.quick_generate_slip)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="⬆ Move Up in Queue", command=lambda: self._shift_queue("up"))
        self.context_menu.add_command(label="⬇ Move Down in Queue", command=lambda: self._shift_queue("down"))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete Family", command=self.delete_selected_family)

        # 6. Footer
        footer = ttk.Frame(parent, padding=(20, 2, 20, 10))
        footer.pack(fill="x")
        self.lbl_shown_count = ttk.Label(footer, text="Showing 0 families", font=("Segoe UI", 9), foreground="#64748B")
        self.lbl_shown_count.pack(side="left")

        sec_notice = ttk.Label(
            footer,
            text="🔒 Client Security: TTD portal login, CAPTCHA, OTP, and payments remain under manual operator control.",
            font=("Segoe UI", 8, "italic"),
            foreground="#94A3B8",
        )
        sec_notice.pack(side="right")

    # ---------------------------------------------------------
    # VIEW 2: Families & Devotees Master-Detail View
    # ---------------------------------------------------------
    def _build_families_view(self, parent):
        top = ttk.Frame(parent, padding=(20, 14, 20, 10))
        top.pack(fill="x")
        ttk.Label(top, text="Families & Pilgrim Directory", style="Header.TLabel").pack(anchor="w")
        ttk.Label(top, text="Browse all registered families and inspect devotee rosters", style="Sub.TLabel").pack(anchor="w")

        body = ttk.PanedWindow(parent, orient="horizontal")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        # Left: Families Tree
        left_frame = ttk.Frame(body, padding=4)
        body.add(left_frame, weight=1)

        f_cols = ("code", "name", "phone", "devotees")
        self.fam_tree = ttk.Treeview(left_frame, columns=f_cols, show="headings", selectmode="browse")
        self.fam_tree.heading("code", text="Family ID")
        self.fam_tree.heading("name", text="Family Name")
        self.fam_tree.heading("phone", text="Phone")
        self.fam_tree.heading("devotees", text="Devotees")
        self.fam_tree.column("code", width=110)
        self.fam_tree.column("name", width=150)
        self.fam_tree.column("phone", width=105)
        self.fam_tree.column("devotees", width=65, anchor="center")

        f_scroll = ttk.Scrollbar(left_frame, orient="vertical", command=self.fam_tree.yview)
        self.fam_tree.configure(yscrollcommand=f_scroll.set)
        self.fam_tree.pack(side="left", fill="both", expand=True)
        f_scroll.pack(side="right", fill="y")
        self.fam_tree.bind("<<TreeviewSelect>>", self._on_family_selected_in_directory)

        # Right: Devotees Details Panel
        self.right_detail_frame = ttk.LabelFrame(body, text=" Devotee Details ", padding=12)
        body.add(self.right_detail_frame, weight=2)

        p_cols = ("idx", "name", "age", "gender", "id_proof", "last4")
        self.p_detail_tree = ttk.Treeview(self.right_detail_frame, columns=p_cols, show="headings")
        self.p_detail_tree.heading("idx", text="#")
        self.p_detail_tree.heading("name", text="Full Name")
        self.p_detail_tree.heading("age", text="Age")
        self.p_detail_tree.heading("gender", text="Gender")
        self.p_detail_tree.heading("id_proof", text="ID Proof")
        self.p_detail_tree.heading("last4", text="Last 4")
        self.p_detail_tree.column("idx", width=35, anchor="center")
        self.p_detail_tree.column("name", width=180)
        self.p_detail_tree.column("age", width=55, anchor="center")
        self.p_detail_tree.column("gender", width=75, anchor="center")
        self.p_detail_tree.column("id_proof", width=110)
        self.p_detail_tree.column("last4", width=80, anchor="center")

        p_scroll = ttk.Scrollbar(self.right_detail_frame, orient="vertical", command=self.p_detail_tree.yview)
        self.p_detail_tree.configure(yscrollcommand=p_scroll.set)
        self.p_detail_tree.pack(fill="both", expand=True)
        p_scroll.pack(side="right", fill="y")

    def _on_family_selected_in_directory(self, event=None):
        sel = self.fam_tree.selection()
        if not sel:
            return
        fid = int(sel[0])
        for item in self.p_detail_tree.get_children():
            self.p_detail_tree.delete(item)
        pilgrims = get_family_pilgrims(fid)
        for idx, p in enumerate(pilgrims, start=1):
            self.p_detail_tree.insert("", "end", values=(
                idx,
                p["full_name"],
                p["age"] if p["age"] is not None else "-",
                p["gender"],
                p["id_proof_type"],
                p["id_proof_last4"] or "-",
            ))

    # ---------------------------------------------------------
    # VIEW 3: Import & Export Hub
    # ---------------------------------------------------------
    def _build_import_export_view(self, parent):
        top = ttk.Frame(parent, padding=(20, 14, 20, 10))
        top.pack(fill="x")
        ttk.Label(top, text="Data Import & Export Center", style="Header.TLabel").pack(anchor="w")
        ttk.Label(top, text="Native Excel (.xlsx) and CSV batch operations with pre-import preview", style="Sub.TLabel").pack(anchor="w")

        hub_frame = ttk.Frame(parent, padding=20)
        hub_frame.pack(fill="both", expand=True)

        # Left: Import Card
        card_import = ttk.LabelFrame(hub_frame, text=" 📥 Import Records with Visual Preview ", padding=16)
        card_import.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(card_import, text="Import multiple families and devotees in bulk.", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 8))
        ttk.Label(card_import, text="• Supports Excel (.xlsx) & CSV files\n• Automatic column synonym matching\n• Visual preview and duplicate detection before saving\n• Clear validation and error alerts", font=("Segoe UI", 9), foreground="#64748B").pack(anchor="w", pady=(0, 16))

        ttk.Button(card_import, text="📂 Select Excel / CSV File to Preview & Import", style="Primary.TButton", command=self.import_file).pack(fill="x", pady=6)
        ttk.Button(card_import, text="⚡ Open Advanced DATA IMPORT Wizard", command=lambda: self.on_nav_click("data_import")).pack(fill="x", pady=6)
        ttk.Button(card_import, text="⬇️ Download Sample Excel Import Template", command=self._download_sample_template).pack(fill="x", pady=6)
        ttk.Button(card_import, text="🧹 Database Cleanup & Mock Data Purge", command=lambda: DataCleanupDialog(self, self)).pack(fill="x", pady=6)

        # Right: Export Card
        card_export = ttk.LabelFrame(hub_frame, text=" 📤 Export Records ", padding=16)
        card_export.pack(side="right", fill="both", expand=True, padx=(10, 0))

        ttk.Label(card_export, text="Export complete database records with devotee rosters.", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 8))
        ttk.Label(card_export, text="• Styled Excel (.xlsx) with auto-column widths\n• Clean UTF-8 CSV exports with full fields\n• Includes booking statuses, payment states and tickets\n• Single-click backup export", font=("Segoe UI", 9), foreground="#64748B").pack(anchor="w", pady=(0, 16))

        ttk.Button(card_export, text="📊 Export All to Excel Workbook (.xlsx)", command=self._export_excel).pack(fill="x", pady=6)
        ttk.Button(card_export, text="📄 Export All to CSV File (.csv)", command=self._export_csv).pack(fill="x", pady=6)

    # ---------------------------------------------------------
    # VIEW 4: Reports & Operational Analytics
    # ---------------------------------------------------------
    def _build_reports_view(self, parent):
        top = ttk.Frame(parent, padding=(20, 14, 20, 8))
        top.pack(fill="x")

        h_left = ttk.Frame(top)
        h_left.pack(side="left")
        ttk.Label(h_left, text="Reports & Operational Analytics", style="Header.TLabel").pack(anchor="w")
        ttk.Label(h_left, text="Daily booking summaries, payment breakdowns, and devotee demographic reports", style="Sub.TLabel").pack(anchor="w")

        ctrl_bar = ttk.Frame(parent, padding=(20, 4, 20, 8))
        ctrl_bar.pack(fill="x")

        ttk.Label(ctrl_bar, text="Select Report:").pack(side="left", padx=(0, 6))
        self.report_type_cb = ttk.Combobox(
            ctrl_bar,
            values=[
                "Daily Completed Bookings",
                "Weekly Operational Analysis",
                "Monthly Executive Summary",
                "Booking Status Summary",
                "Pending Families in Queue",
                "Failed or Unavailable Bookings",
                "Payment Status Breakdown",
                "Total Pilgrims Demographics",
            ],
            state="readonly",
            width=30,
        )
        self.report_type_cb.set("Daily Completed Bookings")
        self.report_type_cb.pack(side="left", padx=(0, 10))
        self.report_type_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_reports_view())

        ttk.Button(ctrl_bar, text="🔄 Generate", command=self._refresh_reports_view).pack(side="left", padx=(0, 6))
        ttk.Button(ctrl_bar, text="📊 Export CSV", command=self._export_current_report_csv).pack(side="left", padx=(0, 6))
        ttk.Button(ctrl_bar, text="📄 Printable PDF", command=self._export_current_report_pdf).pack(side="left", padx=(0, 6))
        ttk.Button(ctrl_bar, text="🔍 Reconcile & Verify Totals", command=self._verify_database_totals).pack(side="left")

        # Report Data Table
        tbl_frame = ttk.Frame(parent, padding=(20, 4, 20, 14))
        tbl_frame.pack(fill="both", expand=True)

        self.rep_tree = ttk.Treeview(tbl_frame, show="headings", selectmode="browse")
        y_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.rep_tree.yview)
        x_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.rep_tree.xview)
        self.rep_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.rep_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        # Bottom info
        self.lbl_rep_summary = ttk.Label(parent, text="Ready", padding=(20, 0, 20, 10), font=("Segoe UI", 9, "bold"), foreground="#0D5C75")
        self.lbl_rep_summary.pack(anchor="w")

    def _refresh_reports_view(self):
        rep_name = self.report_type_cb.get()

        # Clear existing
        for item in self.rep_tree.get_children():
            self.rep_tree.delete(item)

        if rep_name == "Daily Completed Bookings":
            cols = ("date", "families", "pilgrims", "donation")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("date", text="Booking Date")
            self.rep_tree.heading("families", text="Families Booked")
            self.rep_tree.heading("pilgrims", text="Devotees Booked")
            self.rep_tree.heading("donation", text="Donation Collected (₹)")
            self.rep_tree.column("date", width=160, anchor="center")
            self.rep_tree.column("families", width=140, anchor="center")
            self.rep_tree.column("pilgrims", width=140, anchor="center")
            self.rep_tree.column("donation", width=180, anchor="e")

            data = get_daily_completed_report()
            tot_fam = sum(r["families_booked"] for r in data)
            tot_p = sum(r["pilgrims_booked"] for r in data)
            tot_don = sum(r["total_donation"] for r in data)
            for r in data:
                self.rep_tree.insert("", "end", values=(
                    r["booking_date"],
                    r["families_booked"],
                    r["pilgrims_booked"],
                    f"₹{r['total_donation']:,.2f}",
                ))
            self.lbl_rep_summary.config(text=f"Total: {tot_fam} family(ies) booked, {tot_p} devotee(s), ₹{tot_don:,.2f} donation recorded")

        elif rep_name == "Weekly Operational Analysis":
            cols = ("week", "families", "booked", "pending", "pilgrims", "amount")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("week", text="Booking Week")
            self.rep_tree.heading("families", text="Total Families")
            self.rep_tree.heading("booked", text="Booked")
            self.rep_tree.heading("pending", text="Pending")
            self.rep_tree.heading("pilgrims", text="Devotees")
            self.rep_tree.heading("amount", text="Booked Donations (₹)")

            self.rep_tree.column("week", width=120, anchor="center")
            self.rep_tree.column("families", width=120, anchor="center")
            self.rep_tree.column("booked", width=100, anchor="center")
            self.rep_tree.column("pending", width=100, anchor="center")
            self.rep_tree.column("pilgrims", width=110, anchor="center")
            self.rep_tree.column("amount", width=160, anchor="e")

            data = get_weekly_report()
            for r in data:
                self.rep_tree.insert("", "end", values=(
                    r["booking_week"],
                    r["total_families"],
                    r["booked_families"],
                    r["pending_families"],
                    r["total_pilgrims"],
                    f"₹{r['booked_donation']:,.2f}",
                ))
            self.lbl_rep_summary.config(text=f"Weekly Summary: {len(data)} calendar week(s) recorded")

        elif rep_name == "Monthly Executive Summary":
            cols = ("month", "families", "booked", "cancelled", "pilgrims", "amount", "total_don")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("month", text="Month")
            self.rep_tree.heading("families", text="Total Families")
            self.rep_tree.heading("booked", text="Booked")
            self.rep_tree.heading("cancelled", text="Cancelled")
            self.rep_tree.heading("pilgrims", text="Devotees")
            self.rep_tree.heading("amount", text="Booked Amount (₹)")
            self.rep_tree.heading("total_don", text="Total Registered (₹)")

            self.rep_tree.column("month", width=110, anchor="center")
            self.rep_tree.column("families", width=110, anchor="center")
            self.rep_tree.column("booked", width=95, anchor="center")
            self.rep_tree.column("cancelled", width=95, anchor="center")
            self.rep_tree.column("pilgrims", width=100, anchor="center")
            self.rep_tree.column("amount", width=140, anchor="e")
            self.rep_tree.column("total_don", width=140, anchor="e")

            data = get_monthly_report()
            for r in data:
                self.rep_tree.insert("", "end", values=(
                    r["booking_month"],
                    r["total_families"],
                    r["booked_families"],
                    r["cancelled_families"],
                    r["total_pilgrims"],
                    f"₹{r['booked_donation']:,.2f}",
                    f"₹{r['total_donation']:,.2f}",
                ))
            self.lbl_rep_summary.config(text=f"Monthly Summary: {len(data)} calendar month(s) recorded")

        elif rep_name == "Booking Status Summary":
            cols = ("status", "families", "pilgrims", "donation", "tickets")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("status", text="Booking Status")
            self.rep_tree.heading("families", text="Total Families")
            self.rep_tree.heading("pilgrims", text="Total Devotees")
            self.rep_tree.heading("donation", text="Donation Amount (₹)")
            self.rep_tree.heading("tickets", text="Tickets Attached")

            self.rep_tree.column("status", width=140, anchor="w")
            self.rep_tree.column("families", width=120, anchor="center")
            self.rep_tree.column("pilgrims", width=120, anchor="center")
            self.rep_tree.column("donation", width=160, anchor="e")
            self.rep_tree.column("tickets", width=130, anchor="center")

            data = get_booking_status_summary_report()
            for r in data:
                self.rep_tree.insert("", "end", values=(
                    r["status"],
                    r["family_count"],
                    r["pilgrim_count"],
                    f"₹{r['total_donation']:,.2f}",
                    r["tickets_attached"],
                ))
            self.lbl_rep_summary.config(text=f"Status Overview: {len(data)} status category(ies)")

        elif rep_name == "Pending Families in Queue":
            cols = ("code", "name", "contact", "phone", "pilgrims", "date", "priority", "created")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("code", text="Family ID")
            self.rep_tree.heading("name", text="Family Name")
            self.rep_tree.heading("contact", text="Primary Contact")
            self.rep_tree.heading("phone", text="Phone")
            self.rep_tree.heading("pilgrims", text="Devotees")
            self.rep_tree.heading("date", text="Preferred Date")
            self.rep_tree.heading("priority", text="Priority")
            self.rep_tree.heading("created", text="Created At")

            self.rep_tree.column("code", width=120)
            self.rep_tree.column("name", width=150)
            self.rep_tree.column("contact", width=130)
            self.rep_tree.column("phone", width=105)
            self.rep_tree.column("pilgrims", width=75, anchor="center")
            self.rep_tree.column("date", width=110, anchor="center")
            self.rep_tree.column("priority", width=90, anchor="center")
            self.rep_tree.column("created", width=140, anchor="center")

            data = get_pending_families_report()
            tot_p = sum(r["pilgrim_count"] for r in data)
            for r in data:
                self.rep_tree.insert("", "end", values=(
                    r["family_code"],
                    r["family_name"],
                    r["contact_name"],
                    r["phone"],
                    r["pilgrim_count"],
                    r["preferred_date"] or "—",
                    r["priority"],
                    r["created_at"],
                ))
            self.lbl_rep_summary.config(text=f"Queue Status: {len(data)} pending family(ies) ({tot_p} devotees awaiting booking)")

        elif rep_name == "Failed or Unavailable Bookings":
            cols = ("code", "name", "phone", "status", "date", "pilgrims", "notes")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("code", text="Family ID")
            self.rep_tree.heading("name", text="Family Name")
            self.rep_tree.heading("phone", text="Phone")
            self.rep_tree.heading("status", text="Status")
            self.rep_tree.heading("date", text="Preferred Date")
            self.rep_tree.heading("pilgrims", text="Devotees")
            self.rep_tree.heading("notes", text="Reason / Notes")

            self.rep_tree.column("code", width=120)
            self.rep_tree.column("name", width=150)
            self.rep_tree.column("phone", width=110)
            self.rep_tree.column("status", width=100, anchor="center")
            self.rep_tree.column("date", width=110, anchor="center")
            self.rep_tree.column("pilgrims", width=75, anchor="center")
            self.rep_tree.column("notes", width=220)

            data = get_failed_or_unavailable_report()
            for r in data:
                self.rep_tree.insert("", "end", values=(
                    r["family_code"],
                    r["family_name"],
                    r["phone"],
                    r["status"],
                    r["preferred_date"] or "—",
                    r["pilgrim_count"],
                    r["notes"] or "",
                ))
            self.lbl_rep_summary.config(text=f"Total: {len(data)} family record(s) marked Unavailable or Cancelled")

        elif rep_name == "Payment Status Breakdown":
            cols = ("status", "families", "pilgrims", "total_amt", "with_ref")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("status", text="Payment Status")
            self.rep_tree.heading("families", text="Family Count")
            self.rep_tree.heading("pilgrims", text="Devotees")
            self.rep_tree.heading("total_amt", text="Total Amount (₹)")
            self.rep_tree.heading("with_ref", text="With Transaction Ref")

            self.rep_tree.column("status", width=160)
            self.rep_tree.column("families", width=130, anchor="center")
            self.rep_tree.column("pilgrims", width=130, anchor="center")
            self.rep_tree.column("total_amt", width=170, anchor="e")
            self.rep_tree.column("with_ref", width=160, anchor="center")

            data = get_payment_status_report()
            tot_amt = sum(r["total_amount"] for r in data)
            for r in data:
                self.rep_tree.insert("", "end", values=(
                    r["payment_status"],
                    r["family_count"],
                    r["pilgrim_count"],
                    f"₹{r['total_amount']:,.2f}",
                    r["with_ref_count"],
                ))
            self.lbl_rep_summary.config(text=f"Financial Overview: Total registered donation amount across all states: ₹{tot_amt:,.2f}")

        elif rep_name == "Total Pilgrims Demographics":
            cols = ("category", "subcategory", "count")
            self.rep_tree["columns"] = cols
            self.rep_tree.heading("category", text="Category")
            self.rep_tree.heading("subcategory", text="Breakdown")
            self.rep_tree.heading("count", text="Devotee Count")

            self.rep_tree.column("category", width=180)
            self.rep_tree.column("subcategory", width=200)
            self.rep_tree.column("count", width=140, anchor="center")

            data = get_total_pilgrims_report()
            self.rep_tree.insert("", "end", values=("Total Devotees", "All Registered", data["total_pilgrims"]))
            for g, cnt in data["genders"].items():
                self.rep_tree.insert("", "end", values=("Gender", g, cnt))
            for ag, cnt in data["age_groups"].items():
                self.rep_tree.insert("", "end", values=("Age Group", ag, cnt))
            for q, cnt in data["quotas"].items():
                self.rep_tree.insert("", "end", values=("Quota Distribution", q, cnt))

            self.lbl_rep_summary.config(text=f"Demographics: Total of {data['total_pilgrims']} devotee(s) across all families")

    def _export_current_report_csv(self):
        rep_name = self.report_type_cb.get()
        type_key_map = {
            "Daily Completed Bookings": "daily_completed",
            "Weekly Operational Analysis": "weekly",
            "Monthly Executive Summary": "monthly",
            "Booking Status Summary": "booking_status_summary",
            "Pending Families in Queue": "pending_families",
            "Failed or Unavailable Bookings": "failed_or_unavailable",
            "Payment Status Breakdown": "payment_status",
            "Total Pilgrims Demographics": "total_pilgrims",
        }
        key = type_key_map.get(rep_name, "daily_completed")
        filename = f"Srivani_Report_{key}_{datetime.now():%Y%m%d_%H%M}.csv"

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Report to CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files (*.csv)", "*.csv")],
            initialfile=filename,
        )
        if not path:
            return

        try:
            cnt = export_report_to_csv(key, path)
            messagebox.showinfo("Export Complete", f"Successfully exported {cnt} report row(s) to:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export report:\n{e}", parent=self)

    def _export_current_report_pdf(self):
        rep_name = self.report_type_cb.get()
        type_key_map = {
            "Daily Completed Bookings": "daily_completed",
            "Weekly Operational Analysis": "weekly",
            "Monthly Executive Summary": "monthly",
            "Booking Status Summary": "booking_status_summary",
            "Pending Families in Queue": "pending_families",
            "Failed or Unavailable Bookings": "failed_or_unavailable",
            "Payment Status Breakdown": "payment_status",
            "Total Pilgrims Demographics": "total_pilgrims",
        }
        key = type_key_map.get(rep_name, "daily_completed")
        filename = f"Srivani_Executive_Report_{key}_{datetime.now():%Y%m%d_%H%M}.pdf"

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Printable PDF Report",
            defaultextension=".pdf",
            filetypes=[("PDF Documents (*.pdf)", "*.pdf")],
            initialfile=filename,
        )
        if not path:
            return

        ok, msg = generate_printable_pdf_report(key, path)
        if ok:
            ans = messagebox.askyesno(
                "PDF Generated Successfully",
                f"Printable PDF report has been created:\n{path}\n\nWould you like to open it now?",
                parent=self,
            )
            if ans:
                try:
                    os.startfile(path)
                except Exception:
                    webbrowser.open(path)
        else:
            messagebox.showerror("PDF Export Error", f"Failed to generate PDF report:\n{msg}", parent=self)

    def _verify_database_totals(self):
        ok_db, db_issues = check_database_integrity()
        recon = validate_report_totals()

        msg = (
            f"=== DATABASE INTEGRITY & TOTALS RECONCILIATION ===\n\n"
            f"• SQLite PRAGMA Integrity: {'✅ Passed (OK)' if ok_db else '❌ Corrupt'}\n"
            f"• Foreign Key Integrity: {'✅ Valid (0 violations)' if not [i for i in db_issues if 'Foreign' in i] else '❌ Violations Detected'}\n"
            f"• Total Families Registered: {recon['total_families']}\n"
            f"• Total Devotees (Pilgrims): {recon['total_pilgrims']}\n"
            f"• Orphaned Pilgrim Records: {recon['orphaned_pilgrims']} (Expected: 0)\n"
            f"• Total Donation Sum: ₹{recon['total_donation']:,.2f}\n\n"
            f"Reconciliation Status: {'✅ All Totals Match Database Records' if recon['is_valid'] and ok_db else '⚠️ Reconciliation Anomalies Detected'}\n"
        )
        if recon["anomalies"]:
            msg += "\nAnomalies:\n" + "\n".join(f"- {a}" for a in recon["anomalies"])

        messagebox.showinfo("Database Reconciliation Verification", msg, parent=self)

    def open_family_workspace(self, family_id: Optional[int] = None):
        fid = family_id or self.selected_id()
        if fid is None:
            # Pick first family in queue if available
            queue_rows = get_all_families(sort_by="queue")
            if queue_rows:
                fid = queue_rows[0]["id"]
            else:
                messagebox.showinfo("Workspace", "No families currently available. Please add or import a family first.", parent=self)
                return
        BookingWorkspaceDialog(self, fid, on_update_callback=self.refresh)

    # ---------------------------------------------------------
    # VIEW 5: Queue History & Activity Audit Log
    # ---------------------------------------------------------
    def _build_history_view(self, parent):
        top = ttk.Frame(parent, padding=(20, 14, 20, 8))
        top.pack(fill="x")

        h_left = ttk.Frame(top)
        h_left.pack(side="left")
        ttk.Label(h_left, text="Queue & Activity History", style="Header.TLabel").pack(anchor="w")
        ttk.Label(h_left, text="Preserved chronological audit trail of all queue events and status transitions", style="Sub.TLabel").pack(anchor="w")

        ttk.Button(top, text="🔄 Refresh Log", command=self._refresh_history_view).pack(side="right")

        tbl_frame = ttk.Frame(parent, padding=(20, 4, 20, 14))
        tbl_frame.pack(fill="both", expand=True)

        cols = ("time", "action", "code", "family", "status_change", "priority_change", "notes")
        self.hist_tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", selectmode="browse")

        headings = {
            "time": "Timestamp",
            "action": "Event Type",
            "code": "Family ID",
            "family": "Family Name",
            "status_change": "Status Change",
            "priority_change": "Priority Change",
            "notes": "Details / Notes",
        }
        widths = {
            "time": 140,
            "action": 130,
            "code": 115,
            "family": 140,
            "status_change": 140,
            "priority_change": 115,
            "notes": 240,
        }

        for c in cols:
            self.hist_tree.heading(c, text=headings[c])
            self.hist_tree.column(c, width=widths[c], anchor="center" if c in ("time", "action") else "w")

        y_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.hist_tree.yview)
        x_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.hist_tree.xview)
        self.hist_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.hist_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

    def _refresh_history_view(self):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)

        events = get_queue_history(limit=250)
        for ev in events:
            st_change = "—"
            if ev["old_status"] or ev["new_status"]:
                st_change = f"{ev['old_status'] or 'None'} ➔ {ev['new_status'] or 'None'}"

            pr_change = "—"
            if ev["old_priority"] or ev["new_priority"]:
                pr_change = f"{ev['old_priority'] or 'None'} ➔ {ev['new_priority'] or 'None'}"

            self.hist_tree.insert("", "end", values=(
                ev["created_at"],
                ev["action"],
                ev["family_code"] or "—",
                ev["family_name"] or "—",
                st_change,
                pr_change,
                ev["notes"] or "",
            ))

    # ---------------------------------------------------------
    # Data Refresh & Filtering
    # ---------------------------------------------------------
    def refresh(self):
        """Update dashboard summary cards, license notification banner, and table data."""
        stats = get_stats()
        self.cards["total_families"].config(text=str(stats["total_families"]))
        self.cards["total_pilgrims"].config(text=str(stats["total_pilgrims"]))
        self.cards["pending_families"].config(text=str(stats["pending_families"]))
        self.cards["in_progress"].config(text=str(stats["in_progress"]))
        self.cards["booked"].config(text=str(stats["booked"]))
        self.cards["cancelled"].config(text=str(stats["cancelled"]))

        # License Expiry & Warning Notification Check
        try:
            lic = get_license_info()
            if lic.get("is_warning_period") or lic.get("is_expired"):
                self.license_banner.pack(fill="x", padx=20, pady=(6, 0), before=self.stats_frame)
                self.lbl_lic_banner.config(text=f"⚠️ {lic.get('warning_message', 'License Notice')}")
                if lic.get("is_expired"):
                    self.license_banner.config(bg="#FEE2E2")
                    self.lbl_lic_banner.config(fg="#991B1B", bg="#FEE2E2")
                    self.btn_lic_banner.config(bg="#DC2626")
                else:
                    self.license_banner.config(bg="#FEF3C7")
                    self.lbl_lic_banner.config(fg="#92400E", bg="#FEF3C7")
                    self.btn_lic_banner.config(bg="#D97706")
            else:
                self.license_banner.pack_forget()
        except Exception:
            pass

        # Clean Empty State Handling (Phase 9)
        if hasattr(self, "empty_state_frame") and hasattr(self, "dashboard_toolbar"):
            if stats["total_families"] == 0:
                self.empty_state_frame.pack(fill="x", padx=20, pady=(4, 8), before=self.dashboard_toolbar)
            else:
                self.empty_state_frame.pack_forget()

        self.apply_filters()
        self._refresh_families_directory()

        if hasattr(self, "views") and "analytics" in self.views:
            if hasattr(self.views["analytics"], "refresh_analytics"):
                self.views["analytics"].refresh_analytics()

    def _refresh_families_directory(self):
        for item in self.fam_tree.get_children():
            self.fam_tree.delete(item)
        families = get_all_families(sort_by="name")
        for f in families:
            self.fam_tree.insert("", "end", iid=str(f["id"]), values=(
                f["family_code"],
                f["family_name"],
                f["phone"] or "—",
                f["pilgrim_count"],
            ))

    def reset_filters(self):
        self.ent_search.delete(0, tk.END)
        self.filter_status.set("All")
        self.filter_payment.set("All")
        self.filter_quota.set("All")
        self.sort_option.set("Queue Priority")
        self.refresh()

    def apply_filters(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_term = self.ent_search.get().strip()
        st = self.filter_status.get()
        pm = self.filter_payment.get()
        qt = self.filter_quota.get()

        sort_map = {
            "Queue Priority": "queue",
            "Date (Asc)": "date_asc",
            "Date (Desc)": "date_desc",
            "Family Name": "name",
            "Created Date": "created_desc",
        }
        sort_by = sort_map.get(self.sort_option.get(), "queue")

        rows = get_all_families(
            search=search_term,
            status=st,
            payment_status=pm,
            booking_type=qt,
            sort_by=sort_by,
        )

        for r in rows:
            tag = ""
            if r["status"] == "Booked":
                tag = "booked"
            elif r["status"] == "In progress":
                tag = "in_progress"
            elif r["status"] in ("Cancelled", "Unavailable"):
                tag = "cancelled"
            elif r["priority"] == "Urgent":
                tag = "urgent"

            ticket_icon = "📄 Yes" if (r["ticket_pdf_path"] and Path(r["ticket_pdf_path"]).exists()) else "—"

            priority_display = r["priority"]
            if priority_display == "Urgent":
                priority_display = "🔴 Urgent"
            elif priority_display == "High":
                priority_display = "🟠 High"

            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    priority_display,
                    r["family_code"],
                    r["family_name"],
                    r["contact_name"],
                    r["phone"],
                    r["pilgrim_count"],
                    f"{r['donation_amount']:,.2f}",
                    r["booking_type"],
                    r["preferred_date"] or "—",
                    r["status"],
                    r["payment_status"],
                    ticket_icon,
                ),
                tags=(tag,) if tag else (),
            )

        self.lbl_shown_count.config(text=f"Showing {len(rows)} families")

    # ---------------------------------------------------------
    # Actions & Dialogs
    # ---------------------------------------------------------
    def selected_id(self) -> Optional[int]:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Family", "Please select a family from the table first.")
            return None
        return int(sel[0])

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def on_double_click(self, event=None):
        self.edit_selected_family()

    def open_assisted_booking(self):
        sel = self.tree.selection()
        fid = int(sel[0]) if sel else None
        AssistedBookingAssistant(self, on_update_callback=self.refresh, initial_family_id=fid)

    def add_family(self):
        AddFamilyDialog(self, on_save_callback=self.refresh)

    def edit_selected_family(self):
        fid = self.selected_id()
        if fid is not None:
            EditFamilyDialog(self, fid, on_save_callback=self.refresh)

    def update_status(self):
        fid = self.selected_id()
        if fid is not None:
            UpdateStatusDialog(self, fid, on_save_callback=self.refresh)

    def manage_ticket_pdf(self):
        fid = self.selected_id()
        if fid is not None:
            TicketPDFDialog(self, fid, on_save_callback=self.refresh)

    def show_family_history(self):
        fid = self.selected_id()
        if fid is not None:
            QueueHistoryDialog(self, family_id=fid)

    def quick_generate_slip(self):
        fid = self.selected_id()
        if fid is None:
            return
        f = get_family(fid)
        pilgrims = [dict(p) for p in get_family_pilgrims(fid)]
        try:
            slip_path = generate_booking_slip_pdf(dict(f), pilgrims)
            if messagebox.askyesno("Generated", f"Devotee Summary Slip generated at:\n{slip_path}\n\nOpen it now?"):
                open_ticket_pdf(slip_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate slip: {e}")

    def delete_selected_family(self):
        fid = self.selected_id()
        if fid is None:
            return
        fam = get_family(fid)
        if not fam:
            return
        msg = f"Are you sure you want to delete family '{fam['family_name']}' ({fam['family_code']}) and all its devotees?\n\nThis action cannot be undone."
        if messagebox.askyesno("Confirm Delete", msg, default="no"):
            delete_family(fid)
            self.refresh()
            messagebox.showinfo("Deleted", "Family and devotee records removed.")

    def _set_quick_priority(self):
        fid = self.selected_id()
        if fid is None:
            return
        pri = self.cb_quick_priority.get()
        set_priority(fid, pri)
        self.refresh()

    def _shift_queue(self, direction: str):
        fid = self.selected_id()
        if fid is None:
            return
        shift_queue_order(fid, direction)
        self.refresh()
        if self.tree.exists(str(fid)):
            self.tree.selection_set(str(fid))
            self.tree.see(str(fid))

    def import_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Devotees File to Preview (Excel or CSV)",
            filetypes=[
                ("Excel & CSV Files", "*.xlsx *.xls *.csv"),
                ("Excel Workbooks (*.xlsx)", "*.xlsx"),
                ("CSV Files (*.csv)", "*.csv"),
                ("All Files", "*.*"),
            ]
        )
        if not path:
            return
        # Open visual ImportPreviewDialog with duplicate detection
        ImportPreviewDialog(self, path, on_success_callback=self.refresh)

    def export_menu(self):
        win = tk.Toplevel(self)
        win.title("Export Options")
        win.geometry("340x220")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Export Srivani Records", font=("Segoe UI", 11, "bold"), foreground="#1B365D").pack(anchor="w", pady=(0, 10))

        ttk.Button(frm, text="Export to Excel (.xlsx)", command=lambda: [win.destroy(), self._export_excel()]).pack(fill="x", pady=4)
        ttk.Button(frm, text="Export to CSV (.csv)", command=lambda: [win.destroy(), self._export_csv()]).pack(fill="x", pady=4)
        ttk.Button(frm, text="Download Sample Excel Template", command=lambda: [win.destroy(), self._download_sample_template()]).pack(fill="x", pady=4)

    def _export_excel(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile=f"Srivani_Bookings_{datetime.now():%Y%m%d}.xlsx",
        )
        if not path:
            return
        try:
            cnt = export_to_excel(path)
            messagebox.showinfo("Export Successful", f"Exported {cnt} devotee record(s) to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile=f"Srivani_Bookings_{datetime.now():%Y%m%d}.csv",
        )
        if not path:
            return
        try:
            cnt = export_to_csv(path)
            messagebox.showinfo("Export Successful", f"Exported {cnt} devotee record(s) to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _download_sample_template(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
            initialfile="Srivani_Import_Template.xlsx",
        )
        if not path:
            return
        try:
            create_sample_excel_template(path)
            messagebox.showinfo("Template Saved", f"Sample Excel import template saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Failed to Save Template", str(e))

if __name__ == "__main__":
    app = App(require_auth=True)
    app.mainloop()
