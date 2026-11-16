"""
SRIVANI BOOKING MANAGER - Phase 10
Modern Data Import & Dataset Management GUI View

Features:
- File Selection (.csv, .xlsx, .xls) with file name & size display
- Real-time Dataset Preview (scrollable multi-column preview)
- Interactive Column Mapping with auto-detected aliases
- Strict Validation Engine with row & column error breakdown
- Downloadable Validation Error Report (.csv)
- 3-Way Duplicate Handling (Skip, Update, Cancel)
- Pre-Import Visual Summary & Confirmation
- Progress Bar and Transactional Database Execution
- Import History View with batch details & exportable reports
- Embedded Data Cleanup & Mock Purge Hub
"""

import os
import csv
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import DB_PATH
from database import (
    get_connection,
    get_import_batches,
    get_import_batch,
    get_cleanup_audits,
)
from dataset_importer import (
    read_dataset_file,
    detect_column_mapping,
    validate_and_analyze_dataset,
    execute_dataset_import,
    export_validation_report_csv,
    TARGET_FAMILY_FIELDS,
    TARGET_PILGRIM_FIELDS,
    ALL_TARGET_FIELDS,
    DUP_POLICY_SKIP,
    DUP_POLICY_UPDATE,
    DUP_POLICY_CANCEL,
)
from data_cleanup import (
    scan_for_mock_data,
    cleanup_mock_data,
    DataCleanupDialog,
)
from logger import get_logger

logger = get_logger("data_import_view")


class DataImportView(tk.Frame):
    """
    Main Data Import and Dataset Management View.
    Includes:
    1. Import Wizard (File -> Preview -> Mapping -> Validation -> Commit)
    2. Import History (Audit log of all batch imports)
    3. Mock Data Cleanup Hub (Safe purge with auto-backup)
    """

    def __init__(self, parent, app_controller, db_path: Optional[Path] = None):
        super().__init__(parent, bg="#F8FAFC")
        self.app = app_controller
        self.db_path = db_path or DB_PATH

        self.current_file_path: Optional[Path] = None
        self.raw_headers: List[str] = []
        self.raw_rows: List[Dict[str, Any]] = []
        self.file_size: int = 0
        self.file_format: str = ""
        self.mapping_combos: Dict[str, ttk.Combobox] = {}
        self.analysis_result: Optional[Dict[str, Any]] = None

        self._build_ui()

    def _build_ui(self):
        # 1. Header Banner
        header = tk.Frame(self, bg="#FFFFFF", padx=24, pady=16, bd=1, relief="solid")
        header.pack(fill="x", padx=16, pady=(16, 10))

        lbl_title = tk.Label(
            header,
            text="📥 DATASET IMPORT & DATA CLEANUP CENTER",
            font=("Segoe UI", 16, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            header,
            text="Universal CSV & Excel Ingestion • Dynamic Column Mapping • Transactional Safe Commit • Mock Data Purge",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # 2. Notebook Tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Tab 1: Dataset Import Wizard
        self.tab_import = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_import, text="  📥 Import Dataset  ")
        self._build_import_tab(self.tab_import)

        # Tab 2: Import History
        self.tab_history = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_history, text="  📜 Import History  ")
        self._build_history_tab(self.tab_history)

        # Tab 3: Mock Data Cleanup
        self.tab_cleanup = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_cleanup, text="  🧹 Mock Data Cleanup  ")
        self._build_cleanup_tab(self.tab_cleanup)

    # =========================================================================
    # TAB 1: DATASET IMPORT WIZARD
    # =========================================================================

    def _build_import_tab(self, parent):
        # Top File Chooser Bar
        top_box = tk.LabelFrame(parent, text=" 1. Select Dataset File ", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", padx=14, pady=10)
        top_box.pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(top_box, bg="#FFFFFF")
        row1.pack(fill="x")

        btn_select = tk.Button(
            row1,
            text="📂 Select CSV / Excel File",
            font=("Segoe UI", 9, "bold"),
            bg="#0D5C75",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.browse_file,
        )
        btn_select.pack(side="left", padx=(0, 14))

        self.lbl_file_info = tk.Label(
            row1,
            text="No file selected. Please choose a .csv or .xlsx dataset.",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        )
        self.lbl_file_info.pack(side="left")

        # Split pane: Left Column Mapping & Settings | Right Preview & Validation
        split_frame = tk.Frame(parent, bg="#F8FAFC")
        split_frame.pack(fill="both", expand=True)

        # Left Column: Column Mapping & Options
        left_pane = tk.Frame(split_frame, bg="#FFFFFF", bd=1, relief="solid", width=340)
        left_pane.pack(side="left", fill="y", padx=(0, 10))
        left_pane.pack_propagate(False)

        lbl_map_header = tk.Label(
            left_pane,
            text="2. Column Mapping",
            font=("Segoe UI", 10, "bold"),
            bg="#FFFFFF",
            fg="#0F172A",
        )
        lbl_map_header.pack(anchor="w", padx=12, pady=(10, 4))

        tk.Label(
            left_pane,
            text="Match file columns to application fields:",
            font=("Segoe UI", 8),
            bg="#FFFFFF",
            fg="#64748B",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Scrollable mapping container
        map_canvas_frame = tk.Frame(left_pane, bg="#FFFFFF")
        map_canvas_frame.pack(fill="both", expand=True, padx=8)

        self.canvas_map = tk.Canvas(map_canvas_frame, bg="#FFFFFF", highlightthickness=0)
        self.scrollbar_map = ttk.Scrollbar(map_canvas_frame, orient="vertical", command=self.canvas_map.yview)
        self.frame_mapping_inner = tk.Frame(self.canvas_map, bg="#FFFFFF")

        self.frame_mapping_inner.bind(
            "<Configure>",
            lambda e: self.canvas_map.configure(scrollregion=self.canvas_map.bbox("all")),
        )
        self.canvas_map.create_window((0, 0), window=self.frame_mapping_inner, anchor="nw")
        self.canvas_map.configure(yscrollcommand=self.scrollbar_map.set)

        self.canvas_map.pack(side="left", fill="both", expand=True)
        self.scrollbar_map.pack(side="right", fill="y")

        # Duplicate Handling Policy
        dup_box = tk.LabelFrame(left_pane, text=" Duplicate Policy ", font=("Segoe UI", 8, "bold"), bg="#FFFFFF", padx=8, pady=6)
        dup_box.pack(fill="x", padx=12, pady=10)

        self.dup_var = tk.StringVar(value=DUP_POLICY_SKIP)
        ttk.Radiobutton(dup_box, text="Skip existing records", variable=self.dup_var, value=DUP_POLICY_SKIP).pack(anchor="w")
        ttk.Radiobutton(dup_box, text="Update existing records", variable=self.dup_var, value=DUP_POLICY_UPDATE).pack(anchor="w")
        ttk.Radiobutton(dup_box, text="Cancel if duplicate found", variable=self.dup_var, value=DUP_POLICY_CANCEL).pack(anchor="w")

        btn_analyze = tk.Button(
            left_pane,
            text="🔍 Validate & Preview Import",
            font=("Segoe UI", 9, "bold"),
            bg="#F1F5F9",
            fg="#1E293B",
            relief="solid",
            bd=1,
            pady=6,
            cursor="hand2",
            command=self.validate_dataset,
        )
        btn_analyze.pack(fill="x", padx=12, pady=(0, 10))

        # Right Pane: Data Preview Table & Validation Summary
        right_pane = tk.Frame(split_frame, bg="#F8FAFC")
        right_pane.pack(side="right", fill="both", expand=True)

        # 3. Preview Table
        preview_box = tk.LabelFrame(right_pane, text=" 3. Dataset Preview (First 50 Rows) ", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", padx=10, pady=8)
        preview_box.pack(fill="both", expand=True, pady=(0, 8))

        self.tree_preview = ttk.Treeview(preview_box, show="headings", height=8)
        self.tree_scroll_y = ttk.Scrollbar(preview_box, orient="vertical", command=self.tree_preview.yview)
        self.tree_scroll_x = ttk.Scrollbar(preview_box, orient="horizontal", command=self.tree_preview.xview)
        self.tree_preview.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)

        self.tree_preview.pack(side="left", fill="both", expand=True)
        self.tree_scroll_y.pack(side="right", fill="y")
        self.tree_scroll_x.pack(side="bottom", fill="x")

        # 4. Validation Summary & Action Bar
        summary_box = tk.LabelFrame(right_pane, text=" 4. Validation Summary & Execution ", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", padx=14, pady=10)
        summary_box.pack(fill="x")

        self.lbl_summary_stats = tk.Label(
            summary_box,
            text="Dataset not validated yet. Select a file and click 'Validate & Preview Import'.",
            font=("Segoe UI", 9),
            fg="#475569",
            bg="#FFFFFF",
            justify="left",
        )
        self.lbl_summary_stats.pack(anchor="w", pady=(0, 8))

        # Action Buttons
        action_bar = tk.Frame(summary_box, bg="#FFFFFF")
        action_bar.pack(fill="x")

        self.btn_download_errors = ttk.Button(
            action_bar,
            text="📥 Download Error Report (CSV)",
            command=self.download_error_report,
            state="disabled",
        )
        self.btn_download_errors.pack(side="left", padx=(0, 10))

        self.btn_commit = tk.Button(
            action_bar,
            text="✅ Confirm & Commit Import to Database",
            font=("Segoe UI", 9, "bold"),
            bg="#15803D",
            fg="#FFFFFF",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            state="disabled",
            command=self.commit_import,
        )
        self.btn_commit.pack(side="right")

        btn_cancel = ttk.Button(action_bar, text="Reset", command=self.reset_wizard)
        btn_cancel.pack(side="right", padx=(0, 8))

    def browse_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Dataset File to Import",
            filetypes=[
                ("Supported Datasets", "*.csv;*.xlsx;*.xlsm;*.xls"),
                ("CSV Files (*.csv)", "*.csv"),
                ("Excel Workbooks (*.xlsx)", "*.xlsx"),
                ("All Files", "*.*"),
            ],
        )
        if not path:
            return

        self.load_file(Path(path))

    def load_file(self, p: Path):
        try:
            headers, rows, size, fmt = read_dataset_file(p)
            if not headers or not rows:
                messagebox.showerror("Empty File", "The selected file contains no headers or data rows.", parent=self)
                return

            self.current_file_path = p
            self.raw_headers = headers
            self.raw_rows = rows
            self.file_size = size
            self.file_format = fmt

            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.2f} MB"
            self.lbl_file_info.config(
                text=f"📄 {p.name} ({size_str}, {len(rows)} data rows, {fmt})",
                fg="#0F172A",
                font=("Segoe UI", 9, "bold"),
            )

            # Auto-detect column mapping
            mapping = detect_column_mapping(headers)
            self._render_mapping_ui(headers, mapping)
            self._render_preview_table(headers, rows[:50])

            # Auto run initial validation
            self.validate_dataset()

        except Exception as e:
            logger.error(f"Failed to read dataset file '{p}': {e}")
            messagebox.showerror("File Error", f"Unable to read dataset file:\n{e}", parent=self)

    def _render_mapping_ui(self, headers: List[str], initial_mapping: Dict[str, Optional[str]]):
        for widget in self.frame_mapping_inner.winfo_children():
            widget.destroy()
        self.mapping_combos.clear()

        # Available options for mapping dropdowns
        options = ["-- Skip / Ignore --"] + [f"{target} ({label})" for target, label, _ in ALL_TARGET_FIELDS]

        for idx, h in enumerate(headers):
            row_frame = tk.Frame(self.frame_mapping_inner, bg="#FFFFFF", pady=3)
            row_frame.pack(fill="x", padx=4)

            # Column header label
            lbl = tk.Label(
                row_frame,
                text=h[:18] + ("..." if len(h) > 18 else ""),
                font=("Segoe UI", 8, "bold"),
                fg="#1E293B",
                bg="#FFFFFF",
                width=16,
                anchor="w",
            )
            lbl.pack(side="left")

            cb = ttk.Combobox(row_frame, values=options, state="readonly", width=20, font=("Segoe UI", 8))
            cb.pack(side="right", fill="x", expand=True)

            # Match initial mapping
            matched_target = initial_mapping.get(h)
            if matched_target:
                for opt in options:
                    if opt.startswith(matched_target + " "):
                        cb.set(opt)
                        break
            else:
                cb.set("-- Skip / Ignore --")

            self.mapping_combos[h] = cb

    def _render_preview_table(self, headers: List[str], sample_rows: List[Dict[str, Any]]):
        for item in self.tree_preview.get_children():
            self.tree_preview.delete(item)

        cols = ["_row_num"] + headers
        self.tree_preview["columns"] = cols
        self.tree_preview.heading("_row_num", text="Row #")
        self.tree_preview.column("_row_num", width=50, anchor="center")

        for h in headers:
            self.tree_preview.heading(h, text=h)
            self.tree_preview.column(h, width=120)

        for r in sample_rows:
            vals = [r.get("_row_num", "")] + [str(r.get(h, "")) for h in headers]
            self.tree_preview.insert("", "end", values=vals)

    def get_current_mapping(self) -> Dict[str, Optional[str]]:
        mapping = {}
        for h, cb in self.mapping_combos.items():
            sel = cb.get()
            if not sel or sel.startswith("--"):
                mapping[h] = None
            else:
                target = sel.split(" ")[0]
                mapping[h] = target
        return mapping

    def validate_dataset(self):
        if not self.raw_rows:
            messagebox.showinfo("No Data", "Please select a dataset file first.", parent=self)
            return

        mapping = self.get_current_mapping()
        policy = self.dup_var.get()

        try:
            analysis = validate_and_analyze_dataset(
                headers=self.raw_headers,
                raw_rows=self.raw_rows,
                column_mapping=mapping,
                dup_policy=policy,
                db_path=self.db_path,
            )
            self.analysis_result = analysis

            tot = analysis["total_rows"]
            valid = analysis["valid_rows_count"]
            invalid = analysis["invalid_rows_count"]
            new_f = analysis["new_families_count"]
            new_p = analysis["new_pilgrims_count"]
            upd_f = analysis["updated_families_count"]
            upd_p = analysis["updated_pilgrims_count"]
            skip = analysis["skipped_records_count"]
            dup = analysis["duplicate_records_count"]

            stat_text = (
                f"📊 Total Rows: {tot}  |  ✅ Valid: {valid}  |  ⚠️ Invalid: {invalid}\n"
                f"👥 New Families: {new_f}  |  👤 New Pilgrims: {new_p}  |  🔄 Updates: {upd_f + upd_p}  |  ⏩ Skipped: {skip}"
            )
            self.lbl_summary_stats.config(text=stat_text, fg="#0F172A" if invalid == 0 else "#B45309")

            if invalid > 0:
                self.btn_download_errors.config(state="normal")
            else:
                self.btn_download_errors.config(state="disabled")

            if valid > 0:
                self.btn_commit.config(state="normal", bg="#15803D")
            else:
                self.btn_commit.config(state="disabled", bg="#94A3B8")

        except Exception as e:
            logger.error(f"Validation error: {e}")
            messagebox.showerror("Validation Error", str(e), parent=self)
            self.lbl_summary_stats.config(text=f"❌ Error: {e}", fg="#DC2626")
            self.btn_commit.config(state="disabled", bg="#94A3B8")

    def download_error_report(self):
        if not self.analysis_result or not self.analysis_result.get("validation_errors"):
            messagebox.showinfo("No Errors", "No validation errors found to export.", parent=self)
            return

        out_path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Validation Error Report",
            defaultextension=".csv",
            filetypes=[("CSV File (*.csv)", "*.csv")],
            initialfile=f"validation_errors_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv",
        )
        if not out_path:
            return

        export_validation_report_csv(self.analysis_result["validation_errors"], out_path)
        messagebox.showinfo("Report Saved", f"Validation error report saved to:\n{out_path}", parent=self)

    def commit_import(self):
        if not self.analysis_result:
            return

        valid_count = self.analysis_result.get("valid_rows_count", 0)
        invalid_count = self.analysis_result.get("invalid_rows_count", 0)

        msg = (
            f"Are you sure you want to commit this dataset to the database?\n\n"
            f"• Valid Records to Import: {valid_count}\n"
            f"• Rejected Invalid Rows: {invalid_count}\n"
            f"• Duplicate Policy: {self.dup_var.get()}\n\n"
            f"All operations will be committed atomically with foreign key integrity."
        )

        confirm = messagebox.askyesno("Confirm Dataset Import", msg, parent=self)
        if not confirm:
            return

        try:
            mapping = self.get_current_mapping()
            res = execute_dataset_import(
                analysis=self.analysis_result,
                file_name=self.current_file_path.name if self.current_file_path else "dataset.csv",
                file_size=self.file_size,
                file_format=self.file_format,
                column_mapping=mapping,
                admin_user="admin",
                db_path=self.db_path,
            )

            messagebox.showinfo("Import Completed", res["message"], parent=self)
            self.reset_wizard()
            self.refresh_history()

            # Refresh global app views
            if hasattr(self.app, "refresh"):
                self.app.refresh()

        except Exception as e:
            logger.error(f"Import execution error: {e}")
            messagebox.showerror("Import Failed", f"A database error occurred during import:\n{e}", parent=self)

    def reset_wizard(self):
        self.current_file_path = None
        self.raw_headers = []
        self.raw_rows = []
        self.analysis_result = None
        self.lbl_file_info.config(text="No file selected. Please choose a .csv or .xlsx dataset.", fg="#64748B", font=("Segoe UI", 9))
        self.lbl_summary_stats.config(text="Dataset not validated yet.", fg="#475569")
        self.btn_commit.config(state="disabled", bg="#94A3B8")
        self.btn_download_errors.config(state="disabled")

        for item in self.tree_preview.get_children():
            self.tree_preview.delete(item)
        for widget in self.frame_mapping_inner.winfo_children():
            widget.destroy()

    # =========================================================================
    # TAB 2: IMPORT HISTORY
    # =========================================================================

    def _build_history_tab(self, parent):
        top_bar = tk.Frame(parent, bg="#FFFFFF", padx=12, pady=10, bd=1, relief="solid")
        top_bar.pack(fill="x", pady=(0, 10))

        tk.Label(top_bar, text="📜 Import Batch History & Audit Logs", font=("Segoe UI", 11, "bold"), bg="#FFFFFF", fg="#0F172A").pack(side="left")

        btn_ref = ttk.Button(top_bar, text="🔄 Refresh History", command=self.refresh_history)
        btn_ref.pack(side="right")

        # History Table
        tbl_frame = ttk.Frame(parent)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("id", "batch", "file", "format", "rows", "success", "updated", "skipped", "failed", "status", "date")
        self.tree_hist = ttk.Treeview(tbl_frame, columns=cols, show="headings", height=12)
        self.tree_hist.heading("id", text="#")
        self.tree_hist.heading("batch", text="Batch ID")
        self.tree_hist.heading("file", text="File Name")
        self.tree_hist.heading("format", text="Format")
        self.tree_hist.heading("rows", text="Total Rows")
        self.tree_hist.heading("success", text="Succeeded")
        self.tree_hist.heading("updated", text="Updated")
        self.tree_hist.heading("skipped", text="Skipped")
        self.tree_hist.heading("failed", text="Failed")
        self.tree_hist.heading("status", text="Status")
        self.tree_hist.heading("date", text="Imported At")

        self.tree_hist.column("id", width=35, anchor="center")
        self.tree_hist.column("batch", width=140)
        self.tree_hist.column("file", width=160)
        self.tree_hist.column("format", width=80, anchor="center")
        self.tree_hist.column("rows", width=70, anchor="center")
        self.tree_hist.column("success", width=75, anchor="center")
        self.tree_hist.column("updated", width=65, anchor="center")
        self.tree_hist.column("skipped", width=65, anchor="center")
        self.tree_hist.column("failed", width=65, anchor="center")
        self.tree_hist.column("status", width=90, anchor="center")
        self.tree_hist.column("date", width=130)

        hist_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree_hist.yview)
        self.tree_hist.configure(yscrollcommand=hist_scroll.set)
        self.tree_hist.pack(side="left", fill="both", expand=True)
        hist_scroll.pack(side="right", fill="y")

        # Action Buttons
        bot_bar = ttk.Frame(parent)
        bot_bar.pack(fill="x")

        ttk.Button(bot_bar, text="👁️ View Selected Batch Details", command=self._view_batch_details).pack(side="left", padx=(0, 8))

    def refresh_history(self):
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)

        batches = get_import_batches(limit=100, db_path=self.db_path)
        for b in batches:
            self.tree_hist.insert(
                "",
                "end",
                values=(
                    b["id"],
                    b["batch_id"],
                    b["file_name"],
                    b.get("file_format", "CSV"),
                    b["total_rows"],
                    b["successful_records"],
                    b.get("updated_records", 0),
                    b.get("skipped_records", 0),
                    b.get("failed_records", 0),
                    b["status"],
                    b["created_at"],
                ),
            )

    def _view_batch_details(self):
        sel = self.tree_hist.selection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select an import batch to view details.", parent=self)
            return

        item = self.tree_hist.item(sel[0])
        batch_id = item["values"][1]
        batch = get_import_batch(batch_id, db_path=self.db_path)
        if not batch:
            return

        detail_win = tk.Toplevel(self)
        detail_win.title(f"Batch Details — {batch_id}")
        detail_win.geometry("540x440")
        detail_win.configure(bg="#FFFFFF")
        detail_win.transient(self)

        container = ttk.Frame(detail_win, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text=f"Batch: {batch_id}", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))

        info_rows = [
            ("Original File:", f"{batch['file_name']} ({batch.get('file_format', 'N/A')})"),
            ("File Size:", f"{batch['file_size']} bytes"),
            ("Executed By:", batch.get("admin_user", "admin")),
            ("Import Timestamp:", batch["created_at"]),
            ("Total Rows:", str(batch["total_rows"])),
            ("Succeeded:", str(batch["successful_records"])),
            ("Updated:", str(batch.get("updated_records", 0))),
            ("Skipped:", str(batch.get("skipped_records", 0))),
            ("Failed / Rejected:", str(batch.get("failed_records", 0))),
            ("Overall Status:", batch["status"]),
            ("Summary:", batch.get("error_summary", "")),
        ]

        grid = ttk.Frame(container)
        grid.pack(fill="x", pady=10)

        for idx, (k, v) in enumerate(info_rows):
            ttk.Label(grid, text=k, font=("Segoe UI", 9, "bold")).grid(row=idx, column=0, sticky="w", pady=3)
            ttk.Label(grid, text=v, font=("Segoe UI", 9)).grid(row=idx, column=1, sticky="w", padx=10, pady=3)

        ttk.Button(container, text="Close", command=detail_win.destroy).pack(anchor="e", pady=(14, 0))

    # =========================================================================
    # TAB 3: MOCK DATA CLEANUP HUB
    # =========================================================================

    def _build_cleanup_tab(self, parent):
        top_box = tk.Frame(parent, bg="#FFFFFF", padx=16, pady=12, bd=1, relief="solid")
        top_box.pack(fill="x", pady=(0, 12))

        tk.Label(
            top_box,
            text="🧹 Production Database Mock & Demo Data Cleanup",
            font=("Segoe UI", 11, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        ).pack(anchor="w")

        tk.Label(
            top_box,
            text="Removes artificial development test fixtures and sample data while strictly preserving real records.",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        ).pack(anchor="w", pady=(2, 0))

        # Launch Cleanup Modal Button
        action_frame = tk.Frame(parent, bg="#F8FAFC", pady=8)
        action_frame.pack(fill="x", pady=(0, 12))

        btn_open_cleanup = tk.Button(
            action_frame,
            text="🔍 Launch Mock Data Scanner & Purge Tool",
            font=("Segoe UI", 10, "bold"),
            bg="#DC2626",
            fg="#FFFFFF",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self.open_cleanup_modal,
        )
        btn_open_cleanup.pack(side="left")

        # Cleanup Audit Log Table
        aud_box = ttk.LabelFrame(parent, text=" Cleanup Operation Audit Logs ", padding=10)
        aud_box.pack(fill="both", expand=True)

        cols = ("id", "cid", "admin", "fams", "pils", "backup", "date")
        self.tree_audits = ttk.Treeview(aud_box, columns=cols, show="headings", height=8)
        self.tree_audits.heading("id", text="#")
        self.tree_audits.heading("cid", text="Cleanup ID")
        self.tree_audits.heading("admin", text="Admin")
        self.tree_audits.heading("fams", text="Families Purged")
        self.tree_audits.heading("pils", text="Pilgrims Purged")
        self.tree_audits.heading("backup", text="Pre-Cleanup Backup Path")
        self.tree_audits.heading("date", text="Timestamp")

        self.tree_audits.column("id", width=35, anchor="center")
        self.tree_audits.column("cid", width=170)
        self.tree_audits.column("admin", width=80, anchor="center")
        self.tree_audits.column("fams", width=100, anchor="center")
        self.tree_audits.column("pils", width=100, anchor="center")
        self.tree_audits.column("backup", width=220)
        self.tree_audits.column("date", width=130)

        a_scroll = ttk.Scrollbar(aud_box, orient="vertical", command=self.tree_audits.yview)
        self.tree_audits.configure(yscrollcommand=a_scroll.set)
        self.tree_audits.pack(side="left", fill="both", expand=True)
        a_scroll.pack(side="right", fill="y")

        self.refresh_cleanup_audits()

    def open_cleanup_modal(self):
        DataCleanupDialog(
            parent=self.winfo_toplevel(),
            app_controller=self.app,
            db_path=self.db_path,
            on_complete=self.refresh_cleanup_audits,
        )

    def refresh_cleanup_audits(self):
        for item in self.tree_audits.get_children():
            self.tree_audits.delete(item)

        auds = get_cleanup_audits(limit=50, db_path=self.db_path)
        for a in auds:
            self.tree_audits.insert(
                "",
                "end",
                values=(
                    a["id"],
                    a["cleanup_id"],
                    a["admin_user"],
                    a["deleted_families_count"],
                    a["deleted_pilgrims_count"],
                    a["backup_path"],
                    a["created_at"],
                ),
            )
