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
from backup_manager import create_database_backup
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

    def _render_preview_table(self, headers: List[str], sample_rows: List[Dict[str, Any]], mapping: Optional[Dict[str, Optional[str]]] = None):
        for item in self.tree_preview.get_children():
            self.tree_preview.delete(item)

        mapping = mapping or self.get_current_mapping()
        target_to_hdr: Dict[str, str] = {}
        for h, t in mapping.items():
            if t and t not in target_to_hdr:
                target_to_hdr[t] = h

        core_cols = [
            ("_row_num", "Row #", 55, "center"),
            ("fam_id", "Family ID", 110, "center"),
            ("fam_name", "Family Name", 140, "w"),
            ("pilgrim_name", "Pilgrim Name", 140, "w"),
            ("age", "Age", 55, "center"),
            ("gender", "Gender", 65, "center"),
            ("mobile", "Mobile Number", 110, "center"),
        ]

        mapped_hdrs = set(target_to_hdr.values())
        other_hdrs = [h for h in headers if h not in mapped_hdrs]

        all_col_ids = [c[0] for c in core_cols] + [f"other_{i}" for i in range(len(other_hdrs))]
        self.tree_preview["columns"] = all_col_ids

        for cid, title, w, align in core_cols:
            self.tree_preview.heading(cid, text=title)
            self.tree_preview.column(cid, width=w, anchor=align)

        for i, h in enumerate(other_hdrs):
            cid = f"other_{i}"
            self.tree_preview.heading(cid, text=h)
            self.tree_preview.column(cid, width=120, anchor="w")

        f_id_hdr = target_to_hdr.get("family_code")
        f_name_hdr = target_to_hdr.get("family_name")
        p_name_hdr = target_to_hdr.get("full_name")
        age_hdr = target_to_hdr.get("age")
        gender_hdr = target_to_hdr.get("gender")
        phone_hdr = target_to_hdr.get("phone")

        for idx, r in enumerate(sample_rows):
            row_num = r.get("_row_num", idx + 1)
            fam_id = str(r.get(f_id_hdr, "")) if f_id_hdr else ""
            fam_name = str(r.get(f_name_hdr, "")) if f_name_hdr else ""
            p_name = str(r.get(p_name_hdr, "")) if p_name_hdr else ""
            age = str(r.get(age_hdr, "")) if age_hdr else ""
            gender = str(r.get(gender_hdr, "")) if gender_hdr else ""
            mobile = str(r.get(phone_hdr, "")) if phone_hdr else ""

            if not fam_name and p_name:
                fam_name = f"{p_name} Family"

            vals = [row_num, fam_id, fam_name, p_name, age, gender, mobile] + [str(r.get(h, "")) for h in other_hdrs]
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


# =============================================================================
# DEDICATED DATASET IMPORT MODAL DIALOG (Phase 10 / Dashboard Feature)
# =============================================================================

class DatasetImportDialog(tk.Toplevel):
    """
    Dedicated Modern Dataset Import Dialog for the SRIVANI Dashboard.

    Requirements:
    1. Upload CSV button (.csv)
    2. Upload Excel button (.xlsx)
    3. Drag and drop file area (visual drop zone with click-to-browse & windnd support)
    4. Supported formats indicator (.csv and .xlsx)
    5. Selected filename and file size display
    6. Preview Dataset button and Cancel button
    7. Data Preview table with Row #, Family ID, Family name, Pilgrim name, Age, Gender, Mobile number,
       plus other detected columns, with horizontal & vertical scrolling
    8. Column mapping: Map uploaded columns to database fields, detect unmatched columns,
       and prompt confirmation for ambiguous mappings
    9. Validation engine: Missing required values, invalid phone, invalid age, duplicates,
       missing family references, invalid data formats, displaying row-specific errors and error report export
    10. Import options: Skip duplicate records, Update existing records after confirmation, Cancel import
        (with existing family ID reuse for multiple pilgrims)
    11. Import summary before committing with admin confirmation
    12. Database integration: Atomic transaction with rollback, batch ID, pre-import backup, no mock data
    13. Automatic dashboard refresh of all 6 statistics
    14. 100% offline local compliance
    """

    def __init__(
        self,
        parent,
        on_success_callback=None,
        file_path: Optional[str | Path] = None,
        db_path: Optional[Path] = None,
    ):
        super().__init__(parent)
        self.app = parent
        self.on_success = on_success_callback
        self.db_path = db_path or DB_PATH

        self.current_file_path: Optional[Path] = None
        self.raw_headers: List[str] = []
        self.raw_rows: List[Dict[str, Any]] = []
        self.file_size: int = 0
        self.file_format: str = ""
        self.mapping_combos: Dict[str, ttk.Combobox] = {}
        self.mapping_badges: Dict[str, tk.Label] = {}
        self.analysis_result: Optional[Dict[str, Any]] = None

        self.title("📥 Import Dataset — SRIVANI Booking Manager")
        self.geometry("1060x740")
        self.minsize(920, 600)

        # Center on parent or screen
        try:
            self.update_idletasks()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            w = 1060
            h = 740
            x = max(0, px + (pw - w) // 2)
            y = max(0, py + (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        self.transient(parent)
        self.grab_set()

        self._build_ui()

        if file_path:
            self.load_file(Path(file_path))

    def _build_ui(self):
        # Main background container
        self.configure(bg="#F1F5F9")
        main_box = tk.Frame(self, bg="#F1F5F9", padx=16, pady=12)
        main_box.pack(fill="both", expand=True)

        # ---------------------------------------------------------------------
        # 1. Top Header Banner
        # ---------------------------------------------------------------------
        header_frame = tk.Frame(main_box, bg="#FFFFFF", padx=18, pady=12, bd=1, relief="solid")
        header_frame.pack(fill="x", pady=(0, 10))

        h_left = tk.Frame(header_frame, bg="#FFFFFF")
        h_left.pack(side="left")

        lbl_title = tk.Label(
            h_left,
            text="📥 IMPORT DATASET — DEVOTEE INGESTION WIZARD",
            font=("Segoe UI", 14, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            h_left,
            text="Upload CSV or Excel spreadsheets, preview data, map columns, validate records, and commit to local database.",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        btn_close_top = tk.Button(
            header_frame,
            text="✖",
            font=("Segoe UI", 11, "bold"),
            bg="#FFFFFF",
            fg="#64748B",
            activebackground="#FEE2E2",
            activeforeground="#DC2626",
            bd=0,
            cursor="hand2",
            command=self.destroy,
        )
        btn_close_top.pack(side="right")

        # ---------------------------------------------------------------------
        # 2. File Selection & Drop Zone Card
        # ---------------------------------------------------------------------
        file_box = tk.LabelFrame(
            main_box,
            text=" 1. File Selection & Drop Zone ",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            padx=14,
            pady=8,
        )
        file_box.pack(fill="x", pady=(0, 10))

        # Top Button Bar
        btn_row = tk.Frame(file_box, bg="#FFFFFF")
        btn_row.pack(fill="x", pady=(0, 8))

        btn_csv = tk.Button(
            btn_row,
            text="📂 Upload CSV (.csv)",
            font=("Segoe UI", 9, "bold"),
            bg="#0D5C75",
            fg="#FFFFFF",
            activebackground="#0A4B5F",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.browse_csv,
        )
        btn_csv.pack(side="left", padx=(0, 8))

        btn_excel = tk.Button(
            btn_row,
            text="📊 Upload Excel (.xlsx)",
            font=("Segoe UI", 9, "bold"),
            bg="#0F766E",
            fg="#FFFFFF",
            activebackground="#115E59",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=14,
            pady=5,
            cursor="hand2",
            command=self.browse_excel,
        )
        btn_excel.pack(side="left", padx=(0, 8))

        btn_preview = tk.Button(
            btn_row,
            text="👁️ Preview Dataset",
            font=("Segoe UI", 9),
            bg="#1E293B",
            fg="#FFFFFF",
            activebackground="#334155",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.preview_dataset_clicked,
        )
        btn_preview.pack(side="left", padx=(0, 8))

        btn_cancel_file = tk.Button(
            btn_row,
            text="❌ Cancel",
            font=("Segoe UI", 9),
            bg="#F1F5F9",
            fg="#475569",
            activebackground="#E2E8F0",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.destroy,
        )
        btn_cancel_file.pack(side="right")

        # Visual Drag & Drop Area / Drop Zone
        self.drop_zone = tk.Frame(
            file_box,
            bg="#F8FAFC",
            highlightbackground="#94A3B8",
            highlightthickness=2,
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
        )
        self.drop_zone.pack(fill="x", pady=(0, 8))

        lbl_drop_main = tk.Label(
            self.drop_zone,
            text="📥 Drag & Drop your .csv or .xlsx file here, or click to browse",
            font=("Segoe UI", 10, "bold"),
            fg="#1E293B",
            bg="#F8FAFC",
            cursor="hand2",
        )
        lbl_drop_main.pack(anchor="center")

        lbl_drop_sub = tk.Label(
            self.drop_zone,
            text="Supported formats: .csv and .xlsx (Excel Workbooks) • Up to 50MB per file",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg="#F8FAFC",
            cursor="hand2",
        )
        lbl_drop_sub.pack(anchor="center", pady=(2, 0))

        # Click on drop zone opens file chooser
        self.drop_zone.bind("<Button-1>", self.browse_all)
        lbl_drop_main.bind("<Button-1>", self.browse_all)
        lbl_drop_sub.bind("<Button-1>", self.browse_all)

        # Hook windnd if present in environment
        try:
            import windnd
            windnd.hook_dropfiles(self.drop_zone, func=self._on_windnd_drop)
        except Exception:
            pass

        # Selected File Metadata Bar
        info_row = tk.Frame(file_box, bg="#FFFFFF")
        info_row.pack(fill="x")

        self.lbl_selected_file = tk.Label(
            info_row,
            text="Selected File: None",
            font=("Segoe UI", 9, "bold"),
            fg="#64748B",
            bg="#FFFFFF",
        )
        self.lbl_selected_file.pack(side="left", padx=(0, 16))

        self.lbl_file_size = tk.Label(
            info_row,
            text="File Size: —",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        )
        self.lbl_file_size.pack(side="left", padx=(0, 16))

        self.lbl_file_format = tk.Label(
            info_row,
            text="Format: —",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        )
        self.lbl_file_format.pack(side="left")

        # ---------------------------------------------------------------------
        # 3. Main Workspace Notebook (Preview, Mapping, Validation, Summary)
        # ---------------------------------------------------------------------
        self.notebook = ttk.Notebook(main_box)
        self.notebook.pack(fill="both", expand=True, pady=(0, 8))

        # Tab 1: Preview & Column Mapping
        self.tab_preview_map = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_preview_map, text="  👁️ Data Preview & Column Mapping  ")
        self._build_preview_map_tab(self.tab_preview_map)

        # Tab 2: Validation & Row Errors
        self.tab_validation = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_validation, text="  🔍 Validation & Row-Specific Errors  ")
        self._build_validation_tab(self.tab_validation)

        # Tab 3: Summary & Options
        self.tab_summary = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_summary, text="  📋 Import Summary & Options  ")
        self._build_summary_tab(self.tab_summary)

        # ---------------------------------------------------------------------
        # 4. Sticky Bottom Action Footer
        # ---------------------------------------------------------------------
        footer_frame = tk.Frame(main_box, bg="#FFFFFF", padx=14, pady=10, bd=1, relief="solid")
        footer_frame.pack(fill="x")

        self.lbl_bottom_summary = tk.Label(
            footer_frame,
            text="Please select a .csv or .xlsx file to preview and validate records.",
            font=("Segoe UI", 9, "bold"),
            fg="#1E293B",
            bg="#FFFFFF",
        )
        self.lbl_bottom_summary.pack(side="left")

        btn_box = tk.Frame(footer_frame, bg="#FFFFFF")
        btn_box.pack(side="right")

        ttk.Button(btn_box, text="Cancel", command=self.destroy).pack(side="left", padx=(0, 8))

        self.btn_validate_bottom = ttk.Button(
            btn_box,
            text="🔍 Re-Validate",
            command=self.validate_dataset,
        )
        self.btn_validate_bottom.pack(side="left", padx=(0, 8))

        self.btn_commit = tk.Button(
            btn_box,
            text="🚀 Import Dataset",
            font=("Segoe UI", 9, "bold"),
            bg="#15803D",
            fg="#FFFFFF",
            activebackground="#166534",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=16,
            pady=5,
            cursor="hand2",
            state="disabled",
            command=self.commit_import,
        )
        self.btn_commit.pack(side="left")

    # -------------------------------------------------------------------------
    # TAB 1: PREVIEW & COLUMN MAPPING BUILDER
    # -------------------------------------------------------------------------
    def _build_preview_map_tab(self, parent):
        # Split into upper Mapping area and lower Preview table
        # 1. Upper Mapping Container
        map_outer = tk.LabelFrame(
            parent,
            text=" 2. Column Mapping (Map dataset columns to database fields) ",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            padx=10,
            pady=6,
        )
        map_outer.pack(fill="x", pady=(0, 8))

        tk.Label(
            map_outer,
            text="Columns auto-detected based on aliases. Unmatched columns are highlighted below:",
            font=("Segoe UI", 8),
            fg="#64748B",
            bg="#FFFFFF",
        ).pack(anchor="w", pady=(0, 4))

        # Scrollable mapping container
        map_canvas_frame = tk.Frame(map_outer, bg="#FFFFFF", height=130)
        map_canvas_frame.pack(fill="x", expand=False)

        self.canvas_map = tk.Canvas(map_canvas_frame, bg="#FFFFFF", highlightthickness=0, height=130)
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

        # 2. Lower Preview Table Container
        preview_outer = tk.LabelFrame(
            parent,
            text=" 3. Data Preview (First 50 Rows) ",
            font=("Segoe UI", 9, "bold"),
            bg="#FFFFFF",
            padx=10,
            pady=6,
        )
        preview_outer.pack(fill="both", expand=True)

        tbl_box = ttk.Frame(preview_outer)
        tbl_box.pack(fill="both", expand=True)

        self.tree_preview = ttk.Treeview(tbl_box, show="headings", height=9)
        self.tree_scroll_y = ttk.Scrollbar(tbl_box, orient="vertical", command=self.tree_preview.yview)
        self.tree_scroll_x = ttk.Scrollbar(tbl_box, orient="horizontal", command=self.tree_preview.xview)
        self.tree_preview.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)

        self.tree_preview.grid(row=0, column=0, sticky="nsew")
        self.tree_scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree_scroll_x.grid(row=1, column=0, sticky="ew")

        tbl_box.rowconfigure(0, weight=1)
        tbl_box.columnconfigure(0, weight=1)

    # -------------------------------------------------------------------------
    # TAB 2: VALIDATION & ROW-SPECIFIC ERRORS BUILDER
    # -------------------------------------------------------------------------
    def _build_validation_tab(self, parent):
        top_val = tk.Frame(parent, bg="#FFFFFF", padx=10, pady=8, bd=1, relief="solid")
        top_val.pack(fill="x", pady=(0, 8))

        self.lbl_val_status = tk.Label(
            top_val,
            text="No dataset validated yet. Please upload a file.",
            font=("Segoe UI", 9, "bold"),
            fg="#475569",
            bg="#FFFFFF",
        )
        self.lbl_val_status.pack(side="left")

        self.btn_export_errors = ttk.Button(
            top_val,
            text="📥 Export Error Report (.csv)",
            command=self.download_error_report,
            state="disabled",
        )
        self.btn_export_errors.pack(side="right")

        # Row-specific error table
        err_box = ttk.Frame(parent)
        err_box.pack(fill="both", expand=True)

        err_cols = ("row", "column", "value", "error", "severity")
        self.tree_errors = ttk.Treeview(err_box, columns=err_cols, show="headings", height=12)
        self.tree_errors.heading("row", text="Row #")
        self.tree_errors.heading("column", text="Field / Column")
        self.tree_errors.heading("value", text="Problematic Value")
        self.tree_errors.heading("error", text="Error Description")
        self.tree_errors.heading("severity", text="Severity")

        self.tree_errors.column("row", width=60, anchor="center")
        self.tree_errors.column("column", width=140)
        self.tree_errors.column("value", width=140)
        self.tree_errors.column("error", width=380)
        self.tree_errors.column("severity", width=90, anchor="center")

        err_sy = ttk.Scrollbar(err_box, orient="vertical", command=self.tree_errors.yview)
        err_sx = ttk.Scrollbar(err_box, orient="horizontal", command=self.tree_errors.xview)
        self.tree_errors.configure(yscrollcommand=err_sy.set, xscrollcommand=err_sx.set)

        self.tree_errors.grid(row=0, column=0, sticky="nsew")
        err_sy.grid(row=0, column=1, sticky="ns")
        err_sx.grid(row=1, column=0, sticky="ew")

        err_box.rowconfigure(0, weight=1)
        err_box.columnconfigure(0, weight=1)

    # -------------------------------------------------------------------------
    # TAB 3: IMPORT SUMMARY & DUPLICATE OPTIONS BUILDER
    # -------------------------------------------------------------------------
    def _build_summary_tab(self, parent):
        # Summary Counters Box
        sum_box = tk.LabelFrame(parent, text=" Pre-Commit Import Summary ", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", padx=16, pady=12)
        sum_box.pack(fill="x", pady=(0, 10))

        self.badge_sum_labels = {}
        metric_items = [
            ("tot", "Total Rows in File", "0", "#1B365D"),
            ("valid", "Valid Records", "0", "#15803D"),
            ("invalid", "Invalid Records", "0", "#DC2626"),
            ("new_f", "New Families", "0", "#0284C7"),
            ("new_p", "New Pilgrims", "0", "#4338CA"),
            ("dup", "Duplicate Records", "0", "#D97706"),
            ("skip", "Records to Skip", "0", "#64748B"),
        ]

        card_row = tk.Frame(sum_box, bg="#FFFFFF")
        card_row.pack(fill="x", pady=(0, 8))

        for idx, (key, title, d_val, color) in enumerate(metric_items):
            c_frame = tk.Frame(card_row, bg="#F8FAFC", highlightbackground="#CBD5E1", highlightthickness=1, padx=8, pady=6)
            c_frame.pack(side="left", expand=True, fill="x", padx=(0 if idx == 0 else 4, 0))
            tk.Label(c_frame, text=title, font=("Segoe UI", 7, "bold"), fg="#64748B", bg="#F8FAFC").pack(anchor="w")
            lbl_v = tk.Label(c_frame, text=d_val, font=("Segoe UI", 13, "bold"), fg=color, bg="#F8FAFC")
            lbl_v.pack(anchor="w")
            self.badge_sum_labels[key] = lbl_v

        # Duplicate Handling Policy Box
        dup_frame = tk.LabelFrame(parent, text=" Duplicate Record Handling Policy ", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", padx=16, pady=12)
        dup_frame.pack(fill="x", pady=(0, 10))

        self.dup_var = tk.StringVar(value=DUP_POLICY_SKIP)

        ttk.Radiobutton(
            dup_frame,
            text="🔘 Skip duplicate records (Preserve existing database records; attach new pilgrims to existing families)",
            variable=self.dup_var,
            value=DUP_POLICY_SKIP,
            command=self.validate_dataset,
        ).pack(anchor="w", pady=3)

        ttk.Radiobutton(
            dup_frame,
            text="🔄 Update existing records (Update contact, address, or devotee information after confirmation)",
            variable=self.dup_var,
            value=DUP_POLICY_UPDATE,
            command=self.validate_dataset,
        ).pack(anchor="w", pady=3)

        ttk.Radiobutton(
            dup_frame,
            text="⛔ Cancel import if duplicate found (Strict zero-tolerance policy; aborts import)",
            variable=self.dup_var,
            value=DUP_POLICY_CANCEL,
            command=self.validate_dataset,
        ).pack(anchor="w", pady=3)

        # Pre-import Database Backup Notice
        backup_box = tk.Frame(parent, bg="#EFF6FF", highlightbackground="#93C5FD", highlightthickness=1, padx=14, pady=10)
        backup_box.pack(fill="x")

        tk.Label(
            backup_box,
            text="🛡️ Automatic Pre-Import Backup Protection",
            font=("Segoe UI", 9, "bold"),
            fg="#1E40AF",
            bg="#EFF6FF",
        ).pack(anchor="w")

        tk.Label(
            backup_box,
            text="An automated SQLite snapshot will be created in your backups directory before committing any records.\nAll insertions and updates run inside an atomic transaction with automatic rollback on error.",
            font=("Segoe UI", 8),
            fg="#3B82F6",
            bg="#EFF6FF",
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    # -------------------------------------------------------------------------
    # FILE BROWSING & LOADING
    # -------------------------------------------------------------------------
    def browse_csv(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select CSV Dataset to Import",
            filetypes=[("CSV Files (*.csv)", "*.csv"), ("All Files", "*.*")],
        )
        if path:
            self.load_file(Path(path))

    def browse_excel(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Excel Dataset to Import",
            filetypes=[("Excel Workbooks (*.xlsx)", "*.xlsx"), ("All Files", "*.*")],
        )
        if path:
            self.load_file(Path(path))

    def browse_all(self, event=None):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Dataset File to Import (.csv or .xlsx)",
            filetypes=[
                ("Supported Datasets (*.csv;*.xlsx)", "*.csv;*.xlsx"),
                ("CSV Files (*.csv)", "*.csv"),
                ("Excel Files (*.xlsx)", "*.xlsx"),
                ("All Files", "*.*"),
            ],
        )
        if path:
            self.load_file(Path(path))

    def _on_windnd_drop(self, files):
        if files:
            first_file = files[0]
            if isinstance(first_file, bytes):
                first_file = first_file.decode("utf-8", errors="replace")
            p = Path(first_file)
            if p.suffix.lower() in [".csv", ".xlsx", ".xls", ".xlsm"]:
                self.load_file(p)
            else:
                messagebox.showerror("Unsupported File", f"File '{p.name}' is not a supported .csv or .xlsx file.", parent=self)

    def preview_dataset_clicked(self):
        if not self.raw_rows:
            messagebox.showinfo("No File Selected", "Please upload a CSV or Excel dataset file first.", parent=self)
            return
        self.notebook.select(self.tab_preview_map)

    def load_file(self, p: Path):
        try:
            headers, rows, size, fmt = read_dataset_file(p)
            if not headers or not rows:
                messagebox.showerror("Empty File", f"The selected file '{p.name}' contains no headers or data rows.", parent=self)
                return

            self.current_file_path = p
            self.raw_headers = headers
            self.raw_rows = rows
            self.file_size = size
            self.file_format = fmt

            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.2f} MB"
            self.lbl_selected_file.config(text=f"Selected File: {p.name}", fg="#0F172A")
            self.lbl_file_size.config(text=f"File Size: {size_str} ({len(rows)} rows)", fg="#0F172A")
            self.lbl_file_format.config(text=f"Format: {fmt}", fg="#0F172A")

            # Detect initial mapping
            mapping = detect_column_mapping(headers)
            self._render_mapping_ui(headers, mapping)
            self._render_preview_table(headers, rows[:50], mapping)

            # Auto-run validation
            self.validate_dataset()

        except Exception as e:
            logger.error(f"Failed to read dataset file '{p}': {e}")
            messagebox.showerror("File Error", f"Unable to read dataset file:\n{e}", parent=self)

    # -------------------------------------------------------------------------
    # COLUMN MAPPING RENDERING & HANDLING
    # -------------------------------------------------------------------------
    def _render_mapping_ui(self, headers: List[str], initial_mapping: Dict[str, Optional[str]]):
        for widget in self.frame_mapping_inner.winfo_children():
            widget.destroy()
        self.mapping_combos.clear()
        self.mapping_badges.clear()

        options = ["-- Unmatched / Skip --"] + [f"{target} ({label})" for target, label, _ in ALL_TARGET_FIELDS]

        # Arrange in 2-column grid inside inner frame
        for idx, h in enumerate(headers):
            grid_row = idx // 2
            grid_col = idx % 2

            cell_frame = tk.Frame(self.frame_mapping_inner, bg="#FFFFFF", padx=6, pady=3)
            cell_frame.grid(row=grid_row, column=grid_col, sticky="ew", padx=4, pady=2)
            self.frame_mapping_inner.columnconfigure(grid_col, weight=1)

            lbl_h = tk.Label(
                cell_frame,
                text=h[:16] + ("..." if len(h) > 16 else ""),
                font=("Segoe UI", 8, "bold"),
                fg="#1E293B",
                bg="#FFFFFF",
                width=16,
                anchor="w",
            )
            lbl_h.pack(side="left")

            cb = ttk.Combobox(cell_frame, values=options, state="readonly", width=22, font=("Segoe UI", 8))
            cb.pack(side="left", padx=4)

            badge = tk.Label(cell_frame, text="", font=("Segoe UI", 7, "bold"), bg="#FFFFFF", width=10)
            badge.pack(side="left")

            matched_target = initial_mapping.get(h)
            if matched_target:
                for opt in options:
                    if opt.startswith(matched_target + " "):
                        cb.set(opt)
                        break
                badge.config(text="✅ Matched", fg="#15803D")
            else:
                cb.set("-- Unmatched / Skip --")
                badge.config(text="⚠️ Unmatched", fg="#B45309")

            cb.bind("<<ComboboxSelected>>", lambda e, hdr=h: self._on_mapping_change(hdr))
            self.mapping_combos[h] = cb
            self.mapping_badges[h] = badge

    def _on_mapping_change(self, header: str):
        cb = self.mapping_combos.get(header)
        badge = self.mapping_badges.get(header)
        if not cb or not badge:
            return

        sel = cb.get()
        if not sel or sel.startswith("--"):
            badge.config(text="⚠️ Unmatched", fg="#B45309")
        else:
            badge.config(text="✅ Matched", fg="#15803D")

        # Update preview table columns based on new mapping
        if self.raw_headers and self.raw_rows:
            self._render_preview_table(self.raw_headers, self.raw_rows[:50])

        self.validate_dataset()

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

    def check_ambiguous_mappings(self) -> Tuple[bool, str]:
        """Check for duplicate column mappings or missing required identifiers."""
        mapping = self.get_current_mapping()
        target_counts: Dict[str, List[str]] = {}
        for h, t in mapping.items():
            if t:
                target_counts.setdefault(t, []).append(h)

        ambiguous = []
        for t, hdrs in target_counts.items():
            if len(hdrs) > 1:
                ambiguous.append(f"• Target '{t}' is mapped to multiple columns: {', '.join(hdrs)}")

        if ambiguous:
            return True, "Ambiguous Column Mappings Detected:\n" + "\n".join(ambiguous)

        has_fam = "family_name" in mapping.values()
        has_pil = "full_name" in mapping.values()
        if not has_fam and not has_pil:
            return True, "Neither 'Family Name' nor 'Pilgrim Full Name' is mapped. At least one is required."

        return False, ""

    # -------------------------------------------------------------------------
    # DATA PREVIEW RENDERING
    # -------------------------------------------------------------------------
    def _render_preview_table(
        self,
        headers: List[str],
        sample_rows: List[Dict[str, Any]],
        mapping: Optional[Dict[str, Optional[str]]] = None,
    ):
        for item in self.tree_preview.get_children():
            self.tree_preview.delete(item)

        mapping = mapping or self.get_current_mapping()
        target_to_hdr: Dict[str, str] = {}
        for h, t in mapping.items():
            if t and t not in target_to_hdr:
                target_to_hdr[t] = h

        # Core required columns to show
        core_cols = [
            ("_row_num", "Row #", 55, "center"),
            ("fam_id", "Family ID", 110, "center"),
            ("fam_name", "Family Name", 140, "w"),
            ("pilgrim_name", "Pilgrim Name", 140, "w"),
            ("age", "Age", 55, "center"),
            ("gender", "Gender", 65, "center"),
            ("mobile", "Mobile Number", 110, "center"),
        ]

        mapped_hdrs = set(target_to_hdr.values())
        other_hdrs = [h for h in headers if h not in mapped_hdrs]

        all_col_ids = [c[0] for c in core_cols] + [f"other_{i}" for i in range(len(other_hdrs))]
        self.tree_preview["columns"] = all_col_ids

        for cid, title, w, align in core_cols:
            self.tree_preview.heading(cid, text=title)
            self.tree_preview.column(cid, width=w, anchor=align)

        for i, h in enumerate(other_hdrs):
            cid = f"other_{i}"
            self.tree_preview.heading(cid, text=h)
            self.tree_preview.column(cid, width=120, anchor="w")

        f_id_hdr = target_to_hdr.get("family_code")
        f_name_hdr = target_to_hdr.get("family_name")
        p_name_hdr = target_to_hdr.get("full_name")
        age_hdr = target_to_hdr.get("age")
        gender_hdr = target_to_hdr.get("gender")
        phone_hdr = target_to_hdr.get("phone")

        for idx, r in enumerate(sample_rows):
            row_num = r.get("_row_num", idx + 1)
            fam_id = str(r.get(f_id_hdr, "")) if f_id_hdr else ""
            fam_name = str(r.get(f_name_hdr, "")) if f_name_hdr else ""
            p_name = str(r.get(p_name_hdr, "")) if p_name_hdr else ""
            age = str(r.get(age_hdr, "")) if age_hdr else ""
            gender = str(r.get(gender_hdr, "")) if gender_hdr else ""
            mobile = str(r.get(phone_hdr, "")) if phone_hdr else ""

            if not fam_name and p_name:
                fam_name = f"{p_name} Family"

            vals = [row_num, fam_id, fam_name, p_name, age, gender, mobile] + [str(r.get(h, "")) for h in other_hdrs]
            self.tree_preview.insert("", "end", values=vals)

    # -------------------------------------------------------------------------
    # VALIDATION ENGINE & ROW-SPECIFIC ERROR BREAKDOWN
    # -------------------------------------------------------------------------
    def validate_dataset(self):
        if not self.raw_rows:
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
            dup = analysis["duplicate_records_count"]
            skip = analysis["skipped_records_count"]

            # 1. Update Tab 2 Row Error Table
            for item in self.tree_errors.get_children():
                self.tree_errors.delete(item)

            val_errors = analysis.get("validation_errors", [])
            for err in val_errors:
                self.tree_errors.insert(
                    "",
                    "end",
                    values=(
                        err.get("row", ""),
                        err.get("column", ""),
                        err.get("value", ""),
                        err.get("error", ""),
                        err.get("severity", "Error"),
                    ),
                )

            if invalid > 0:
                self.lbl_val_status.config(
                    text=f"⚠️ {invalid} row-specific validation error(s) found across {tot} rows. Review below:",
                    fg="#DC2626",
                )
                self.btn_export_errors.config(state="normal")
            else:
                self.lbl_val_status.config(
                    text=f"✅ All {tot} rows validated successfully with zero errors!",
                    fg="#15803D",
                )
                self.btn_export_errors.config(state="disabled")

            # 2. Update Tab 3 Summary Badges
            self.badge_sum_labels["tot"].config(text=str(tot))
            self.badge_sum_labels["valid"].config(text=str(valid))
            self.badge_sum_labels["invalid"].config(text=str(invalid))
            self.badge_sum_labels["new_f"].config(text=str(new_f))
            self.badge_sum_labels["new_p"].config(text=str(new_p))
            self.badge_sum_labels["dup"].config(text=str(dup))
            self.badge_sum_labels["skip"].config(text=str(skip))

            # 3. Update Sticky Bottom Summary Label
            summary_str = (
                f"📊 Total Rows: {tot}  |  ✅ Valid: {valid}  |  ⚠️ Invalid: {invalid}  |  "
                f"👥 New Families: {new_f}  |  👤 New Pilgrims: {new_p}  |  ⏩ Skipped: {skip}"
            )
            self.lbl_bottom_summary.config(
                text=summary_str,
                fg="#0F172A" if invalid == 0 else "#B45309",
            )

            # 4. Commit Button State
            if valid > 0:
                self.btn_commit.config(state="normal", bg="#15803D")
            else:
                self.btn_commit.config(state="disabled", bg="#94A3B8")

        except Exception as e:
            logger.error(f"Dataset validation error: {e}")
            self.lbl_bottom_summary.config(text=f"❌ Validation Error: {e}", fg="#DC2626")
            self.lbl_val_status.config(text=f"❌ Validation Error: {e}", fg="#DC2626")
            self.btn_commit.config(state="disabled", bg="#94A3B8")

    def download_error_report(self):
        if not self.analysis_result or not self.analysis_result.get("validation_errors"):
            messagebox.showinfo("No Errors", "No validation errors to export.", parent=self)
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

    # -------------------------------------------------------------------------
    # IMPORT COMMIT & DATABASE INTEGRATION
    # -------------------------------------------------------------------------
    def commit_import(self):
        if not self.analysis_result:
            return

        valid_count = self.analysis_result.get("valid_rows_count", 0)
        invalid_count = self.analysis_result.get("invalid_rows_count", 0)
        tot = self.analysis_result.get("total_rows", 0)
        new_f = self.analysis_result.get("new_families_count", 0)
        new_p = self.analysis_result.get("new_pilgrims_count", 0)
        dup = self.analysis_result.get("duplicate_records_count", 0)
        skip = self.analysis_result.get("skipped_records_count", 0)
        policy = self.dup_var.get()

        # Step 1: Check ambiguous mappings
        is_ambiguous, amb_msg = self.check_ambiguous_mappings()
        if is_ambiguous:
            proceed_amb = messagebox.askyesno(
                "Ambiguous Mapping Warning",
                f"⚠️ {amb_msg}\n\nDo you want to proceed anyway?",
                parent=self,
            )
            if not proceed_amb:
                return

        # Step 2: Confirmation if UPDATE policy selected
        if policy == DUP_POLICY_UPDATE:
            confirm_upd = messagebox.askyesno(
                "Confirm Record Update",
                "⚠️ Update Policy Selected:\nExisting database records will be updated with new data from file.\n\nAre you sure you want to proceed?",
                parent=self,
            )
            if not confirm_upd:
                return

        # Step 3: Full import summary confirmation modal
        summary_msg = (
            "📋 DATASET IMPORT SUMMARY & CONFIRMATION\n"
            "===========================================\n"
            f"• Total Rows in File:       {tot}\n"
            f"• Valid Records to Import:  {valid_count}\n"
            f"• Rejected Invalid Rows:    {invalid_count}\n"
            f"• New Families to Create:   {new_f}\n"
            f"• New Pilgrims to Add:      {new_p}\n"
            f"• Duplicate Records:        {dup}\n"
            f"• Records to Skip:          {skip}\n"
            f"• Duplicate Handling:       {policy}\n"
            "===========================================\n\n"
            "🛡️ An automatic SQLite database backup will be created before committing.\n"
            "All operations run within an atomic transaction.\n\n"
            "Do you want to commit these records to the database now?"
        )

        confirm_commit = messagebox.askyesno("Confirm Dataset Import", summary_msg, parent=self)
        if not confirm_commit:
            return

        try:
            # Create pre-import database backup
            try:
                create_database_backup(db_path=self.db_path)
            except Exception as b_err:
                logger.warning(f"Pre-import backup warning: {b_err}")

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

            # Trigger on_success callback to automatically refresh dashboard statistics
            if self.on_success:
                try:
                    self.on_success()
                except Exception as cb_err:
                    logger.error(f"Dashboard refresh callback error: {cb_err}")

            messagebox.showinfo(
                "Import Successful",
                f"✅ Dataset Import Completed!\n\n"
                f"• Successfully Imported: {res.get('successful_records', 0)} devotee records\n"
                f"• Families Created: {new_f}\n"
                f"• Batch ID: {res.get('batch_id', 'N/A')}\n\n"
                f"Dashboard statistics have been refreshed.",
                parent=self,
            )

            self.destroy()

        except Exception as e:
            logger.error(f"Dataset import execution failed: {e}")
            messagebox.showerror(
                "Import Failed",
                f"A database error occurred during import:\n{e}\n\nTransaction has been rolled back safely.",
                parent=self,
            )

