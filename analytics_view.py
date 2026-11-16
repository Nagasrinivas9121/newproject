"""
SRIVANI BOOKING MANAGER - Interactive Analytics & Operational Intelligence UI
Phase 7 Upgrade: Professional Analytics Dashboard, Interactive Canvas Charts,
Queue Intelligence, Family-Level Analytics, Payment Reconciliation, Document Compliance,
Configurable Operational Intelligence, and Multi-Format Report Generation.
Strictly relies on real SQLite database records; zero fabricated statistics.
"""
import sys
import os
import datetime
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import DB_PATH
from analytics_engine import (
    parse_date_filter,
    get_analytics_summary,
    get_booking_performance,
    get_queue_intelligence,
    get_family_analytics,
    get_payment_analytics,
    get_document_analytics,
    get_operational_intelligence,
    get_operational_intelligence_config,
    save_operational_intelligence_config,
)
from analytics_export import (
    export_summary_to_csv,
    export_performance_to_csv,
    export_queue_intelligence_to_csv,
    export_daily_report_csv,
    export_weekly_report_csv,
    export_monthly_report_csv,
    export_family_report_csv,
    export_payment_report_csv,
    export_full_analytics_workbook_xlsx,
    export_daily_report_xlsx,
    export_weekly_report_xlsx,
    export_monthly_report_xlsx,
    export_family_report_xlsx,
    export_payment_report_xlsx,
    export_analytics_report_pdf,
    export_report,
)
from analytics_charts import CanvasBarChart, CanvasDonutChart, CanvasLineChart
from themes import get_theme_palette, get_current_theme_name
from logger import get_logger

logger = get_logger("analytics_view")


class AnalyticsRuleConfigDialog(tk.Toplevel):
    """
    Admin configuration dialog for operational intelligence alert thresholds
    and queue prioritization scoring weights.
    """
    def __init__(self, parent, db_path: Optional[Path] = None, on_saved=None):
        super().__init__(parent)
        self.db_path = db_path
        self.on_saved = on_saved

        self.title("⚙️ Configure Operational Intelligence & Queue Rules")
        self.geometry("560x520")
        self.minsize(500, 460)
        self.configure(bg="#F8FAFC")
        self.transient(parent)
        self.grab_set()

        self.config_data = get_operational_intelligence_config(self.db_path)
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
        # Header
        hdr = tk.Frame(self, bg="#0F172A", padx=16, pady=12)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr,
            text="OPERATIONAL THRESHOLDS & QUEUE WEIGHTS",
            font=("Segoe UI", 11, "bold"),
            fg="#F59E0B",
            bg="#0F172A",
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text="Adjust alert sensitivities and heuristic queue prioritization scoring weights.",
            font=("Segoe UI", 8),
            fg="#94A3B8",
            bg="#0F172A",
        ).pack(anchor="w", pady=(2, 0))

        content = tk.Frame(self, bg="#F8FAFC", padx=20, pady=14)
        content.pack(fill=tk.BOTH, expand=True)

        # 1. Alert Thresholds Section
        f_alerts = tk.LabelFrame(content, text=" Rule-Based Alert Sensitivities ", font=("Segoe UI", 9, "bold"), bg="#F8FAFC", padx=12, pady=8)
        f_alerts.pack(fill=tk.X, pady=(0, 12))

        # Stale Pending Days
        r1 = tk.Frame(f_alerts, bg="#F8FAFC")
        r1.pack(fill=tk.X, pady=3)
        tk.Label(r1, text="Stale Pending Queue Threshold (Days):", font=("Segoe UI", 9), bg="#F8FAFC").pack(side=tk.LEFT)
        self.spn_stale = ttk.Spinbox(r1, from_=1, to=60, width=6)
        self.spn_stale.set(int(self.config_data.get("stale_pending_days", 7)))
        self.spn_stale.pack(side=tk.RIGHT)

        # Stalled In Progress Hours
        r2 = tk.Frame(f_alerts, bg="#F8FAFC")
        r2.pack(fill=tk.X, pady=3)
        tk.Label(r2, text="Stalled In Progress Threshold (Hours):", font=("Segoe UI", 9), bg="#F8FAFC").pack(side=tk.LEFT)
        self.spn_stalled = ttk.Spinbox(r2, from_=1, to=168, width=6)
        self.spn_stalled.set(int(self.config_data.get("stalled_in_prog_hours", 24)))
        self.spn_stalled.pack(side=tk.RIGHT)

        # Imminent Date Days
        r3 = tk.Frame(f_alerts, bg="#F8FAFC")
        r3.pack(fill=tk.X, pady=3)
        tk.Label(r3, text="Imminent Darshan Date Threshold (Days):", font=("Segoe UI", 9), bg="#F8FAFC").pack(side=tk.LEFT)
        self.spn_imminent = ttk.Spinbox(r3, from_=1, to=30, width=6)
        self.spn_imminent.set(int(self.config_data.get("imminent_date_days", 3)))
        self.spn_imminent.pack(side=tk.RIGHT)

        # 2. Queue Prioritization Weights Section
        f_weights = tk.LabelFrame(content, text=" Queue Prioritization Scoring Weights ", font=("Segoe UI", 9, "bold"), bg="#F8FAFC", padx=12, pady=8)
        f_weights.pack(fill=tk.X, pady=(0, 14))

        weights_cfg = [
            ("weight_urgent", "Urgent Priority Flag Weight:", 40),
            ("weight_high", "High Priority Flag Weight:", 25),
            ("weight_normal", "Normal Priority Flag Weight:", 10),
            ("weight_date_imminent", "Imminent Target Date Bonus:", 50),
            ("weight_aging_7d", "Queue Aging (> 7d) Bonus:", 25),
            ("weight_docs_ready", "Documents 100% Ready Bonus:", 15),
        ]
        self.weight_entries: Dict[str, ttk.Spinbox] = {}
        for key, lbl_text, default_v in weights_cfg:
            rw = tk.Frame(f_weights, bg="#F8FAFC")
            rw.pack(fill=tk.X, pady=2)
            tk.Label(rw, text=lbl_text, font=("Segoe UI", 9), bg="#F8FAFC").pack(side=tk.LEFT)
            spn = ttk.Spinbox(rw, from_=0, to=100, width=6)
            spn.set(int(self.config_data.get(key, default_v)))
            spn.pack(side=tk.RIGHT)
            self.weight_entries[key] = spn

        # Footer Buttons
        btn_bar = tk.Frame(self, bg="#E2E8F0", padx=16, pady=10)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_cancel = tk.Button(
            btn_bar,
            text="Cancel",
            font=("Segoe UI", 9),
            bg="#94A3B8",
            fg="white",
            relief="flat",
            padx=12,
            pady=4,
            command=self.destroy,
        )
        btn_cancel.pack(side=tk.RIGHT, padx=(8, 0))

        btn_save = tk.Button(
            btn_bar,
            text="💾 Save Configuration",
            font=("Segoe UI", 9, "bold"),
            bg="#16A34A",
            fg="white",
            relief="flat",
            padx=14,
            pady=4,
            command=self._save_config,
        )
        btn_save.pack(side=tk.RIGHT)

    def _save_config(self):
        try:
            new_cfg = {
                "stale_pending_days": float(self.spn_stale.get()),
                "stalled_in_prog_hours": float(self.spn_stalled.get()),
                "imminent_date_days": int(self.spn_imminent.get()),
            }
            for k, spn in self.weight_entries.items():
                new_cfg[k] = int(spn.get())

            save_operational_intelligence_config(new_cfg, self.db_path)
            messagebox.showinfo("Rules Saved", "Operational intelligence rules and queue weights successfully updated.", parent=self)
            if self.on_saved:
                self.on_saved()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save rules configuration: {e}", parent=self)


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
        self.chart_mode = "daily"  # 'daily', 'weekly', 'monthly', 'outcomes'
        self.is_loading = False

        self._build_ui()
        self.refresh_analytics()

    def _build_ui(self):
        # 1. Top Header & Date Filter Toolbar
        self._build_top_filter_bar()

        # 2. Executive 9-KPI Summary Cards
        self._build_kpi_cards()

        # 3. Main Multi-Tab Analytics Workspace
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 10))

        # Tab 1: Booking Performance & Interactive Charts
        self.tab_performance = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_performance, text="📈 Performance & Charts")
        self._build_performance_tab()

        # Tab 2: Queue Intelligence & Aging
        self.tab_queue = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_queue, text="⏱️ Queue Intelligence")
        self._build_queue_tab()

        # Tab 3: Family Analytics (New in Phase 7)
        self.tab_family = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_family, text="👥 Family Analytics")
        self._build_family_tab()

        # Tab 4: Payment Analytics
        self.tab_payments = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_payments, text="💳 Payment Analytics")
        self._build_payment_tab()

        # Tab 5: Document Compliance & Checksums
        self.tab_documents = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_documents, text="📁 Document Compliance")
        self._build_document_tab()

        # Tab 6: Operational Intelligence & Prioritization Engine
        self.tab_ops = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_ops, text="💡 Operational Insights & Queue Order")
        self._build_ops_tab()

    def _build_top_filter_bar(self):
        top_bar = tk.Frame(self, bg="#0F172A", padx=16, pady=8)
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

        # Right Controls: Filter Selector + Export Dropdown + Refresh Button
        ctrl_box = tk.Frame(top_bar, bg="#0F172A")
        ctrl_box.pack(side=tk.RIGHT)

        # Loading status badge
        self.lbl_loading = tk.Label(
            ctrl_box,
            text="",
            font=("Segoe UI", 8, "bold"),
            fg="#38BDF8",
            bg="#0F172A",
        )
        self.lbl_loading.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(ctrl_box, text="Date Filter:", font=("Segoe UI", 9, "bold"), fg="#E2E8F0", bg="#0F172A").pack(side=tk.LEFT, padx=(0, 4))

        self.filter_combo = ttk.Combobox(
            ctrl_box,
            values=["All Time", "Today", "Last 7 Days", "Last 30 Days", "This Month", "Custom Range"],
            state="readonly",
            width=12,
        )
        self.filter_combo.set("All Time")
        self.filter_combo.pack(side=tk.LEFT, padx=(0, 4))
        self.filter_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Custom date entries
        self.custom_frame = tk.Frame(ctrl_box, bg="#0F172A")
        tk.Label(self.custom_frame, text="From:", font=("Segoe UI", 8), fg="#CBD5E1", bg="#0F172A").pack(side=tk.LEFT, padx=(2, 2))
        self.ent_start = ttk.Entry(self.custom_frame, width=9)
        self.ent_start.pack(side=tk.LEFT, padx=(0, 2))

        tk.Label(self.custom_frame, text="To:", font=("Segoe UI", 8), fg="#CBD5E1", bg="#0F172A").pack(side=tk.LEFT, padx=(2, 2))
        self.ent_end = ttk.Entry(self.custom_frame, width=9)
        self.ent_end.pack(side=tk.LEFT, padx=(0, 4))

        btn_apply = tk.Button(
            self.custom_frame,
            text="Apply",
            font=("Segoe UI", 8, "bold"),
            bg="#0284C7",
            fg="white",
            relief="flat",
            padx=6,
            pady=1,
            command=self._on_custom_apply,
        )
        btn_apply.pack(side=tk.LEFT, padx=(0, 4))

        # Export Dropdown Menu
        self.btn_export = tk.Menubutton(
            ctrl_box,
            text="📥 Export Reports ▾",
            font=("Segoe UI", 9, "bold"),
            bg="#2563EB",
            fg="white",
            relief="flat",
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.export_menu = tk.Menu(self.btn_export, tearoff=0)
        self.export_menu.add_command(label="📊 Full Analytics Workbook (.xlsx)", command=lambda: self._export_dispatcher("workbook", "xlsx"))
        self.export_menu.add_command(label="📄 Executive Printable Report (.pdf)", command=lambda: self._export_dispatcher("summary", "pdf"))
        self.export_menu.add_separator()
        self.export_menu.add_command(label="📅 Daily Booking Report (Excel / PDF / CSV)", command=lambda: self._prompt_report_format("daily"))
        self.export_menu.add_command(label="📆 Weekly Operational Report (Excel / PDF / CSV)", command=lambda: self._prompt_report_format("weekly"))
        self.export_menu.add_command(label="🗓️ Monthly Booking Report (Excel / PDF / CSV)", command=lambda: self._prompt_report_format("monthly"))
        self.export_menu.add_command(label="👥 Family Roster Report (Excel / PDF / CSV)", command=lambda: self._prompt_report_format("family"))
        self.export_menu.add_command(label="💳 Payment Reconciliation Report (Excel / PDF / CSV)", command=lambda: self._prompt_report_format("payment"))
        self.export_menu.add_command(label="⏱️ Queue Intelligence Audit (Excel / PDF / CSV)", command=lambda: self._prompt_report_format("queue"))
        self.btn_export.config(menu=self.export_menu)
        self.btn_export.pack(side=tk.LEFT, padx=(0, 4))

        # Rules Config Button
        btn_config = tk.Button(
            ctrl_box,
            text="⚙️ Rules",
            font=("Segoe UI", 9),
            bg="#475569",
            fg="white",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._open_rule_config,
        )
        btn_config.pack(side=tk.LEFT, padx=(0, 4))

        # Refresh Button
        btn_refresh = tk.Button(
            ctrl_box,
            text="🔄 Refresh",
            font=("Segoe UI", 9),
            bg="#334155",
            fg="#F8FAFC",
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.refresh_analytics,
        )
        btn_refresh.pack(side=tk.LEFT)

    def _build_kpi_cards(self):
        """Build Module 1 all 9-KPI cards row."""
        kpi_bar = ttk.Frame(self, padding=(16, 6, 16, 2))
        kpi_bar.pack(fill=tk.X)

        self.cards = {}
        # 9 Required Metrics
        configs = [
            ("total_families", "1. FAMILIES", "0", "#1E3A8A"),
            ("total_pilgrims", "2. PILGRIMS", "0", "#4338CA"),
            ("completed_bookings", "3. COMPLETED", "0", "#15803D"),
            ("pending_bookings", "4. PENDING", "0", "#B45309"),
            ("in_progress_bookings", "5. IN PROGRESS", "0", "#0369A1"),
            ("unavailable_bookings", "6. UNAVAIL.", "0", "#64748B"),
            ("cancelled_bookings", "7. CANCELLED", "0", "#DC2626"),
            ("payment_summary", "8. REVENUE", "₹0.00", "#0F766E"),
            ("completion_rate", "9. COMPL. RATE", "0%", "#7C3AED"),
        ]

        for idx, (key, label, default_val, color) in enumerate(configs):
            card = tk.Frame(kpi_bar, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1, padx=8, pady=4)
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0 if idx == 0 else 4, 0))

            tk.Label(card, text=label, font=("Segoe UI", 7, "bold"), fg="#64748B", bg="#FFFFFF").pack(anchor="w")
            lbl_val = tk.Label(card, text=default_val, font=("Segoe UI", 11, "bold"), fg=color, bg="#FFFFFF")
            lbl_val.pack(anchor="w", pady=(1, 0))
            self.cards[key] = lbl_val

    # ---------------------------------------------------------
    # TAB 1: Booking Performance & Interactive Charts
    # ---------------------------------------------------------
    def _build_performance_tab(self):
        parent = self.tab_performance

        # Top Control Row: Chart View Switcher + Turnaround KPI Banner
        ctrl_strip = tk.Frame(parent, bg="#F1F5F9", padx=10, pady=6)
        ctrl_strip.pack(fill=tk.X, pady=(0, 6))

        tk.Label(ctrl_strip, text="Chart View:", font=("Segoe UI", 9, "bold"), bg="#F1F5F9", fg="#0F172A").pack(side=tk.LEFT, padx=(0, 6))

        self.btn_chart_daily = tk.Button(
            ctrl_strip, text="📅 Daily Trend", font=("Segoe UI", 8, "bold"), bg="#2563EB", fg="white", relief="flat", padx=8, pady=2,
            command=lambda: self._set_chart_mode("daily"),
        )
        self.btn_chart_daily.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_chart_weekly = tk.Button(
            ctrl_strip, text="📆 Weekly", font=("Segoe UI", 8), bg="#E2E8F0", fg="#334155", relief="flat", padx=8, pady=2,
            command=lambda: self._set_chart_mode("weekly"),
        )
        self.btn_chart_weekly.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_chart_monthly = tk.Button(
            ctrl_strip, text="🗓️ Monthly", font=("Segoe UI", 8), bg="#E2E8F0", fg="#334155", relief="flat", padx=8, pady=2,
            command=lambda: self._set_chart_mode("monthly"),
        )
        self.btn_chart_monthly.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_chart_outcomes = tk.Button(
            ctrl_strip, text="🍩 Booking Outcomes", font=("Segoe UI", 8), bg="#E2E8F0", fg="#334155", relief="flat", padx=8, pady=2,
            command=lambda: self._set_chart_mode("outcomes"),
        )
        self.btn_chart_outcomes.pack(side=tk.LEFT, padx=(0, 8))

        self.lbl_turnaround = tk.Label(
            ctrl_strip,
            text="⚡ Average Lead Time: 0.0 Hours  |  Processed vs Backlog: 0 / 0",
            font=("Segoe UI", 9, "bold"),
            fg="#0F766E",
            bg="#F1F5F9",
        )
        self.lbl_turnaround.pack(side=tk.RIGHT)

        # Upper Area: Interactive Chart Container (Height ~ 190)
        chart_frame = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        chart_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 8))
        chart_frame.config(height=190)

        self.perf_bar_chart = CanvasBarChart(chart_frame, height=185)
        self.perf_bar_chart.pack(fill=tk.BOTH, expand=True)

        self.perf_donut_chart = CanvasDonutChart(chart_frame, height=185)
        # Hidden initially; shown when mode is 'outcomes'

        # Lower Area: Detailed Trends Data Table
        table_container = ttk.Frame(parent)
        table_container.pack(fill=tk.BOTH, expand=True)

        cols = ("date", "total", "booked", "pending", "unavailable", "cancelled", "pilgrims", "revenue")
        self.tree_perf = ttk.Treeview(table_container, columns=cols, show="headings", height=8)

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
        widths = {"date": 110, "total": 95, "booked": 80, "pending": 80, "unavailable": 90, "cancelled": 80, "pilgrims": 80, "revenue": 130}

        for c in cols:
            self.tree_perf.heading(c, text=headings[c])
            align = "e" if c == "revenue" else ("center" if c != "date" else "w")
            self.tree_perf.column(c, width=widths[c], anchor=align)

        y_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.tree_perf.yview)
        self.tree_perf.configure(yscrollcommand=y_scroll.set)
        self.tree_perf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _set_chart_mode(self, mode: str):
        self.chart_mode = mode
        # Update button highlights
        buttons = [
            ("daily", self.btn_chart_daily),
            ("weekly", self.btn_chart_weekly),
            ("monthly", self.btn_chart_monthly),
            ("outcomes", self.btn_chart_outcomes),
        ]
        for m, btn in buttons:
            if m == mode:
                btn.config(bg="#2563EB", fg="white", font=("Segoe UI", 8, "bold"))
            else:
                btn.config(bg="#E2E8F0", fg="#334155", font=("Segoe UI", 8))

        self.refresh_analytics()

    # ---------------------------------------------------------
    # TAB 2: Queue Intelligence & Aging
    # ---------------------------------------------------------
    def _build_queue_tab(self):
        parent = self.tab_queue

        # Top row: Aging Buckets + Oldest Record
        info_row = tk.Frame(parent)
        info_row.pack(fill=tk.X, pady=(0, 6))

        f_aging = tk.LabelFrame(info_row, text=" Queue Aging Breakdown ", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        f_aging.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.lbl_aging_metrics = tk.Label(
            f_aging,
            text="< 24 Hours: 0  |  1–3 Days: 0  |  4–7 Days: 0  |  > 7 Days: 0",
            font=("Segoe UI", 9, "bold"),
            fg="#0284C7",
        )
        self.lbl_aging_metrics.pack(anchor="w", pady=2)

        f_old = tk.LabelFrame(info_row, text=" Oldest Record in Queue ", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        f_old.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.lbl_oldest_record = tk.Label(
            f_old,
            text="None currently pending.",
            font=("Segoe UI", 8),
            fg="#B45309",
        )
        self.lbl_oldest_record.pack(anchor="w", pady=2)

        # In-Progress Family Tracking Section
        tk.Label(parent, text="⚡ In-Progress Family Tracking (Currently Open in Portal/Workspace):", font=("Segoe UI", 9, "bold"), fg="#0F172A").pack(anchor="w", pady=(2, 2))
        cols_inp = ("code", "name", "contact", "phone", "pilgrims", "date", "hours")
        self.tree_in_prog = ttk.Treeview(parent, columns=cols_inp, show="headings", height=4)
        self.tree_in_prog.heading("code", text="Family Code")
        self.tree_in_prog.heading("name", text="Family Name")
        self.tree_in_prog.heading("contact", text="Contact Person")
        self.tree_in_prog.heading("phone", text="Phone")
        self.tree_in_prog.heading("pilgrims", text="Devotees")
        self.tree_in_prog.heading("date", text="Preferred Date")
        self.tree_in_prog.heading("hours", text="Hours In Progress")

        self.tree_in_prog.column("code", width=100)
        self.tree_in_prog.column("name", width=150)
        self.tree_in_prog.column("contact", width=120)
        self.tree_in_prog.column("phone", width=100)
        self.tree_in_prog.column("pilgrims", width=70, anchor="center")
        self.tree_in_prog.column("date", width=100, anchor="center")
        self.tree_in_prog.column("hours", width=120, anchor="center")
        self.tree_in_prog.pack(fill=tk.X, pady=(0, 6))

        # Attention Items Table
        tk.Label(parent, text="⚠️ Records Requiring Administrator Attention:", font=("Segoe UI", 9, "bold"), fg="#1E293B").pack(anchor="w", pady=(4, 2))
        cols_att = ("code", "name", "phone", "reason", "created")
        self.tree_attention = ttk.Treeview(parent, columns=cols_att, show="headings", height=5)
        self.tree_attention.heading("code", text="Family Code")
        self.tree_attention.heading("name", text="Family Name")
        self.tree_attention.heading("phone", text="Phone")
        self.tree_attention.heading("reason", text="Attention Flag / Reason")
        self.tree_attention.heading("created", text="Created Date")

        self.tree_attention.column("code", width=110)
        self.tree_attention.column("name", width=150)
        self.tree_attention.column("phone", width=100)
        self.tree_attention.column("reason", width=220)
        self.tree_attention.column("created", width=130, anchor="center")
        self.tree_attention.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        # Bottleneck Advice & Disclaimer
        self.lbl_bottlenecks = tk.Label(parent, text="", font=("Segoe UI", 8, "italic"), fg="#475569", justify=tk.LEFT)
        self.lbl_bottlenecks.pack(anchor="w")

        disclaimer_lbl = tk.Label(
            parent,
            text="* Disclaimer: Operational intelligence operates on local records and does not predict or guarantee official TTD ticket availability.",
            font=("Segoe UI", 7, "italic"),
            fg="#94A3B8",
        )
        disclaimer_lbl.pack(anchor="w", pady=(2, 0))

    # ---------------------------------------------------------
    # TAB 3: Family Analytics (New in Phase 7)
    # ---------------------------------------------------------
    def _build_family_tab(self):
        parent = self.tab_family

        # Search & Filter Strip
        f_strip = tk.Frame(parent, bg="#F1F5F9", padx=10, pady=6)
        f_strip.pack(fill=tk.X, pady=(0, 6))

        tk.Label(f_strip, text="Search Family:", font=("Segoe UI", 9, "bold"), bg="#F1F5F9").pack(side=tk.LEFT, padx=(0, 4))
        self.ent_fam_search = ttk.Entry(f_strip, width=18)
        self.ent_fam_search.pack(side=tk.LEFT, padx=(0, 8))
        self.ent_fam_search.bind("<Return>", lambda e: self.refresh_family_analytics())

        tk.Label(f_strip, text="Status:", font=("Segoe UI", 9), bg="#F1F5F9").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_fam_status = ttk.Combobox(
            f_strip,
            values=["All", "Booked", "Pending", "In progress", "Unavailable", "Cancelled"],
            state="readonly",
            width=11,
        )
        self.combo_fam_status.set("All")
        self.combo_fam_status.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_fam_status.bind("<<ComboboxSelected>>", lambda e: self.refresh_family_analytics())

        tk.Label(f_strip, text="Ticket PDF:", font=("Segoe UI", 9), bg="#F1F5F9").pack(side=tk.LEFT, padx=(0, 4))
        self.combo_fam_ticket = ttk.Combobox(
            f_strip,
            values=["All", "With Ticket", "Missing Ticket"],
            state="readonly",
            width=13,
        )
        self.combo_fam_ticket.set("All")
        self.combo_fam_ticket.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_fam_ticket.bind("<<ComboboxSelected>>", lambda e: self.refresh_family_analytics())

        btn_fam_go = tk.Button(
            f_strip,
            text="Filter",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="white",
            relief="flat",
            padx=8,
            pady=1,
            command=self.refresh_family_analytics,
        )
        btn_fam_go.pack(side=tk.LEFT)

        self.lbl_fam_count = tk.Label(f_strip, text="Records Found: 0", font=("Segoe UI", 8, "bold"), fg="#0F766E", bg="#F1F5F9")
        self.lbl_fam_count.pack(side=tk.RIGHT)

        # Devotee Distribution Banner
        self.lbl_devotee_dist = tk.Label(
            parent,
            text="Devotee Distribution: Loading...",
            font=("Segoe UI", 8, "italic"),
            fg="#475569",
        )
        self.lbl_devotee_dist.pack(anchor="w", pady=(0, 4))

        # Family Records Table
        fam_table_frame = ttk.Frame(parent)
        fam_table_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("code", "name", "contact", "phone", "pilgrims", "donation", "type", "date", "status", "payment", "ticket")
        self.tree_family = ttk.Treeview(fam_table_frame, columns=cols, show="headings", height=12)

        headings = {
            "code": "Family Code",
            "name": "Family Name",
            "contact": "Contact Person",
            "phone": "Phone",
            "pilgrims": "Devotees",
            "donation": "Donation (₹)",
            "type": "Quota Type",
            "date": "Preferred Date",
            "status": "Booking Status",
            "payment": "Payment Status",
            "ticket": "Ticket Attached",
        }
        widths = {
            "code": 95,
            "name": 140,
            "contact": 110,
            "phone": 95,
            "pilgrims": 65,
            "donation": 90,
            "type": 80,
            "date": 95,
            "status": 95,
            "payment": 95,
            "ticket": 95,
        }

        for c in cols:
            self.tree_family.heading(c, text=headings[c])
            align = "e" if c == "donation" else ("center" if c in ("pilgrims", "date", "ticket") else "w")
            self.tree_family.column(c, width=widths[c], anchor=align)

        y_fam_scroll = ttk.Scrollbar(fam_table_frame, orient="vertical", command=self.tree_family.yview)
        self.tree_family.configure(yscrollcommand=y_fam_scroll.set)
        self.tree_family.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_fam_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # ---------------------------------------------------------
    # TAB 4: Payment Analytics
    # ---------------------------------------------------------
    def _build_payment_tab(self):
        parent = self.tab_payments

        top_pay = tk.Frame(parent, bg="#F1F5F9", padx=10, pady=6)
        top_pay.pack(fill=tk.X, pady=(0, 6))

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
        self.tree_pay = ttk.Treeview(parent, columns=cols, show="headings", height=5)
        self.tree_pay.heading("status", text="Payment Status")
        self.tree_pay.heading("count", text="Transactions")
        self.tree_pay.heading("amount", text="Total Amount (₹)")
        self.tree_pay.heading("with_ref", text="With Reference No.")

        self.tree_pay.column("status", width=140)
        self.tree_pay.column("count", width=120, anchor="center")
        self.tree_pay.column("amount", width=160, anchor="e")
        self.tree_pay.column("with_ref", width=140, anchor="center")
        self.tree_pay.pack(fill=tk.X, pady=(0, 8))

        # Date-wise Collections Table
        tk.Label(parent, text="📅 Date-wise Donation Receipts (Paid Bookings):", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))
        cols_date = ("date", "paid_cnt", "amount")
        self.tree_pay_dates = ttk.Treeview(parent, columns=cols_date, show="headings", height=7)
        self.tree_pay_dates.heading("date", text="Receipt Date")
        self.tree_pay_dates.heading("paid_cnt", text="Paid Bookings")
        self.tree_pay_dates.heading("amount", text="Daily Collection (₹)")

        self.tree_pay_dates.column("date", width=140)
        self.tree_pay_dates.column("paid_cnt", width=120, anchor="center")
        self.tree_pay_dates.column("amount", width=160, anchor="e")
        self.tree_pay_dates.pack(fill=tk.BOTH, expand=True)

        pay_note = tk.Label(
            parent,
            text="🔒 Security Assurance: Client banking credentials, card numbers, OTPs, and UPI PINs are strictly never requested or stored.",
            font=("Segoe UI", 8, "italic"),
            fg="#64748B",
        )
        pay_note.pack(anchor="w", pady=(4, 0))

    # ---------------------------------------------------------
    # TAB 5: Document Compliance & Checksums
    # ---------------------------------------------------------
    def _build_document_tab(self):
        parent = self.tab_documents

        top_doc = tk.Frame(parent, bg="#F1F5F9", padx=10, pady=6)
        top_doc.pack(fill=tk.X, pady=(0, 6))

        self.lbl_doc_summary = tk.Label(
            top_doc,
            text="📁 Ticket PDF Compliance: 0% Attached  |  Incomplete Devotee Profiles: 0",
            font=("Segoe UI", 9, "bold"),
            fg="#1E3A8A",
            bg="#F1F5F9",
        )
        self.lbl_doc_summary.pack(side=tk.LEFT)

        # Incomplete Profiles Table (Missing identity info)
        tk.Label(parent, text="⚠️ Incomplete Devotee Records (Missing Proof Type or Last-4 or Contact Phone):", font=("Segoe UI", 9, "bold"), fg="#B45309").pack(anchor="w", pady=(2, 2))
        cols_inc = ("code", "name", "phone", "devotees", "issues")
        self.tree_incomplete_docs = ttk.Treeview(parent, columns=cols_inc, show="headings", height=5)
        self.tree_incomplete_docs.heading("code", text="Family Code")
        self.tree_incomplete_docs.heading("name", text="Family Name")
        self.tree_incomplete_docs.heading("phone", text="Phone")
        self.tree_incomplete_docs.heading("devotees", text="Devotees")
        self.tree_incomplete_docs.heading("issues", text="Missing Information Details")

        self.tree_incomplete_docs.column("code", width=100)
        self.tree_incomplete_docs.column("name", width=150)
        self.tree_incomplete_docs.column("phone", width=100)
        self.tree_incomplete_docs.column("devotees", width=70, anchor="center")
        self.tree_incomplete_docs.column("issues", width=250)
        self.tree_incomplete_docs.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        # Missing Tickets Table
        tk.Label(parent, text="📄 Booked Families Missing Official Ticket PDFs:", font=("Segoe UI", 9, "bold"), fg="#991B1B").pack(anchor="w", pady=(2, 2))
        cols_t = ("code", "name", "phone", "booked_at")
        self.tree_missing_tickets = ttk.Treeview(parent, columns=cols_t, show="headings", height=5)
        self.tree_missing_tickets.heading("code", text="Family Code")
        self.tree_missing_tickets.heading("name", text="Family Name")
        self.tree_missing_tickets.heading("phone", text="Phone")
        self.tree_missing_tickets.heading("booked_at", text="Booked Date")

        self.tree_missing_tickets.column("code", width=110)
        self.tree_missing_tickets.column("name", width=180)
        self.tree_missing_tickets.column("phone", width=110)
        self.tree_missing_tickets.column("booked_at", width=130, anchor="center")
        self.tree_missing_tickets.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        self.lbl_dup_warnings = tk.Label(parent, text="Duplicate Ticket Checksums: None detected.", font=("Segoe UI", 8), fg="#15803D")
        self.lbl_dup_warnings.pack(anchor="w")

    # ---------------------------------------------------------
    # TAB 6: Operational Insights & Queue Order
    # ---------------------------------------------------------
    def _build_ops_tab(self):
        parent = self.tab_ops

        # Top Insights Container
        f_ins = tk.LabelFrame(parent, text=" Rule-Based Operational Findings & Audit Alerts ", font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        f_ins.pack(fill=tk.X, pady=(0, 8))

        self.txt_insights = tk.Text(f_ins, height=4, font=("Segoe UI", 8), bg="#F8FAFC", relief="solid", borderwidth=1, padx=6, pady=4)
        self.txt_insights.pack(fill=tk.X)
        self.txt_insights.config(state="disabled")

        # Suggested Queue Table
        tk.Label(
            parent,
            text="🎯 Suggested Sequential Queue Order (Ranked by Heuristic Priority Score):",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
        ).pack(anchor="w", pady=(2, 2))

        cols = ("rank", "score", "code", "name", "pilgrims", "date", "reasons")
        self.tree_recs = ttk.Treeview(parent, columns=cols, show="headings", height=9)
        self.tree_recs.heading("rank", text="Rank")
        self.tree_recs.heading("score", text="Score")
        self.tree_recs.heading("code", text="Family Code")
        self.tree_recs.heading("name", text="Family Name")
        self.tree_recs.heading("pilgrims", text="Devotees")
        self.tree_recs.heading("date", text="Preferred Date")
        self.tree_recs.heading("reasons", text="Prioritization Reasoning Tags")

        self.tree_recs.column("rank", width=45, anchor="center")
        self.tree_recs.column("score", width=55, anchor="center")
        self.tree_recs.column("code", width=105)
        self.tree_recs.column("name", width=145)
        self.tree_recs.column("pilgrims", width=65, anchor="center")
        self.tree_recs.column("date", width=95, anchor="center")
        self.tree_recs.column("reasons", width=260)
        self.tree_recs.pack(fill=tk.BOTH, expand=True)

    # ---------------------------------------------------------
    # Filtering & Refresh Logic
    # ---------------------------------------------------------
    def _on_filter_changed(self, event=None):
        val = self.filter_combo.get()
        if val == "Custom Range":
            self.custom_frame.pack(side=tk.LEFT, padx=(2, 4))
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

            # 2. Update All 9 KPI Cards
            self.cards["total_families"].config(text=str(summary["total_families"]))
            self.cards["total_pilgrims"].config(text=str(summary["total_pilgrims"]))
            self.cards["completed_bookings"].config(text=str(summary["completed_bookings"]))
            self.cards["pending_bookings"].config(text=str(summary["pending_bookings"]))
            self.cards["in_progress_bookings"].config(text=str(summary["in_progress_bookings"]))
            self.cards["unavailable_bookings"].config(text=str(summary["unavailable_bookings"]))
            self.cards["cancelled_bookings"].config(text=str(summary["cancelled_bookings"]))
            self.cards["payment_summary"].config(text=f"₹{pay['total_revenue_collected']:,.2f}")
            self.cards["completion_rate"].config(text=f"{summary['booking_completion_percentage']}%")

            # 3. Update Performance Tab & Chart
            self.lbl_turnaround.config(
                text=f"⚡ Average Turnaround: {perf['avg_turnaround_hours']}h ({perf['avg_turnaround_days']}d)  |  Processed vs Backlog: {perf['total_processed']} / {perf['total_backlog']}"
            )

            # Update Chart
            if self.chart_mode == "daily":
                self.perf_donut_chart.pack_forget()
                self.perf_bar_chart.pack(fill=tk.BOTH, expand=True)
                self.perf_bar_chart.set_data(
                    perf["daily_trends"],
                    label_key="activity_date",
                    val_key="booked",
                    secondary_key="pending",
                    title="Daily Bookings (Blue: Booked, Gold: Pending)",
                )
            elif self.chart_mode == "weekly":
                self.perf_donut_chart.pack_forget()
                self.perf_bar_chart.pack(fill=tk.BOTH, expand=True)
                self.perf_bar_chart.set_data(
                    perf["weekly_trends"],
                    label_key="activity_week",
                    val_key="booked",
                    secondary_key="pending",
                    title="Weekly Operational Performance (Blue: Booked, Gold: Pending)",
                )
            elif self.chart_mode == "monthly":
                self.perf_donut_chart.pack_forget()
                self.perf_bar_chart.pack(fill=tk.BOTH, expand=True)
                self.perf_bar_chart.set_data(
                    perf["monthly_trends"],
                    label_key="activity_month",
                    val_key="booked",
                    title="Monthly Completed Bookings",
                )
            elif self.chart_mode == "outcomes":
                self.perf_bar_chart.pack_forget()
                self.perf_donut_chart.pack(fill=tk.BOTH, expand=True)
                outcomes = perf.get("outcomes", {})
                slices = [
                    ("Booked", outcomes.get("Booked", 0), "#15803D"),
                    ("Pending", outcomes.get("Pending", 0), "#B45309"),
                    ("In Progress", outcomes.get("In progress", 0), "#0369A1"),
                    ("Unavailable", outcomes.get("Unavailable", 0), "#64748B"),
                    ("Cancelled", outcomes.get("Cancelled", 0), "#DC2626"),
                ]
                self.perf_donut_chart.set_data(slices, title="Booking Status Outcomes Breakdown", center_label="TOTAL")

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

            # In-progress table
            for item in self.tree_in_prog.get_children():
                self.tree_in_prog.delete(item)
            for inp in queue.get("in_progress_tracking", []):
                self.tree_in_prog.insert("", "end", values=(
                    inp.get("family_code"),
                    inp.get("family_name"),
                    inp.get("contact_name", "—"),
                    inp.get("phone", "—"),
                    inp.get("pilgrim_count", 0),
                    inp.get("preferred_date") or "—",
                    f"{inp.get('hours_in_progress', 0.0)} hrs",
                ))

            # Attention table
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

            # 5. Update Family Analytics Tab
            self.refresh_family_analytics()

            # 6. Update Payments Tab
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

            # 7. Update Documents Tab
            self.lbl_doc_summary.config(
                text=f"📁 Ticket Compliance: {doc['ticket_compliance_percentage']}% Attached ({doc['booked_with_tickets']} of {doc['booked_families_total']})  |  Incomplete Devotee Profiles: {doc['incomplete_document_families_count']}"
            )

            for item in self.tree_incomplete_docs.get_children():
                self.tree_incomplete_docs.delete(item)
            for inc in doc.get("incomplete_document_families", []):
                self.tree_incomplete_docs.insert("", "end", values=(
                    inc.get("family_code"),
                    inc.get("family_name"),
                    inc.get("phone", "—"),
                    inc.get("total_pilgrims", 0),
                    inc.get("missing_details", "Incomplete document details"),
                ))

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

            # 8. Update Operational Insights Tab
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

    def refresh_family_analytics(self):
        """Fetch and populate family records in the Family Analytics tab."""
        try:
            s_term = self.ent_fam_search.get().strip() if hasattr(self, "ent_fam_search") else ""
            st_filter = self.combo_fam_status.get() if hasattr(self, "combo_fam_status") else "All"
            tk_filter = self.combo_fam_ticket.get() if hasattr(self, "combo_fam_ticket") else "All"

            data = get_family_analytics(
                db_path=self.db_path,
                search_term=s_term,
                status_filter=st_filter,
                ticket_filter=tk_filter,
                limit=1000,
            )

            self.lbl_fam_count.config(text=f"Records Found: {data['total_found']}")

            # Devotee Distribution string
            dist_str = "Devotee Distribution: " + "  |  ".join(f"{k}: {v}" for k, v in data["pilgrim_distribution"].items())
            self.lbl_devotee_dist.config(text=dist_str)

            for item in self.tree_family.get_children():
                self.tree_family.delete(item)

            for r in data["family_records"]:
                self.tree_family.insert("", "end", values=(
                    r["family_code"],
                    r["family_name"],
                    r["contact_name"],
                    r["phone"],
                    r["pilgrim_count"],
                    f"₹{r['donation_amount']:,.2f}",
                    r["booking_type"],
                    r["preferred_date"] or "—",
                    r["status"],
                    r["payment_status"],
                    "Yes" if r.get("has_ticket") else "No",
                ))

        except Exception as e:
            logger.error(f"Error refreshing family analytics: {e}")

    # ---------------------------------------------------------
    # Dialogs & Export Handlers
    # ---------------------------------------------------------
    def _open_rule_config(self):
        AnalyticsRuleConfigDialog(self, self.db_path, on_saved=self.refresh_analytics)

    def _prompt_report_format(self, report_type: str):
        """Prompt admin to select export format (Excel, PDF, or CSV) for specified report."""
        dialog = tk.Toplevel(self)
        dialog.title(f"Export {report_type.capitalize()} Report")
        dialog.geometry("380x180")
        dialog.configure(bg="#F8FAFC")
        dialog.transient(self)
        dialog.grab_set()

        # Center
        dialog.update_idletasks()
        w, h = 380, 180
        x = (dialog.winfo_screenwidth() - w) // 2
        y = (dialog.winfo_screenheight() - h) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(
            dialog,
            text=f"Export {report_type.upper()} Report",
            font=("Segoe UI", 10, "bold"),
            fg="#1E3A8A",
            bg="#F8FAFC",
        ).pack(pady=(16, 4))
        tk.Label(
            dialog,
            text="Choose desired file export format:",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg="#F8FAFC",
        ).pack(pady=(0, 14))

        btn_box = tk.Frame(dialog, bg="#F8FAFC")
        btn_box.pack(pady=4)

        def pick(fmt):
            dialog.destroy()
            self._export_dispatcher(report_type, fmt)

        tk.Button(btn_box, text="📊 Excel (.xlsx)", font=("Segoe UI", 9, "bold"), bg="#15803D", fg="white", relief="flat", padx=10, pady=4, command=lambda: pick("xlsx")).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_box, text="📄 PDF (.pdf)", font=("Segoe UI", 9, "bold"), bg="#B91C1C", fg="white", relief="flat", padx=10, pady=4, command=lambda: pick("pdf")).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_box, text="📑 CSV (.csv)", font=("Segoe UI", 9, "bold"), bg="#0284C7", fg="white", relief="flat", padx=10, pady=4, command=lambda: pick("csv")).pack(side=tk.LEFT, padx=4)

    def _export_dispatcher(self, report_type: str, export_format: str):
        """Handle file selection and launch non-blocking background report export."""
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        ext = f".{export_format.lower()}"
        default_name = f"Srivani_{report_type.capitalize()}_Report_{now_str}{ext}"

        filetypes_map = {
            "xlsx": [("Excel Workbooks (*.xlsx)", "*.xlsx")],
            "pdf": [("PDF Documents (*.pdf)", "*.pdf")],
            "csv": [("CSV Documents (*.csv)", "*.csv")],
        }

        dest = filedialog.asksaveasfilename(
            parent=self,
            title=f"Save {report_type.capitalize()} Report ({export_format.upper()})",
            defaultextension=ext,
            filetypes=filetypes_map.get(export_format.lower(), [("All Files", "*.*")]),
            initialfile=default_name,
        )
        if not dest:
            return

        self._run_export_in_background(report_type, export_format, dest)

    def _run_export_in_background(self, report_type: str, export_format: str, dest_path: str):
        """Execute report generation in background thread to prevent UI freezing."""
        self.lbl_loading.config(text="⏳ Generating Report...")

        def worker():
            err = None
            out_file = None
            try:
                out_file = export_report(
                    report_type=report_type,
                    export_format=export_format,
                    dest_path=dest_path,
                    db_path=self.db_path,
                    filter_type=self.active_filter,
                    custom_start=self.custom_start,
                    custom_end=self.custom_end,
                )
            except Exception as e:
                err = e

            # Update UI on main thread
            self.after(0, lambda: self._on_export_complete(out_file, err, report_type, export_format))

        threading.Thread(target=worker, daemon=True).start()

    def _on_export_complete(self, out_file: Optional[Path], error: Optional[Exception], report_type: str, export_format: str):
        self.lbl_loading.config(text="")
        if error:
            messagebox.showerror("Export Error", f"Failed to generate {report_type} report: {error}", parent=self)
        else:
            ans = messagebox.askyesno(
                "Export Complete",
                f"Successfully generated {export_format.upper()} report:\n{out_file}\n\nOpen file now?",
                parent=self,
            )
            if ans and out_file and os.path.exists(out_file):
                try:
                    os.startfile(out_file)
                except Exception as ex:
                    logger.error(f"Error opening file: {ex}")
