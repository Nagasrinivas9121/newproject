"""
SRIVANI BOOKING MANAGER - PHASE 9
Fast Booking Preparation Engine & Manual Booking Workspace

Components:
1. FastBookingDashboardView: High-level KPI dashboard, readiness summary, payment tracking, and recent activity.
2. ManualBookingWorkspaceDialog: Dedicated family workspace with 7-step checklist and 'OPEN OFFICIAL TTD WEBSITE' launcher.
3. DocumentManagementDialog: Supporting document attachments (.pdf, .png, .jpg, .jpeg) with preview and integrity checks.
4. BookingHistoryFrame: Filterable, searchable booking history with CSV and Excel exports.
5. BookingReadinessInspectorDialog: Detailed readiness checklist and missing information breakdown.

Strict Compliance:
- Strictly assisted booking preparation only.
- No automated TTD DOM interactions, no CAPTCHA solving, no browser injection.
- TTD portal opened in default browser only upon explicit user click.
"""

import os
import sys
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

import config
from database import (
    get_connection,
    get_family,
    get_family_pilgrims,
    get_all_families,
    get_family_documents,
    add_family_document,
    delete_family_document,
    update_family_readiness,
    update_family_payment_tracking,
    update_status_and_payment,
    get_fast_booking_dashboard_stats,
    log_queue_action,
)
from readiness_engine import (
    STATUS_NOT_STARTED,
    STATUS_INCOMPLETE,
    STATUS_READY_FOR_MANUAL_BOOKING,
    STATUS_BOOKING_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_CANCELLED,
    ALL_BOOKING_STATUSES,
    PAYMENT_NOT_PAID,
    PAYMENT_PENDING,
    PAYMENT_PAID,
    PAYMENT_FAILED,
    PAYMENT_REFUNDED,
    ALL_PAYMENT_STATUSES,
    calculate_booking_readiness,
    normalize_booking_status,
    normalize_payment_tracking_status,
)
from document_manager import (
    store_family_document,
    validate_document_file,
    open_document_preview,
)
from ticket_manager import store_ticket_pdf, open_ticket_pdf, generate_booking_slip_pdf


class FastBookingDashboardView(tk.Frame):
    """
    Phase 9: Fast Booking Dashboard.
    Displays:
    - Total families
    - Total pilgrims
    - Ready for booking (READY_FOR_MANUAL_BOOKING)
    - Incomplete profiles (INCOMPLETE)
    - Pending bookings
    - Completed bookings
    - Payment status breakdown (NOT_PAID, PAYMENT_PENDING, PAID, FAILED, REFUNDED)
    - Recent booking activity
    """

    def __init__(self, parent, app_controller):
        super().__init__(parent, bg="#F8FAFC")
        self.app = app_controller
        self._build_ui()

    def _build_ui(self):
        # 1. Header Banner
        header_frame = tk.Frame(self, bg="#FFFFFF", padx=24, pady=16, bd=1, relief="solid")
        header_frame.pack(fill="x", padx=16, pady=(16, 12))

        lbl_title = tk.Label(
            header_frame,
            text="🎯 FAST BOOKING PREPARATION DASHBOARD",
            font=("Segoe UI", 16, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            header_frame,
            text="Assisted Booking Readiness Engine • Strict Compliance Model • Official TTD Portal Assist",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Top Action Buttons
        btn_bar = tk.Frame(header_frame, bg="#FFFFFF")
        btn_bar.pack(anchor="e", pady=(8, 0))

        btn_refresh = tk.Button(
            btn_bar,
            text="🔄 Refresh Stats",
            font=("Segoe UI", 9, "bold"),
            bg="#F1F5F9",
            fg="#1E293B",
            bd=1,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.refresh_dashboard,
        )
        btn_refresh.pack(side="right", padx=(8, 0))

        btn_launch = tk.Button(
            btn_bar,
            text="⚡ Open Manual Workspace",
            font=("Segoe UI", 9, "bold"),
            bg="#D97706",
            fg="#FFFFFF",
            bd=0,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self._launch_workspace_for_selected,
        )
        btn_launch.pack(side="right")

        # 2. Main KPI Grid (2 rows x 3 columns)
        kpi_container = tk.Frame(self, bg="#F8FAFC")
        kpi_container.pack(fill="x", padx=16, pady=(0, 12))

        self.kpi_cards = {}
        cards_def = [
            ("total_fams", "TOTAL FAMILIES", "👥", "#0F172A", "#F8FAFC", "#E2E8F0"),
            ("total_pils", "TOTAL PILGRIMS", "🪪", "#0F172A", "#F8FAFC", "#E2E8F0"),
            ("ready", "READY FOR BOOKING", "✅", "#15803D", "#DCFCE7", "#86EFAC"),
            ("incomplete", "INCOMPLETE PROFILES", "⚠️", "#B45309", "#FEF3C7", "#FDE68A"),
            ("pending", "PENDING BOOKINGS", "⏳", "#0369A1", "#E0F2FE", "#7DD3FC"),
            ("completed", "COMPLETED BOOKINGS", "🎉", "#047857", "#D1FAE5", "#6EE7B7"),
        ]

        for i, (key, title, icon, fg_color, bg_color, border_color) in enumerate(cards_def):
            row = i // 3
            col = i % 3
            card = tk.Frame(kpi_container, bg=bg_color, bd=1, relief="solid", padx=16, pady=12)
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            kpi_container.grid_columnconfigure(col, weight=1)

            lbl_card_title = tk.Label(
                card,
                text=f"{icon} {title}",
                font=("Segoe UI", 8, "bold"),
                fg="#64748B",
                bg=bg_color,
            )
            lbl_card_title.pack(anchor="w")

            val_label = tk.Label(
                card,
                text="--",
                font=("Segoe UI", 22, "bold"),
                fg=fg_color,
                bg=bg_color,
            )
            val_label.pack(anchor="w", pady=(4, 0))
            self.kpi_cards[key] = val_label

        # 3. Two-Column Lower Section: Payment Tracking Breakdown & Recent Activity
        self.lower_container = tk.Frame(self, bg="#F8FAFC")
        lower_container = self.lower_container
        lower_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Empty State Onboarding Frame
        self.empty_state_frame = tk.Frame(self, bg="#FFFFFF", bd=1, relief="solid", padx=20, pady=16)
        lbl_e_title = tk.Label(
            self.empty_state_frame,
            text="✨ Welcome to Fast Booking Preparation",
            font=("Segoe UI", 12, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        lbl_e_title.pack(anchor="w")
        lbl_e_desc = tk.Label(
            self.empty_state_frame,
            text=(
                "No devotee records found. The database is clean and ready for your real client datasets.\n"
                "Import your CSV or Excel dataset, or add a devotee family to begin fast assisted preparation."
            ),
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#FFFFFF",
            justify="left",
        )
        lbl_e_desc.pack(anchor="w", pady=(4, 10))

        e_btn_box = tk.Frame(self.empty_state_frame, bg="#FFFFFF")
        e_btn_box.pack(anchor="w")

        tk.Button(
            e_btn_box,
            text="📥 Import Dataset (.csv / .xlsx)",
            font=("Segoe UI", 9, "bold"),
            bg="#0D5C75",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_import_click,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            e_btn_box,
            text="➕ Register Family",
            font=("Segoe UI", 9, "bold"),
            bg="#15803D",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_add_family_click,
        ).pack(side="left")

        # Left Column: Payment Status Summary
        left_box = tk.LabelFrame(
            lower_container,
            text=" 💳 Payment Tracking Status (Non-Financial Accounting) ",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
            padx=14,
            pady=12,
        )
        left_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.payment_labels = {}
        pay_rows = [
            (PAYMENT_NOT_PAID, "Not Paid", "#64748B"),
            (PAYMENT_PENDING, "Payment Pending", "#D97706"),
            (PAYMENT_PAID, "Paid / Reconciled", "#16A34A"),
            (PAYMENT_FAILED, "Failed / Review", "#DC2626"),
            (PAYMENT_REFUNDED, "Refunded", "#9333EA"),
        ]

        for p_key, p_label, p_color in pay_rows:
            p_row = tk.Frame(left_box, bg="#FFFFFF")
            p_row.pack(fill="x", pady=4)

            tk.Label(
                p_row,
                text=f"• {p_label}:",
                font=("Segoe UI", 9, "bold"),
                fg=p_color,
                bg="#FFFFFF",
            ).pack(side="left")

            count_lbl = tk.Label(
                p_row,
                text="0",
                font=("Segoe UI", 10, "bold"),
                fg="#0F172A",
                bg="#FFFFFF",
            )
            count_lbl.pack(side="right")
            self.payment_labels[p_key] = count_lbl

        compliance_box = tk.Frame(left_box, bg="#FEF3C7", bd=1, relief="solid", padx=10, pady=8)
        compliance_box.pack(fill="x", pady=(16, 0))

        tk.Label(
            compliance_box,
            text="⚠️ COMPLIANCE GUARANTEE",
            font=("Segoe UI", 8, "bold"),
            fg="#B45309",
            bg="#FEF3C7",
        ).pack(anchor="w")

        tk.Label(
            compliance_box,
            text="This application records status notes only. Banking credentials, OTPs, UPI PINs, and payment gateway tokens are never collected, processed, or stored.",
            font=("Segoe UI", 7),
            fg="#92400E",
            bg="#FEF3C7",
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        # Right Column: Recent Booking Activity Table
        right_box = tk.LabelFrame(
            lower_container,
            text=" 📜 Recent Booking Preparation Activity ",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
            padx=14,
            pady=12,
        )
        right_box.pack(side="right", fill="both", expand=True, padx=(8, 0))

        tree_scroll = ttk.Scrollbar(right_box)
        tree_scroll.pack(side="right", fill="y")

        cols = ("time", "family", "action", "notes")
        self.tree_activity = ttk.Treeview(
            right_box,
            columns=cols,
            show="headings",
            yscrollcommand=tree_scroll.set,
            height=8,
        )
        tree_scroll.config(command=self.tree_activity.yview)

        self.tree_activity.heading("time", text="Timestamp")
        self.tree_activity.heading("family", text="Family / ID")
        self.tree_activity.heading("action", text="Action")
        self.tree_activity.heading("notes", text="Operational Notes")

        self.tree_activity.column("time", width=110, anchor="w")
        self.tree_activity.column("family", width=120, anchor="w")
        self.tree_activity.column("action", width=120, anchor="w")
        self.tree_activity.column("notes", width=220, anchor="w")

        self.tree_activity.pack(fill="both", expand=True)

        self.refresh_dashboard()

    def refresh_dashboard(self):
        """Fetch real SQLite records and re-calculate Phase 9 KPI cards."""
        stats = get_fast_booking_dashboard_stats()

        self.kpi_cards["total_fams"].config(text=str(stats.get("total_families", 0)))
        self.kpi_cards["total_pils"].config(text=str(stats.get("total_pilgrims", 0)))
        self.kpi_cards["ready"].config(text=str(stats.get("ready_for_booking", 0)))
        self.kpi_cards["incomplete"].config(text=str(stats.get("incomplete_profiles", 0)))
        self.kpi_cards["pending"].config(text=str(stats.get("pending_bookings", 0)))
        self.kpi_cards["completed"].config(text=str(stats.get("completed_bookings", 0)))

        # Update payment status counters
        pay_counts = stats.get("payment_status", {})
        for p_key, lbl in self.payment_labels.items():
            lbl.config(text=str(pay_counts.get(p_key, 0)))

        # Update recent activity
        for item in self.tree_activity.get_children():
            self.tree_activity.delete(item)

        for act in stats.get("recent_activity", []):
            t_str = str(act.get("created_at") or "")
            if "T" in t_str:
                t_str = t_str.replace("T", " ")[:16]
            fam_label = f"{act.get('family_name') or 'Family'} ({act.get('family_code') or 'N/A'})"
            self.tree_activity.insert(
                "",
                "end",
                values=(
                    t_str,
                    fam_label,
                    act.get("action", ""),
                    act.get("notes", ""),
                ),
            )

        # Handle clean empty database state
        total_fams = stats.get("total_families", 0)
        if total_fams == 0:
            self.empty_state_frame.pack(fill="x", padx=16, pady=(0, 12), before=self.lower_container)
        else:
            self.empty_state_frame.pack_forget()

    def _on_import_click(self):
        if hasattr(self.app, "on_nav_click"):
            self.app.on_nav_click("data_import")

    def _on_add_family_click(self):
        if hasattr(self.app, "add_family"):
            self.app.add_family()

    def _launch_workspace_for_selected(self):
        """Prompt user or open workspace for the first pending/ready family."""
        fams = get_all_families()
        if not fams:
            messagebox.showinfo("No Families", "No family records found. Please add a family first.")
            return

        # Select first family that is ready or pending
        target = fams[0]
        for f in fams:
            st = normalize_booking_status(f.get("status"))
            if st in (STATUS_READY_FOR_MANUAL_BOOKING, STATUS_INCOMPLETE, STATUS_NOT_STARTED):
                target = f
                break

        ManualBookingWorkspaceDialog(
            parent=self.winfo_toplevel(),
            family_id=target["id"],
            on_update_callback=self.refresh_dashboard,
        )


class ManualBookingWorkspaceDialog(tk.Toplevel):
    """
    Module 6: Dedicated Manual Booking Workspace for each family.
    
    Features:
    - Display Family Details with one-click copy buttons
    - Pilgrim Roster with one-click copy buttons
    - Locally Configured Donation Amount with disclaimer
    - Document Checklist & Document Attachment Management
    - Booking Readiness Badge & Percentage Score
    - Button: 'OPEN OFFICIAL TTD WEBSITE' (opens official TTD website in default browser)
    - Manual 7-Step Booking Assistance Checklist requiring explicit user interaction
    - Booking Status and Payment Tracking updates
    """

    def __init__(self, parent, family_id: int, on_update_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.family_id = family_id
        self.on_update = on_update_callback
        raw_fam = get_family(family_id)
        if not raw_fam:
            messagebox.showerror("Error", f"Family ID {family_id} not found.")
            self.destroy()
            return
        self.family = dict(raw_fam)

        self.title(f"Manual Booking Workspace — {self.family['family_name']} ({self.family['family_code']})")
        self.geometry("1100x800")
        self.minsize(980, 680)
        self.transient(parent)

        # 7-Step Manual Checklist State
        self.checklist_vars = [
            tk.BooleanVar(value=False),  # Step 1: Client logs into official TTD website
            tk.BooleanVar(value=False),  # Step 2: Client reviews relevant booking details
            tk.BooleanVar(value=False),  # Step 3: Client independently enters required info
            tk.BooleanVar(value=False),  # Step 4: Client manually completes CAPTCHA
            tk.BooleanVar(value=False),  # Step 5: Client independently reviews and submits
            tk.BooleanVar(value=False),  # Step 6: Client completes payment directly
            tk.BooleanVar(value=False),  # Step 7: Client returns and updates booking status
        ]

        self._build_ui()
        self.refresh_workspace_data()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Top Header & Launch Bar
        top_bar = ttk.Frame(container)
        top_bar.pack(fill="x", pady=(0, 12))

        title_box = ttk.Frame(top_bar)
        title_box.pack(side="left")

        self.lbl_head = ttk.Label(
            title_box,
            text=f"Family Booking Workspace: {self.family['family_name']}",
            font=("Segoe UI", 15, "bold"),
            foreground="#0F172A",
        )
        self.lbl_head.pack(anchor="w")

        self.lbl_subhead = ttk.Label(
            title_box,
            text=f"Code: {self.family['family_code']} • Phone: {self.family['phone']} • Date: {self.family['preferred_date'] or 'Not set'}",
            font=("Segoe UI", 9),
            foreground="#64748B",
        )
        self.lbl_subhead.pack(anchor="w", pady=(2, 0))

        # Big Button: OPEN OFFICIAL TTD WEBSITE
        launch_box = ttk.Frame(top_bar)
        launch_box.pack(side="right")

        btn_ttd = tk.Button(
            launch_box,
            text="🌐 OPEN OFFICIAL TTD WEBSITE",
            font=("Segoe UI", 11, "bold"),
            bg="#D97706",
            fg="#FFFFFF",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._open_official_ttd_website,
        )
        btn_ttd.pack(anchor="e")

        lbl_ttd_note = ttk.Label(
            launch_box,
            text="Opens official portal in default browser • No automation",
            font=("Segoe UI", 7, "italic"),
            foreground="#64748B",
        )
        lbl_ttd_note.pack(anchor="e", pady=(2, 0))

        # Main Workspace Panes (Left: Preparation & Roster | Right: Checklist & Actions)
        workspace_pane = ttk.PanedWindow(container, orient="horizontal")
        workspace_pane.pack(fill="both", expand=True)

        left_frame = ttk.Frame(workspace_pane, padding=(0, 0, 8, 0))
        right_frame = ttk.Frame(workspace_pane, padding=(8, 0, 0, 0))
        workspace_pane.add(left_frame, weight=3)
        workspace_pane.add(right_frame, weight=2)

        # -------------------------------------------------------------
        # LEFT PANE: Family Details, Pilgrim Roster & Donation Preference
        # -------------------------------------------------------------
        # 1. Family Summary Card
        fam_card = ttk.LabelFrame(left_frame, text=" Family Preparation Profile ", padding=10)
        fam_card.pack(fill="x", pady=(0, 10))

        r1 = ttk.Frame(fam_card)
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text="Primary Contact:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.lbl_fam_contact = ttk.Label(r1, text=f"{self.family['family_name']} ({self.family['phone']})")
        self.lbl_fam_contact.pack(side="left", padx=6)
        ttk.Button(r1, text="📋 Copy Phone", command=lambda: self._copy_to_clipboard(self.family['phone'])).pack(side="right")

        r2 = ttk.Frame(fam_card)
        r2.pack(fill="x", pady=2)
        ttk.Label(r2, text="Locally Configured Donation:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.lbl_donation = ttk.Label(r2, text=f"₹{float(self.family.get('donation_amount') or 0):,.0f}", font=("Segoe UI", 9, "bold"), foreground="#0D5C75")
        self.lbl_donation.pack(side="left", padx=6)
        disclaimer = ttk.Label(r2, text="(Preparation record only — never automatically entered into TTD)", font=("Segoe UI", 7, "italic"), foreground="#64748B")
        disclaimer.pack(side="left", padx=4)

        # Readiness Status & Missing Items Alert Bar
        self.readiness_bar = tk.Frame(fam_card, bg="#F1F5F9", bd=1, relief="solid", padx=8, pady=6)
        self.readiness_bar.pack(fill="x", pady=(6, 0))

        self.lbl_readiness_badge = tk.Label(
            self.readiness_bar,
            text="Readiness: Evaluating...",
            font=("Segoe UI", 9, "bold"),
            bg="#F1F5F9",
            fg="#0F172A",
        )
        self.lbl_readiness_badge.pack(side="left")

        btn_inspect = ttk.Button(self.readiness_bar, text="🔍 View Readiness Audit", command=self._inspect_readiness)
        btn_inspect.pack(side="right")

        # 2. Pilgrim Roster Table
        pil_card = ttk.LabelFrame(left_frame, text=" Devotee Pilgrim Roster ", padding=10)
        pil_card.pack(fill="both", expand=True, pady=(0, 10))

        tbl_box = ttk.Frame(pil_card)
        tbl_box.pack(fill="both", expand=True)

        cols = ("idx", "name", "age", "gender", "id_type", "last4")
        self.tree_pilgrims = ttk.Treeview(tbl_box, columns=cols, show="headings", height=6)
        self.tree_pilgrims.heading("idx", text="#")
        self.tree_pilgrims.heading("name", text="Full Name")
        self.tree_pilgrims.heading("age", text="Age")
        self.tree_pilgrims.heading("gender", text="Gender")
        self.tree_pilgrims.heading("id_type", text="ID Proof")
        self.tree_pilgrims.heading("last4", text="Masked ID")

        self.tree_pilgrims.column("idx", width=35, anchor="center")
        self.tree_pilgrims.column("name", width=160)
        self.tree_pilgrims.column("age", width=50, anchor="center")
        self.tree_pilgrims.column("gender", width=70, anchor="center")
        self.tree_pilgrims.column("id_type", width=100)
        self.tree_pilgrims.column("last4", width=80, anchor="center")

        p_scroll = ttk.Scrollbar(tbl_box, orient="vertical", command=self.tree_pilgrims.yview)
        self.tree_pilgrims.configure(yscrollcommand=p_scroll.set)
        self.tree_pilgrims.pack(side="left", fill="both", expand=True)
        p_scroll.pack(side="right", fill="y")

        # Copy Pilgrim Action Bar
        copy_bar = ttk.Frame(pil_card)
        copy_bar.pack(fill="x", pady=(6, 0))
        ttk.Button(copy_bar, text="📋 Copy Selected Devotee", command=self._copy_selected_pilgrim).pack(side="left", padx=(0, 6))
        ttk.Button(copy_bar, text="📋 Copy Entire Roster (Plaintext)", command=self._copy_all_pilgrims).pack(side="left")

        # 3. Document Management Summary & Launcher
        doc_card = ttk.LabelFrame(left_frame, text=" Supporting Document Management ", padding=10)
        doc_card.pack(fill="x")

        self.lbl_doc_summary = ttk.Label(doc_card, text="Attached Documents: Checking...", font=("Segoe UI", 9))
        self.lbl_doc_summary.pack(side="left")

        btn_docs = ttk.Button(doc_card, text="📁 Manage Documents & PDFs", command=self._open_document_manager)
        btn_docs.pack(side="right")

        # -------------------------------------------------------------
        # RIGHT PANE: Manual 7-Step Checklist, Booking & Payment Status
        # -------------------------------------------------------------
        chk_frame = ttk.LabelFrame(right_frame, text=" Manual Booking Assistance Checklist ", padding=12)
        chk_frame.pack(fill="x", pady=(0, 10))

        steps_labels = [
            "1. Client logs into the official TTD website.",
            "2. Client reviews the relevant booking details.",
            "3. Client independently enters the required information.",
            "4. Client manually completes CAPTCHA.",
            "5. Client independently reviews and submits the booking.",
            "6. Client completes payment directly through the official payment flow.",
            "7. Client returns to this application and updates the booking status.",
        ]

        for i, text in enumerate(steps_labels):
            chk = ttk.Checkbutton(chk_frame, text=text, variable=self.checklist_vars[i])
            chk.pack(anchor="w", pady=2)

        chk_disclaimer = ttk.Label(
            chk_frame,
            text="🔒 Every step must be executed independently by the client on the official TTD portal. This tool does not control the browser.",
            font=("Segoe UI", 7, "italic"),
            foreground="#64748B",
            wraplength=340,
        )
        chk_disclaimer.pack(anchor="w", pady=(8, 0))

        # Booking Status Transition Card
        b_status_card = ttk.LabelFrame(right_frame, text=" Booking Status Management ", padding=12)
        b_status_card.pack(fill="x", pady=(0, 10))

        f_status_grid = ttk.Frame(b_status_card)
        f_status_grid.pack(fill="x")

        ttk.Label(f_status_grid, text="Current Booking Status:").grid(row=0, column=0, sticky="w", pady=3)
        self.cb_booking_status = ttk.Combobox(
            f_status_grid,
            values=[STATUS_NOT_STARTED, STATUS_INCOMPLETE, STATUS_READY_FOR_MANUAL_BOOKING, STATUS_BOOKING_IN_PROGRESS, STATUS_BOOKED, STATUS_CANCELLED],
            state="readonly",
            width=26,
        )
        self.cb_booking_status.grid(row=0, column=1, sticky="w", padx=6, pady=3)

        btn_save_status = ttk.Button(f_status_grid, text="Update Booking Status", command=self._save_booking_status)
        btn_save_status.grid(row=1, column=1, sticky="e", padx=6, pady=(4, 0))

        # Payment Tracking Card
        pay_card = ttk.LabelFrame(right_frame, text=" Payment Tracking Status ", padding=12)
        pay_card.pack(fill="both", expand=True)

        pay_grid = ttk.Frame(pay_card)
        pay_grid.pack(fill="x")

        ttk.Label(pay_grid, text="Payment Status:").grid(row=0, column=0, sticky="w", pady=3)
        self.cb_payment_status = ttk.Combobox(
            pay_grid,
            values=[PAYMENT_NOT_PAID, PAYMENT_PENDING, PAYMENT_PAID, PAYMENT_FAILED, PAYMENT_REFUNDED],
            state="readonly",
            width=26,
        )
        self.cb_payment_status.grid(row=0, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(pay_grid, text="Transaction Reference:").grid(row=1, column=0, sticky="w", pady=3)
        self.ent_pay_ref = ttk.Entry(pay_grid, width=28)
        self.ent_pay_ref.grid(row=1, column=1, sticky="w", padx=6, pady=3)

        ttk.Label(pay_grid, text="Accounting Notes:").grid(row=2, column=0, sticky="w", pady=3)
        self.ent_pay_notes = ttk.Entry(pay_grid, width=28)
        self.ent_pay_notes.grid(row=2, column=1, sticky="w", padx=6, pady=3)

        btn_save_pay = ttk.Button(pay_grid, text="Update Payment Tracking", command=self._save_payment_tracking)
        btn_save_pay.grid(row=3, column=1, sticky="e", padx=6, pady=(6, 0))

    def refresh_workspace_data(self):
        """Fetch updated family, pilgrim, and document records."""
        raw_fam = get_family(self.family_id)
        if not raw_fam:
            return
        self.family = dict(raw_fam)

        pilgrims = [dict(p) for p in get_family_pilgrims(self.family_id)]
        docs = [dict(d) for d in get_family_documents(self.family_id)]

        # Update Pilgrim Tree
        for item in self.tree_pilgrims.get_children():
            self.tree_pilgrims.delete(item)

        for i, p in enumerate(pilgrims, start=1):
            self.tree_pilgrims.insert(
                "",
                "end",
                values=(
                    i,
                    p.get("full_name", ""),
                    p.get("age", ""),
                    p.get("gender", ""),
                    p.get("id_proof_type", ""),
                    p.get("id_proof_last4", ""),
                ),
            )

        # Update Document Summary
        doc_count = len(docs)
        ticket_attached = bool(self.family.get("ticket_pdf_path"))
        summary_text = f"Attached Supporting Docs: {doc_count}"
        if ticket_attached:
            summary_text += " • Ticket PDF attached"
        self.lbl_doc_summary.config(text=summary_text)

        # Calculate Readiness
        readiness = calculate_booking_readiness(self.family, pilgrims, docs)
        update_family_readiness(
            self.family_id,
            readiness_status=readiness["status"],
            readiness_score=readiness["score"],
            missing_items=readiness["missing_items"],
        )

        # Update Readiness Badge UI
        status_text = readiness["status"]
        score = readiness["score"]
        if readiness["is_ready"]:
            self.readiness_bar.config(bg="#DCFCE7")
            self.lbl_readiness_badge.config(
                text=f"✅ READINESS: READY FOR MANUAL BOOKING ({score}%)",
                bg="#DCFCE7",
                fg="#15803D",
            )
        else:
            self.readiness_bar.config(bg="#FEF3C7")
            self.lbl_readiness_badge.config(
                text=f"⚠️ READINESS: {status_text} ({score}%)",
                bg="#FEF3C7",
                fg="#B45309",
            )

        # Update Status Comboboxes
        norm_b_status = normalize_booking_status(self.family.get("status"))
        self.cb_booking_status.set(norm_b_status)

        norm_p_status = normalize_payment_tracking_status(self.family.get("payment_status"))
        self.cb_payment_status.set(norm_p_status)

        self.ent_pay_ref.delete(0, tk.END)
        self.ent_pay_ref.insert(0, self.family.get("payment_ref") or "")

        self.ent_pay_notes.delete(0, tk.END)
        self.ent_pay_notes.insert(0, self.family.get("payment_notes") or "")

    def _open_official_ttd_website(self):
        """
        Compliance-approved action:
        Opens the official TTD website in the client's default system browser.
        No automation, no DOM manipulation, no browser control.
        """
        url = "https://ttdevasthanams.ap.gov.in"
        webbrowser.open(url)
        # Check Step 1 on checklist automatically to assist user
        self.checklist_vars[0].set(True)

    def _copy_to_clipboard(self, text: str):
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", f"Copied to clipboard: {text}")

    def _copy_selected_pilgrim(self):
        sel = self.tree_pilgrims.selection()
        if not sel:
            messagebox.showinfo("Select Devotee", "Please select a devotee in the table to copy.")
            return
        vals = self.tree_pilgrims.item(sel[0], "values")
        text = f"Name: {vals[1]}, Age: {vals[2]}, Gender: {vals[3]}, ID Type: {vals[4]}, ID Last4: {vals[5]}"
        self._copy_to_clipboard(text)

    def _copy_all_pilgrims(self):
        pilgrims = get_family_pilgrims(self.family_id)
        if not pilgrims:
            messagebox.showinfo("Empty", "No pilgrims in roster to copy.")
            return
        lines = []
        for i, p in enumerate(pilgrims, start=1):
            lines.append(f"{i}. {p.get('full_name')}, Age: {p.get('age')}, Gender: {p.get('gender')}, ID: {p.get('id_proof_type')} {p.get('id_proof_last4')}")
        self._copy_to_clipboard("\n".join(lines))

    def _open_document_manager(self):
        DocumentManagementDialog(self, self.family_id, on_update_callback=self.refresh_workspace_data)

    def _inspect_readiness(self):
        BookingReadinessInspectorDialog(self, self.family_id)

    def _save_booking_status(self):
        new_status = self.cb_booking_status.get()
        if not new_status:
            return

        with get_connection() as con:
            con.execute("UPDATE families SET status = ? WHERE id = ?", (new_status, self.family_id))
            con.commit()

        log_queue_action(
            family_id=self.family_id,
            action="STATUS_UPDATED",
            new_status=new_status,
            notes=f"Booking status manually updated to {new_status}",
        )

        messagebox.showinfo("Saved", f"Booking status updated to {new_status}.")
        self.refresh_workspace_data()
        if self.on_update:
            self.on_update()

    def _save_payment_tracking(self):
        new_status = self.cb_payment_status.get()
        ref = self.ent_pay_ref.get().strip()
        notes = self.ent_pay_notes.get().strip()

        update_family_payment_tracking(
            family_id=self.family_id,
            payment_status=new_status,
            payment_ref=ref,
            payment_notes=notes,
        )

        messagebox.showinfo("Saved", f"Payment tracking status updated to {new_status}.")
        self.refresh_workspace_data()
        if self.on_update:
            self.on_update()


class DocumentManagementDialog(tk.Toplevel):
    """
    Module 7: Supporting Document Management Dialog.
    Allows adding PDF or image documents, validating sizes and formats,
    viewing previews, and deleting documents.
    """

    def __init__(self, parent, family_id: int, on_update_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.family_id = family_id
        self.on_update = on_update_callback
        raw_fam = get_family(family_id)
        if not raw_fam:
            messagebox.showerror("Error", f"Family ID {family_id} not found.")
            self.destroy()
            return
        self.family = dict(raw_fam)

        self.title(f"Document Management — {self.family['family_name']} ({self.family['family_code']})")
        self.geometry("780x520")
        self.transient(parent)

        self._build_ui()
        self.refresh_document_list()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text=f"📁 Supporting Documents: {self.family['family_name']}",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        btn_add = ttk.Button(header, text="➕ Attach Document (PDF/Image)", command=self._attach_document)
        btn_add.pack(side="right")

        # Table of Documents
        tbl_box = ttk.Frame(container)
        tbl_box.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("id", "type", "name", "size", "sha256", "date")
        self.tree_docs = ttk.Treeview(tbl_box, columns=cols, show="headings", height=8)
        self.tree_docs.heading("id", text="#")
        self.tree_docs.heading("type", text="Doc Type")
        self.tree_docs.heading("name", text="File Name")
        self.tree_docs.heading("size", text="Size")
        self.tree_docs.heading("sha256", text="SHA-256 Checksum")
        self.tree_docs.heading("date", text="Attached At")

        self.tree_docs.column("id", width=35, anchor="center")
        self.tree_docs.column("type", width=100)
        self.tree_docs.column("name", width=180)
        self.tree_docs.column("size", width=70, anchor="center")
        self.tree_docs.column("sha256", width=140)
        self.tree_docs.column("date", width=130)

        scroll = ttk.Scrollbar(tbl_box, orient="vertical", command=self.tree_docs.yview)
        self.tree_docs.configure(yscrollcommand=scroll.set)
        self.tree_docs.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Action Buttons
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x")

        ttk.Button(btn_bar, text="👁️ Open / Preview Document", command=self._preview_selected).pack(side="left", padx=(0, 8))
        ttk.Button(btn_bar, text="🗑️ Remove Document", command=self._delete_selected).pack(side="left")
        ttk.Button(btn_bar, text="Close", command=self.destroy).pack(side="right")

    def refresh_document_list(self):
        for item in self.tree_docs.get_children():
            self.tree_docs.delete(item)

        docs = [dict(d) for d in get_family_documents(self.family_id)]
        for d in docs:
            size_kb = f"{d['file_size'] / 1024:.1f} KB" if d.get("file_size") else "N/A"
            sha_short = (d.get("sha256") or "")[:12] + "..."
            self.tree_docs.insert(
                "",
                "end",
                values=(
                    d["id"],
                    d.get("doc_type", "ID_PROOF"),
                    d.get("file_name", ""),
                    size_kb,
                    sha_short,
                    d.get("created_at", ""),
                ),
            )

    def _attach_document(self):
        file_path = filedialog.askopenfilename(
            title="Select Supporting Document (PDF or Image)",
            filetypes=[
                ("All Supported Files", "*.pdf;*.png;*.jpg;*.jpeg"),
                ("PDF Documents", "*.pdf"),
                ("Images", "*.png;*.jpg;*.jpeg"),
            ],
        )
        if not file_path:
            return

        valid, err = validate_document_file(file_path)
        if not valid:
            messagebox.showerror("Invalid File", err)
            return

        try:
            meta = store_family_document(
                family_id=self.family_id,
                source_file_path=file_path,
                doc_type="ID_PROOF",
            )
            add_family_document(
                family_id=self.family_id,
                doc_type=meta["doc_type"],
                file_name=meta["file_name"],
                file_path=meta["file_path"],
                file_size=meta["file_size"],
                sha256=meta["sha256"],
            )
            messagebox.showinfo("Success", f"Document '{meta['file_name']}' attached successfully.")
            self.refresh_document_list()
            if self.on_update:
                self.on_update()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to store document: {e}")

    def _preview_selected(self):
        sel = self.tree_docs.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a document to preview.")
            return
        doc_id = int(self.tree_docs.item(sel[0], "values")[0])
        docs = [dict(d) for d in get_family_documents(self.family_id)]
        target = next((d for d in docs if d["id"] == doc_id), None)
        if target:
            success = open_document_preview(target["file_path"])
            if not success:
                messagebox.showerror("Error", "Could not launch system viewer for this document.")

    def _delete_selected(self):
        sel = self.tree_docs.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a document to delete.")
            return
        doc_id = int(self.tree_docs.item(sel[0], "values")[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to remove this attached document?"):
            delete_family_document(doc_id)
            self.refresh_document_list()
            if self.on_update:
                self.on_update()


class BookingReadinessInspectorDialog(tk.Toplevel):
    """
    Module 5: Detailed Booking Readiness Audit Inspector.
    Visualizes exact passed checklist items, missing items, and validation errors.
    """

    def __init__(self, parent, family_id: int):
        super().__init__(parent)
        self.family_id = family_id
        raw_fam = get_family(family_id)
        if not raw_fam:
            messagebox.showerror("Error", f"Family ID {family_id} not found.")
            self.destroy()
            return
        self.family = dict(raw_fam)

        self.title(f"Readiness Audit — {self.family['family_name']} ({self.family['family_code']})")
        self.geometry("640x540")
        self.transient(parent)

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        pilgrims = [dict(p) for p in get_family_pilgrims(self.family_id)]
        docs = [dict(d) for d in get_family_documents(self.family_id)]
        eval_res = calculate_booking_readiness(self.family, pilgrims, docs)

        status_str = eval_res["status"]
        score = eval_res["score"]
        is_ready = eval_res["is_ready"]

        # Top Banner
        badge_bg = "#DCFCE7" if is_ready else "#FEF3C7"
        badge_fg = "#15803D" if is_ready else "#B45309"

        header_box = tk.Frame(container, bg=badge_bg, bd=1, relief="solid", padx=14, pady=12)
        header_box.pack(fill="x", pady=(0, 14))

        tk.Label(
            header_box,
            text=f"STATUS: {status_str}",
            font=("Segoe UI", 12, "bold"),
            fg=badge_fg,
            bg=badge_bg,
        ).pack(anchor="w")

        tk.Label(
            header_box,
            text=f"Readiness Score: {score}% • {'Eligible for manual booking' if is_ready else 'Profile requires client attention'}",
            font=("Segoe UI", 9),
            fg=badge_fg,
            bg=badge_bg,
        ).pack(anchor="w", pady=(2, 0))

        # Completed Items Card
        c_card = ttk.LabelFrame(container, text=" ✅ Completed Preparation Items ", padding=10)
        c_card.pack(fill="x", pady=(0, 10))

        for item in eval_res.get("completed_items", []):
            ttk.Label(c_card, text=f"• {item}", foreground="#15803D").pack(anchor="w", pady=1)

        if not eval_res.get("completed_items"):
            ttk.Label(c_card, text="No items completed yet.", font=("Segoe UI", 8, "italic")).pack(anchor="w")

        # Missing Items Card
        m_card = ttk.LabelFrame(container, text=" ⚠️ Missing Information & Action Checklist ", padding=10)
        m_card.pack(fill="both", expand=True, pady=(0, 10))

        for item in eval_res.get("missing_items", []):
            ttk.Label(m_card, text=f"• {item}", foreground="#B45309", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=2)

        for err in eval_res.get("validation_errors", []):
            ttk.Label(m_card, text=f"  ↳ Error: {err}", foreground="#DC2626", font=("Segoe UI", 8)).pack(anchor="w", pady=1)

        if not eval_res.get("missing_items") and not eval_res.get("validation_errors"):
            ttk.Label(m_card, text="All requirements satisfied. Family is ready for manual booking.", foreground="#15803D", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        btn_close = ttk.Button(container, text="Close Inspector", command=self.destroy)
        btn_close.pack(anchor="e")


class BookingHistoryFrame(tk.Frame):
    """
    Module 9: Filterable, searchable booking history view with CSV and Excel export.
    """

    def __init__(self, parent, app_controller):
        super().__init__(parent, bg="#F8FAFC")
        self.app = app_controller
        self._build_ui()

    def _build_ui(self):
        # Header & Filter Toolbar
        top_bar = tk.Frame(self, bg="#FFFFFF", padx=20, pady=12, bd=1, relief="solid")
        top_bar.pack(fill="x", padx=16, pady=(16, 10))

        tk.Label(
            top_bar,
            text="📜 BOOKING & PAYMENT TRANSACTION HISTORY",
            font=("Segoe UI", 14, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        ).pack(anchor="w")

        filter_row = tk.Frame(top_bar, bg="#FFFFFF")
        filter_row.pack(fill="x", pady=(10, 0))

        tk.Label(filter_row, text="Search:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side="left")
        self.ent_search = ttk.Entry(filter_row, width=20)
        self.ent_search.pack(side="left", padx=(6, 16))
        self.ent_search.bind("<KeyRelease>", lambda e: self.filter_history())

        tk.Label(filter_row, text="Booking Status:", font=("Segoe UI", 9), bg="#FFFFFF").pack(side="left")
        self.cb_status = ttk.Combobox(filter_row, values=["All"] + ALL_BOOKING_STATUSES, state="readonly", width=18)
        self.cb_status.set("All")
        self.cb_status.pack(side="left", padx=(6, 16))
        self.cb_status.bind("<<ComboboxSelected>>", lambda e: self.filter_history())

        tk.Label(filter_row, text="Payment Status:", font=("Segoe UI", 9), bg="#FFFFFF").pack(side="left")
        self.cb_pay = ttk.Combobox(filter_row, values=["All"] + ALL_PAYMENT_STATUSES, state="readonly", width=16)
        self.cb_pay.set("All")
        self.cb_pay.pack(side="left", padx=(6, 16))
        self.cb_pay.bind("<<ComboboxSelected>>", lambda e: self.filter_history())

        btn_export_csv = ttk.Button(filter_row, text="📥 Export CSV", command=self.export_history_csv)
        btn_export_csv.pack(side="right", padx=(6, 0))

        btn_export_xlsx = ttk.Button(filter_row, text="📊 Export Excel", command=self.export_history_xlsx)
        btn_export_xlsx.pack(side="right")

        # History Table
        table_container = tk.Frame(self, bg="#FFFFFF", bd=1, relief="solid")
        table_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        cols = ("code", "name", "phone", "b_status", "p_status", "pref", "pils", "date")
        self.tree_history = ttk.Treeview(table_container, columns=cols, show="headings", height=15)
        self.tree_history.heading("code", text="Family Code")
        self.tree_history.heading("name", text="Family Name")
        self.tree_history.heading("phone", text="Contact Phone")
        self.tree_history.heading("b_status", text="Booking Status")
        self.tree_history.heading("p_status", text="Payment Status")
        self.tree_history.heading("pref", text="Payment Ref")
        self.tree_history.heading("pils", text="Devotees")
        self.tree_history.heading("date", text="Created Date")

        self.tree_history.column("code", width=100, anchor="center")
        self.tree_history.column("name", width=180)
        self.tree_history.column("phone", width=110, anchor="center")
        self.tree_history.column("b_status", width=140, anchor="center")
        self.tree_history.column("p_status", width=130, anchor="center")
        self.tree_history.column("pref", width=120)
        self.tree_history.column("pils", width=70, anchor="center")
        self.tree_history.column("date", width=130)

        scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.tree_history.yview)
        self.tree_history.configure(yscrollcommand=scroll.set)
        self.tree_history.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.filter_history()

    def filter_history(self):
        query = self.ent_search.get().strip().lower()
        st_filter = self.cb_status.get()
        p_filter = self.cb_pay.get()

        for item in self.tree_history.get_children():
            self.tree_history.delete(item)

        fams = get_all_families()
        for f_row in fams:
            f = dict(f_row)
            name = (f.get("family_name") or "").lower()
            code = (f.get("family_code") or "").lower()
            phone = (f.get("phone") or "").lower()

            if query and (query not in name and query not in code and query not in phone):
                continue

            b_st = normalize_booking_status(f.get("status"))
            if st_filter != "All" and b_st != st_filter:
                continue

            p_st = normalize_payment_tracking_status(f.get("payment_status"))
            if p_filter != "All" and p_st != p_filter:
                continue

            pils = get_family_pilgrims(f["id"])
            c_date = str(f.get("created_at") or "")[:10]

            self.tree_history.insert(
                "",
                "end",
                values=(
                    f.get("family_code", ""),
                    f.get("family_name", ""),
                    f.get("phone", ""),
                    b_st,
                    p_st,
                    f.get("payment_ref") or "-",
                    len(pils),
                    c_date,
                ),
            )

    def export_history_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"srivani_booking_history_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if not path:
            return

        import csv
        fams = get_all_families()
        with open(path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["Family Code", "Family Name", "Phone", "Booking Status", "Payment Status", "Payment Ref", "Devotees Count", "Preferred Date", "Created Date"])
            for fam_row in fams:
                fam = dict(fam_row)
                pils = get_family_pilgrims(fam["id"])
                writer.writerow([
                    fam.get("family_code", ""),
                    fam.get("family_name", ""),
                    fam.get("phone", ""),
                    normalize_booking_status(fam.get("status")),
                    normalize_payment_tracking_status(fam.get("payment_status")),
                    fam.get("payment_ref") or "",
                    len(pils),
                    fam.get("preferred_date") or "",
                    fam.get("created_at") or "",
                ])
        messagebox.showinfo("Export Successful", f"Booking history exported to:\n{path}")

    def export_history_xlsx(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=f"srivani_booking_history_{datetime.now().strftime('%Y%m%d')}.xlsx",
        )
        if not path:
            return

        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Booking History"

        headers = ["Family Code", "Family Name", "Phone", "Booking Status", "Payment Status", "Payment Ref", "Devotees Count", "Preferred Date", "Created Date"]
        ws.append(headers)

        fams = get_all_families()
        for fam_row in fams:
            fam = dict(fam_row)
            pils = get_family_pilgrims(fam["id"])
            ws.append([
                fam.get("family_code", ""),
                fam.get("family_name", ""),
                fam.get("phone", ""),
                normalize_booking_status(fam.get("status")),
                normalize_payment_tracking_status(fam.get("payment_status")),
                fam.get("payment_ref") or "",
                len(pils),
                fam.get("preferred_date") or "",
                fam.get("created_at") or "",
            ])

        wb.save(path)
        messagebox.showinfo("Export Successful", f"Booking history exported to Excel:\n{path}")
