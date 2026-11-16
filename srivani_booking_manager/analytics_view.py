"""
SRIVANI BOOKING MANAGER - Interactive Analytics & Operational Intelligence UI
Features date range filtering, executive KPI metric cards, performance trend tables,
queue aging buckets, payment analytics, document compliance, and rule-based prioritization.
"""
import sys
import os
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from analytics_engine import (
    parse_date_filter,
    get_analytics_summary,
    get_booking_performance,
    get_queue_intelligence,
    get_payment_analytics,
    get_document_analytics,
    get_operational_intelligence,
)
from analytics_export import (
    export_summary_to_csv,
    export_performance_to_csv,
    export_queue_intelligence_to_csv,
    export_full_analytics_workbook_xlsx,
    export_analytics_report_pdf,
)
from logger import get_logger

logger = get_logger("analytics_view")


class AnalyticsDashboardFrame(ttk.Frame):
    """
    Primary Interactive Analytics Dashboard and Operational Intelligence View.
    Integrates directly into the main application container.
    """

    def __init__(self, parent, app_controller, db_path: Optional[Path] = None):
        super().__init__(parent)
        self.app = app_controller
        self.db_path = db_path
        self.active_filter = "all"
        self.custom_start = ""
        self.custom_end = ""

        self._build_ui()
        self.refresh_analytics()

    def _build_ui(self):
        # 1. Top Header & Date Filter Toolbar
        self._build_top_filter_bar()

        # 2. Executive KPI Summary Cards
        self._build_kpi_cards()

        # 3. Main Multi-Tab Analytics Workspace
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(6, 12))

        # Tab 1: Booking Performance & Trends
        self.tab_performance = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_performance, text="📈 Performance & Trends")
        self._build_performance_tab()

        # Tab 2: Queue Intelligence & Bottlenecks
        self.tab_queue = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_queue, text="⏱️ Queue Intelligence")
        self._build_queue_tab()

        # Tab 3: Payment Analytics
        self.tab_payments = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_payments, text="💳 Payment Analytics")
        self._build_payment_tab()

        # Tab 4: Document & Ticket Compliance
        self.tab_documents = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_documents, text="📁 Document Compliance")
        self._build_document_tab()

        # Tab 5: Operational Insights & Prioritization Engine
        self.tab_ops = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_ops, text="💡 Operational Insights & Queue Order")
        self._build_ops_tab()

    def _build_top_filter_bar(self):
        top_bar = tk.Frame(self, bg="#0F172A", padx=16, pady=10)
        top_bar.pack(fill=tk.X)

        lbl_box = tk.Frame(top_bar, bg="#0F172A")
        lbl_box.pack(side=tk.LEFT)

        tk.Label(
            lbl_box,
            text="OPERATIONAL ANALYTICS & INTELLIGENCE",
            font=("Segoe UI", 11, "bold"),
            fg="#F59E0B",
            bg="#0F172A",
        ).pack(anchor="w")

        self.lbl_filter_scope = tk.Label(
            lbl_box,
            text="Scope: All Time | Live SQLite Database Records",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#0F172A",
        )
        self.lbl_filter_scope.pack(anchor="w")

        # Right Controls: Filter Selector + Export Button + Refresh
        ctrl_box = tk.Frame(top_bar, bg="#0F172A")
        ctrl_box.pack(side=tk.RIGHT)

        tk.Label(ctrl_box, text="Date Filter:", font=("Segoe UI", 9, "bold"), fg="#E2E8F0", bg="#0F172A").pack(side=tk.LEFT, padx=(0, 6))

        self.filter_combo = ttk.Combobox(
            ctrl_box,
            values=["All Time", "Today", "Last 7 Days", "Last 30 Days", "This Month", "Custom Range"],
            state="readonly",
            width=13,
        )
        self.filter_combo.set("All Time")
        self.filter_combo.pack(side=tk.LEFT, padx=(0, 6))
        self.filter_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Custom date entries (hidden unless Custom Range is selected)
        self.custom_frame = tk.Frame(ctrl_box, bg="#0F172A")
        tk.Label(self.custom_frame, text="From:", font=("Segoe UI", 8), fg="#CBD5E1", bg="#0F172A").pack(side=tk.LEFT, padx=(4, 2))
        self.ent_start = ttk.Entry(self.custom_frame, width=10)
        self.ent_start.pack(side=tk.LEFT, padx=(0, 4))

        tk.Label(self.custom_frame, text="To:", font=("Segoe UI", 8), fg="#CBD5E1", bg="#0F172A").pack(side=tk.LEFT, padx=(2, 2))
        self.ent_end = ttk.Entry(self.custom_frame, width=10)
        self.ent_end.pack(side=tk.LEFT, padx=(0, 6))

        btn_apply = tk.Button(
            self.custom_frame,
            text="Apply",
            font=("Segoe UI", 8, "bold"),
            bg="#0284C7",
            fg="white",
            relief="flat",
            padx=8,
            pady=2,
            command=self._on_custom_apply,
        )
        btn_apply.pack(side=tk.LEFT, padx=(0, 6))

        # Export Dropdown Menu Button
        self.btn_export = tk.Menubutton(
            ctrl_box,
            text="📥 Export Report ▾",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
        )
        self.export_menu = tk.Menu(self.btn_export, tearoff=0)
        self.export_menu.add_command(label="📊 Full Excel Workbook (.xlsx)", command=self._export_excel_workbook)
        self.export_menu.add_command(label="📄 Printable Executive PDF (.pdf)", command=self._export_pdf_report)
        self.export_menu.add_separator()
        self.export_menu.add_command(label="📑 KPI Summary (.csv)", command=lambda: self._export_csv("summary"))
        self.export_menu.add_command(label="📈 Daily Performance Trends (.csv)", command=lambda: self._export_csv("performance"))
        self.export_menu.add_command(label="⏱️ Queue Intelligence Audit (.csv)", command=lambda: self._export_csv("queue"))
        self.btn_export.config(menu=self.export_menu)
        self.btn_export.pack(side=tk.LEFT, padx=(0, 6))

        # Refresh Button
        btn_refresh = tk.Button(
            ctrl_box,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#F8FAFC",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.refresh_analytics,
        )
        btn_refresh.pack(side=tk.LEFT)

    def _build_kpi_cards(self):
        kpi_bar = ttk.Frame(self, padding=(20, 8, 20, 4))
        kpi_bar.pack(fill=tk.X)

        self.cards = {}
        configs = [
            ("total_families", "TOTAL FAMILIES", "0", "#1E3A8A"),
            ("total_pilgrims", "TOTAL DEVOTEES", "0", "#4338CA"),
            ("completed_bookings", "BOOKED (COMPLETED)", "0 (0%)", "#15803D"),
            ("pending_bookings", "PENDING IN QUEUE", "0", "#B45309"),
            ("processing_rate", "PROCESSING RATE", "0%", "#0369A1"),
            ("total_revenue", "COLLECTED REVENUE", "₹0.00", "#0F766E"),
        ]

        for idx, (key, label, default_val, color) in enumerate(configs):
            card = tk.Frame(kpi_bar, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1, padx=12, pady=6)
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0 if idx == 0 else 6, 0))

            tk.Label(card, text=label, font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#FFFFFF").pack(anchor="w")
            lbl_val = tk.Label(card, text=default_val, font=("Segoe UI", 13, "bold"), fg=color, bg="#FFFFFF")
            lbl_val.pack(anchor="w", pady=(2, 0))
            self.cards[key] = lbl_val

    # ---------------------------------------------------------
    # TAB 1: Performance & Trends
    # ---------------------------------------------------------
    def _build_performance_tab(self):
        parent = self.tab_performance

        # Metrics Banner
        top_box = tk.Frame(parent, bg="#F1F5F9", padx=12, pady=8)
        top_box.pack(fill=tk.X, pady=(0, 8))

        self.lbl_turnaround = tk.Label(
            top_box,
            text="⚡ Average Lead Time: 0.0 Hours  |  Processed vs Backlog: 0 / 0",
            font=("Segoe UI", 9, "bold"),
            fg="#1E293B",
            bg="#F1F5F9",
        )
        self.lbl_turnaround.pack(side=tk.LEFT)

        # Performance Treeview Table
        cols = ("date", "total", "booked", "pending", "unavailable", "cancelled", "pilgrims", "revenue")
        self.tree_perf = ttk.Treeview(parent, columns=cols, show="headings", height=12)

        headings = {
            "date": "Activity Date",
            "total": "Total Families",
            "booked": "Booked",
            "pending": "Pending",
            "unavailable": "Unavailable",
            "cancelled": "Cancelled",
            "pilgrims": "Devotees",
            "revenue": "Booked Revenue (₹)",
        }
        widths = {
            "date": 120,
            "total": 110,
            "booked": 90,
            "pending": 90,
            "unavailable": 100,
            "cancelled": 90,
            "pilgrims": 90,
            "revenue": 140,
        }

        for c in cols:
            self.tree_perf.heading(c, text=headings[c])
            align = "e" if c in ("revenue",) else ("center" if c != "date" else "w")
            self.tree_perf.column(c, width=widths[c], anchor=align)

        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.tree_perf.yview)
        self.tree_perf.configure(yscrollcommand=y_scroll.set)
        self.tree_perf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # ---------------------------------------------------------
    # TAB 2: Queue Intelligence & Bottlenecks
    # ---------------------------------------------------------
    def _build_queue_tab(self):
        parent = self.tab_queue

        # Top row: Aging Buckets + Oldest Record
        info_row = tk.Frame(parent)
        info_row.pack(fill=tk.X, pady=(0, 10))

        # Aging Card
        f_aging = tk.LabelFrame(info_row, text=" Queue Aging Breakdown ", font=("Segoe UI", 9, "bold"), padx=12, pady=8)
        f_aging.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.lbl_aging_metrics = tk.Label(
            f_aging,
            text="< 24 Hours: 0  |  1–3 Days: 0  |  4–7 Days: 0  |  > 7 Days: 0",
            font=("Segoe UI", 10, "bold"),
            fg="#0284C7",
        )
        self.lbl_aging_metrics.pack(anchor="w", pady=4)

        # Oldest Record Card
        f_old = tk.LabelFrame(info_row, text=" Oldest Record in Queue ", font=("Segoe UI", 9, "bold"), padx=12, pady=8)
        f_old.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.lbl_oldest_record = tk.Label(
            f_old,
            text="None currently pending.",
            font=("Segoe UI", 9),
            fg="#B45309",
        )
        self.lbl_oldest_record.pack(anchor="w", pady=4)

        # Attention Items Table
        tk.Label(parent, text="⚠️ Records Requiring Administrator Attention:", font=("Segoe UI", 9, "bold"), fg="#1E293B").pack(anchor="w", pady=(4, 2))

        cols = ("code", "name", "phone", "reason", "created")
        self.tree_attention = ttk.Treeview(parent, columns=cols, show="headings", height=8)

        self.tree_attention.heading("code", text="Family Code")
        self.tree_attention.heading("name", text="Family Name")
        self.tree_attention.heading("phone", text="Phone")
        self.tree_attention.heading("reason", text="Attention Flag / Reason")
        self.tree_attention.heading("created", text="Created Date")

        self.tree_attention.column("code", width=120)
        self.tree_attention.column("name", width=160)
        self.tree_attention.column("phone", width=110)
        self.tree_attention.column("reason", width=220)
        self.tree_attention.column("created", width=140, anchor="center")

        self.tree_attention.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # Bottleneck Advice
        self.lbl_bottlenecks = tk.Label(parent, text="", font=("Segoe UI", 8, "italic"), fg="#475569", justify=tk.LEFT)
        self.lbl_bottlenecks.pack(anchor="w")

    # ---------------------------------------------------------
    # TAB 3: Payment Analytics
    # ---------------------------------------------------------
    def _build_payment_tab(self):
        parent = self.tab_payments

        top_pay = tk.Frame(parent, bg="#F1F5F9", padx=12, pady=8)
        top_pay.pack(fill=tk.X, pady=(0, 8))

        self.lbl_pay_ref_rate = tk.Label(
            top_pay,
            text="💳 Payment Reference Capture Rate: 0.0%  |  Total Collections: ₹0.00",
            font=("Segoe UI", 9, "bold"),
            fg="#0F766E",
            bg="#F1F5F9",
        )
        self.lbl_pay_ref_rate.pack(side=tk.LEFT)

        # Payment Status Breakdown Table
        cols = ("status", "count", "amount", "with_ref")
        self.tree_pay = ttk.Treeview(parent, columns=cols, show="headings", height=6)
        self.tree_pay.heading("status", text="Payment Status")
        self.tree_pay.heading("count", text="Transactions")
        self.tree_pay.heading("amount", text="Total Amount (₹)")
        self.tree_pay.heading("with_ref", text="With Reference No.")

        self.tree_pay.column("status", width=140)
        self.tree_pay.column("count", width=120, anchor="center")
        self.tree_pay.column("amount", width=160, anchor="e")
        self.tree_pay.column("with_ref", width=140, anchor="center")

        self.tree_pay.pack(fill=tk.X, pady=(0, 10))

        # Date-wise Collections
        tk.Label(parent, text="📅 Date-wise Donation Receipts (Paid Bookings):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        cols_date = ("date", "paid_cnt", "amount")
        self.tree_pay_dates = ttk.Treeview(parent, columns=cols_date, show="headings", height=6)
        self.tree_pay_dates.heading("date", text="Receipt Date")
        self.tree_pay_dates.heading("paid_cnt", text="Paid Bookings")
        self.tree_pay_dates.heading("amount", text="Daily Collection (₹)")

        self.tree_pay_dates.column("date", width=140)
        self.tree_pay_dates.column("paid_cnt", width=120, anchor="center")
        self.tree_pay_dates.column("amount", width=160, anchor="e")
        self.tree_pay_dates.pack(fill=tk.BOTH, expand=True)

    # ---------------------------------------------------------
    # TAB 4: Document Compliance & Tickets
    # ---------------------------------------------------------
    def _build_document_tab(self):
        parent = self.tab_documents

        top_doc = tk.Frame(parent, bg="#F1F5F9", padx=12, pady=8)
        top_doc.pack(fill=tk.X, pady=(0, 8))

        self.lbl_doc_summary = tk.Label(
            top_doc,
            text="📁 Ticket PDF Compliance: 0% Attached  |  Incomplete Document Profiles: 0",
            font=("Segoe UI", 9, "bold"),
            fg="#1E3A8A",
            bg="#F1F5F9",
        )
        self.lbl_doc_summary.pack(side=tk.LEFT)

        # Missing Tickets Table
        tk.Label(parent, text="📄 Booked Families Missing Official Ticket PDFs:", font=("Segoe UI", 9, "bold"), fg="#991B1B").pack(anchor="w", pady=(4, 2))

        cols = ("code", "name", "phone", "booked_at")
        self.tree_missing_tickets = ttk.Treeview(parent, columns=cols, show="headings", height=8)
        self.tree_missing_tickets.heading("code", text="Family Code")
        self.tree_missing_tickets.heading("name", text="Family Name")
        self.tree_missing_tickets.heading("phone", text="Phone")
        self.tree_missing_tickets.heading("booked_at", text="Booked Date")

        self.tree_missing_tickets.column("code", width=120)
        self.tree_missing_tickets.column("name", width=180)
        self.tree_missing_tickets.column("phone", width=120)
        self.tree_missing_tickets.column("booked_at", width=140, anchor="center")
        self.tree_missing_tickets.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.lbl_dup_warnings = tk.Label(parent, text="Duplicate Ticket Checksums: None detected.", font=("Segoe UI", 8), fg="#15803D")
        self.lbl_dup_warnings.pack(anchor="w")

    # ---------------------------------------------------------
    # TAB 5: Operational Insights & Suggested Queue Order
    # ---------------------------------------------------------
    def _build_ops_tab(self):
        parent = self.tab_ops

        # Top Insights Container
        f_ins = tk.LabelFrame(parent, text=" Rule-Based Operational Findings & Audit Alerts ", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        f_ins.pack(fill=tk.X, pady=(0, 10))

        self.txt_insights = tk.Text(f_ins, height=4, font=("Segoe UI", 8), bg="#F8FAFC", relief="solid", borderwidth=1, padx=6, pady=4)
        self.txt_insights.pack(fill=tk.X)
        self.txt_insights.config(state="disabled")

        # Suggested Queue Table
        tk.Label(
            parent,
            text="🎯 Suggested Sequential Queue Order (Ranked by Heuristic Priority Score):",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
        ).pack(anchor="w", pady=(4, 2))

        cols = ("rank", "score", "code", "name", "pilgrims", "date", "reasons")
        self.tree_recs = ttk.Treeview(parent, columns=cols, show="headings", height=9)

        self.tree_recs.heading("rank", text="Rank")
        self.tree_recs.heading("score", text="Score")
        self.tree_recs.heading("code", text="Family Code")
        self.tree_recs.heading("name", text="Family Name")
        self.tree_recs.heading("pilgrims", text="Devotees")
        self.tree_recs.heading("date", text="Preferred Date")
        self.tree_recs.heading("reasons", text="Prioritization Reasoning Tags")

        self.tree_recs.column("rank", width=50, anchor="center")
        self.tree_recs.column("score", width=60, anchor="center")
        self.tree_recs.column("code", width=110)
        self.tree_recs.column("name", width=150)
        self.tree_recs.column("pilgrims", width=70, anchor="center")
        self.tree_recs.column("date", width=100, anchor="center")
        self.tree_recs.column("reasons", width=260)

        self.tree_recs.pack(fill=tk.BOTH, expand=True)

    # ---------------------------------------------------------
    # Filtering & Refresh Logic
    # ---------------------------------------------------------
    def _on_filter_changed(self, event=None):
        val = self.filter_combo.get()
        if val == "Custom Range":
            self.custom_frame.pack(side=tk.LEFT, padx=(4, 6))
        else:
            self.custom_frame.pack_forget()
            mapping = {
                "All Time": "all",
                "Today": "today",
                "Last 7 Days": "7days",
                "Last 30 Days": "30days",
                "This Month": "this_month",
            }
            self.active_filter = mapping.get(val, "all")
            self.custom_start = ""
            self.custom_end = ""
            self.refresh_analytics()

    def _on_custom_apply(self):
        s = self.ent_start.get().strip()
        e = self.ent_end.get().strip()
        if not s and not e:
            messagebox.showwarning("Custom Filter", "Please provide at least a start or end date (YYYY-MM-DD).", parent=self)
            return
        self.active_filter = "custom"
        self.custom_start = s
        self.custom_end = e
        self.refresh_analytics()

    def refresh_analytics(self):
        """Fetch updated analytics calculations and refresh all dashboard widgets."""
        try:
            summary = get_analytics_summary(self.db_path, self.active_filter, self.custom_start, self.custom_end)
            perf = get_booking_performance(self.db_path, self.active_filter, self.custom_start, self.custom_end)
            queue = get_queue_intelligence(self.db_path)
            pay = get_payment_analytics(self.db_path, self.active_filter, self.custom_start, self.custom_end)
            doc = get_document_analytics(self.db_path)
            ops = get_operational_intelligence(self.db_path)

            # 1. Update Scope Banner
            self.lbl_filter_scope.config(text=f"Scope: {summary['filter_label']}  |  Live SQLite Database Records")

            # 2. Update KPI Cards
            self.cards["total_families"].config(text=str(summary["total_families"]))
            self.cards["total_pilgrims"].config(text=str(summary["total_pilgrims"]))
            self.cards["completed_bookings"].config(text=f"{summary['completed_bookings']} ({summary['booking_completion_percentage']}%)")
            self.cards["pending_bookings"].config(text=str(summary["pending_bookings"]))
            self.cards["processing_rate"].config(text=f"{perf['processing_completion_rate']}%")
            self.cards["total_revenue"].config(text=f"₹{pay['total_revenue_collected']:,.2f}")

            # 3. Update Performance Tab
            self.lbl_turnaround.config(
                text=f"⚡ Average Lead Time: {perf['avg_turnaround_hours']} Hours ({perf['avg_turnaround_days']} Days)  |  Processed vs Backlog: {perf['total_processed']} / {perf['total_backlog']}"
            )
            for item in self.tree_perf.get_children():
                self.tree_perf.delete(item)
            for r in perf["daily_trends"]:
                self.tree_perf.insert("", "end", values=(
                    r["activity_date"],
                    r["total_families"],
                    r["booked"],
                    r["pending"],
                    r["unavailable"],
                    r["cancelled"],
                    r["pilgrims_count"],
                    f"{r['booked_revenue']:,.2f}",
                ))

            # 4. Update Queue Tab
            b_txt = "  |  ".join(f"{b}: {cnt}" for b, cnt in queue["aging_buckets"].items())
            self.lbl_aging_metrics.config(text=b_txt)

            if queue["oldest_pending"]:
                op = queue["oldest_pending"]
                self.lbl_oldest_record.config(text=f"'{op['family_name']}' ({op['family_code']}) — Waiting {op['days_in_queue']} days ({op['priority']})")
            else:
                self.lbl_oldest_record.config(text="No pending families in queue.")

            for item in self.tree_attention.get_children():
                self.tree_attention.delete(item)
            for r in queue["attention_items"]:
                self.tree_attention.insert("", "end", values=(
                    r.get("family_code"),
                    r.get("family_name"),
                    r.get("phone", "—"),
                    r.get("reason"),
                    r.get("created_at"),
                ))
            self.lbl_bottlenecks.config(text="  •  ".join(queue["bottleneck_insights"]))

            # 5. Update Payments Tab
            self.lbl_pay_ref_rate.config(
                text=f"💳 Reference Capture Rate: {pay['payment_ref_capture_rate']}%  |  Total Revenue: ₹{pay['total_revenue_collected']:,.2f}  |  Paid Bookings: {pay['paid_transactions_count']}"
            )
            for item in self.tree_pay.get_children():
                self.tree_pay.delete(item)
            for pst, pinfo in pay["payment_summary"].items():
                self.tree_pay.insert("", "end", values=(
                    pst,
                    pinfo["count"],
                    f"₹{pinfo['amount']:,.2f}",
                    pinfo.get("with_ref", 0),
                ))

            for item in self.tree_pay_dates.get_children():
                self.tree_pay_dates.delete(item)
            for r in pay["date_wise_collections"]:
                self.tree_pay_dates.insert("", "end", values=(
                    r["tx_date"],
                    r["paid_count"],
                    f"₹{r['daily_amount']:,.2f}",
                ))

            # 6. Update Documents Tab
            self.lbl_doc_summary.config(
                text=f"📁 Ticket Compliance: {doc['ticket_compliance_percentage']}% Attached ({doc['booked_with_tickets']} of {doc['booked_families_total']})  |  Incomplete Devotee Profiles: {doc['incomplete_document_families_count']}"
            )
            for item in self.tree_missing_tickets.get_children():
                self.tree_missing_tickets.delete(item)
            for r in doc["missing_tickets"]:
                self.tree_missing_tickets.insert("", "end", values=(
                    r["family_code"],
                    r["family_name"],
                    r["phone"] or "—",
                    r["booked_at"] or "Booked",
                ))

            if doc["duplicate_ticket_warnings"]:
                self.lbl_dup_warnings.config(
                    text=f"⚠️ {len(doc['duplicate_ticket_warnings'])} duplicate ticket checksums detected across multiple records!",
                    fg="#DC2626",
                )
            else:
                self.lbl_dup_warnings.config(text="✅ Zero duplicate ticket checksums detected.", fg="#15803D")

            # 7. Update Operational Insights Tab
            self.txt_insights.config(state="normal")
            self.txt_insights.delete("1.0", tk.END)
            if ops["insights"]:
                for ins in ops["insights"]:
                    self.txt_insights.insert(tk.END, f"[{ins['severity']}] {ins['category']} — {ins['title']}: {ins['description']}\n")
            else:
                self.txt_insights.insert(tk.END, "✓ All operational audits healthy: Zero critical bottlenecks or payment discrepancies.\n")
            self.txt_insights.config(state="disabled")

            for item in self.tree_recs.get_children():
                self.tree_recs.delete(item)
            for r_idx, rec in enumerate(ops["recommended_queue"], start=1):
                self.tree_recs.insert("", "end", values=(
                    f"#{r_idx}",
                    rec["score"],
                    rec["family_code"],
                    rec["family_name"],
                    rec["pilgrim_count"],
                    rec["preferred_date"] or "—",
                    ", ".join(rec["reasons"]),
                ))

        except Exception as e:
            logger.error(f"Error refreshing analytics view: {e}")

    # ---------------------------------------------------------
    # Export Handlers
    # ---------------------------------------------------------
    def _export_excel_workbook(self):
        default_name = f"Srivani_Operational_Analytics_{datetime.datetime.now():%Y%m%d_%H%M}.xlsx"
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Export Full Analytics Workbook (.xlsx)",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbooks (*.xlsx)", "*.xlsx")],
            initialfile=default_name,
        )
        if not dest:
            return

        try:
            out_p = export_full_analytics_workbook_xlsx(
                dest,
                self.db_path,
                self.active_filter,
                self.custom_start,
                self.custom_end,
            )
            ans = messagebox.askyesno(
                "Export Complete",
                f"Multi-tab Excel analytics workbook generated:\n{out_p}\n\nOpen it now?",
                parent=self,
            )
            if ans:
                os.startfile(out_p)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Excel workbook: {e}", parent=self)

    def _export_pdf_report(self):
        default_name = f"Srivani_Executive_Analytics_{datetime.datetime.now():%Y%m%d_%H%M}.pdf"
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Export Executive Analytics PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Documents (*.pdf)", "*.pdf")],
            initialfile=default_name,
        )
        if not dest:
            return

        try:
            out_p = export_analytics_report_pdf(
                "analytics_summary",
                dest,
                self.db_path,
                self.active_filter,
                self.custom_start,
                self.custom_end,
            )
            ans = messagebox.askyesno(
                "PDF Export Complete",
                f"Printable executive analytics PDF generated:\n{out_p}\n\nOpen it now?",
                parent=self,
            )
            if ans:
                os.startfile(out_p)
        except Exception as e:
            messagebox.showerror("PDF Export Error", f"Failed to generate analytics PDF: {e}", parent=self)

    def _export_csv(self, category: str):
        default_name = f"Srivani_{category}_{datetime.datetime.now():%Y%m%d_%H%M}.csv"
        dest = filedialog.asksaveasfilename(
            parent=self,
            title=f"Export {category.capitalize()} (.csv)",
            defaultextension=".csv",
            filetypes=[("CSV Documents (*.csv)", "*.csv")],
            initialfile=default_name,
        )
        if not dest:
            return

        try:
            if category == "summary":
                export_summary_to_csv(dest, self.db_path, self.active_filter, self.custom_start, self.custom_end)
            elif category == "performance":
                export_performance_to_csv(dest, self.db_path, self.active_filter, self.custom_start, self.custom_end)
            elif category == "queue":
                export_queue_intelligence_to_csv(dest, self.db_path)
            messagebox.showinfo("Export Complete", f"{category.capitalize()} report exported to:\n{dest}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}", parent=self)
