"""
SRIVANI BOOKING MANAGER - Phase 10
Data Cleanup & Mock Data Removal Engine

Safely identifies and removes artificial, mock, sample, or test records from the
production SQLite database while strictly preserving real user-created records,
administrator accounts, application settings, and uploaded files.

Safety Guarantees:
1. Always creates an automated full database backup before cleanup.
2. Identifies mock records using verifiable seed markers & known demo templates.
3. Ambiguous records are NEVER automatically deleted; they are retained for admin review.
4. Records all cleanup actions in an immutable cleanup audit log.
"""

import sqlite3
import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import tkinter as tk
from tkinter import ttk, messagebox

from config import DB_PATH
from database import (
    get_connection,
    record_cleanup_audit,
    get_cleanup_audits,
)
from backup_manager import create_database_backup
from logger import get_logger

logger = get_logger("data_cleanup")

# Verified mock / demo signatures
MOCK_FAMILY_CODES = {"FAM-001", "FAM-002", "FAM-003"}
MOCK_DOMAINS = {"@example.com", "@sample.com", "@test.com", "@dummy.com"}
MOCK_NAMES = {
    "reddy family",
    "sharma family",
    "verma family",
    "varadarajan pilgrims roster",
}
MOCK_PHONES = {"9848022338", "9440112233", "9876543210"}


def scan_for_mock_data(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Scan the database for artificial or demo records without modifying any data.
    
    Returns structured analysis categorizing records into:
    - mock_records: Confirmed mock/sample records with clear evidence
    - ambiguous_records: Records requiring admin inspection
    - legitimate_records: Clean, real user records that will be preserved
    """
    mock_records: List[Dict[str, Any]] = []
    ambiguous_records: List[Dict[str, Any]] = []
    legitimate_records: List[Dict[str, Any]] = []

    with get_connection(db_path) as con:
        families = con.execute("SELECT * FROM families").fetchall()

        for fam_row in families:
            fam = dict(fam_row)
            fid = fam["id"]
            code = str(fam.get("family_code") or "").strip()
            name = str(fam.get("family_name") or "").strip().lower()
            email = str(fam.get("email") or "").strip().lower()
            phone = str(fam.get("phone") or "").strip()
            ticket_path = str(fam.get("ticket_pdf_path") or "").strip()

            pilgrims = con.execute("SELECT * FROM pilgrims WHERE family_id = ?", (fid,)).fetchall()
            fam["pilgrims"] = [dict(p) for p in pilgrims]
            fam["pilgrim_count"] = len(pilgrims)

            evidence = []

            # 1. Check known mock codes from sample templates
            if code in MOCK_FAMILY_CODES:
                evidence.append(f"Known sample template code '{code}'")

            # 2. Check dummy test email domains
            for dom in MOCK_DOMAINS:
                if dom in email:
                    evidence.append(f"Dummy email domain '{dom}' in '{email}'")

            # 3. Check sample names and phone numbers
            if name in MOCK_NAMES and code in MOCK_FAMILY_CODES:
                evidence.append(f"Matches sample template family name '{fam['family_name']}'")
            elif name in MOCK_NAMES and any(dom in email for dom in MOCK_DOMAINS):
                evidence.append(f"Sample devotee name with demo domain: '{fam['family_name']}'")
            elif name == "varadarajan pilgrims roster" and phone == "9822233344":
                evidence.append("Screenshot capture test record ('Varadarajan Pilgrims Roster')")

            fam["evidence"] = evidence

            # Categorize based on evidence and presence of legitimate assets
            if evidence:
                # If a family has a real ticket PDF attached on disk, mark as AMBIGUOUS for safety
                if ticket_path and Path(ticket_path).exists() and not any(t in ticket_path.lower() for t in ["mock", "demo", "sample", "test"]):
                    fam["ambiguous_reason"] = f"Has physical ticket file at '{ticket_path}' despite mock markers."
                    ambiguous_records.append(fam)
                else:
                    mock_records.append(fam)
            else:
                legitimate_records.append(fam)

    total_mock_pilgrims = sum(f["pilgrim_count"] for f in mock_records)
    total_ambiguous_pilgrims = sum(f["pilgrim_count"] for f in ambiguous_records)
    total_legitimate_pilgrims = sum(f["pilgrim_count"] for f in legitimate_records)

    return {
        "mock_families": mock_records,
        "ambiguous_families": ambiguous_records,
        "legitimate_families": legitimate_records,
        "total_mock_pilgrims": total_mock_pilgrims,
        "total_ambiguous_pilgrims": total_ambiguous_pilgrims,
        "total_legitimate_pilgrims": total_legitimate_pilgrims,
        "has_mock_data": len(mock_records) > 0,
        "has_ambiguous_data": len(ambiguous_records) > 0,
    }


def cleanup_mock_data(
    admin_user: str = "admin",
    db_path: Optional[Path] = None,
    force: bool = False,
    include_ambiguous_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Safely purge confirmed mock data from the database.
    
    Always creates a full backup before performing any deletion.
    Cascades deletion to pilgrims, queue history, and document records.
    Logs the action to the cleanup audit log.
    """
    scan = scan_for_mock_data(db_path)
    mock_fams = scan["mock_families"]
    ambiguous_fams = scan["ambiguous_families"]

    target_ids = [f["id"] for f in mock_fams]

    # Include specific ambiguous IDs only if explicitly approved
    if include_ambiguous_ids:
        for f in ambiguous_fams:
            if f["id"] in include_ambiguous_ids:
                target_ids.append(f["id"])

    if not target_ids:
        return {
            "status": "NO_OP",
            "message": "No mock records found in the database. Database is already clean.",
            "deleted_families": 0,
            "deleted_pilgrims": 0,
            "backup_path": None,
        }

    # 1. Create automatic safety backup before destructive operations
    backup_path = create_database_backup(db_path=db_path)
    logger.info(f"Safety backup created prior to mock data cleanup: {backup_path}")

    cleanup_id = f"CLEANUP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    deleted_fams_count = len(target_ids)
    deleted_pilgrims_count = 0

    with get_connection(db_path) as con:
        # Count pilgrims to be deleted
        placeholders = ",".join("?" for _ in target_ids)
        p_count = con.execute(
            f"SELECT COUNT(*) FROM pilgrims WHERE family_id IN ({placeholders})",
            target_ids,
        ).fetchone()[0]
        deleted_pilgrims_count = p_count

        # Delete dependent documents
        con.execute(
            f"DELETE FROM family_documents WHERE family_id IN ({placeholders})",
            target_ids,
        )

        # Delete dependent queue history
        con.execute(
            f"DELETE FROM queue_history WHERE family_id IN ({placeholders})",
            target_ids,
        )

        # Delete dependent pilgrims
        con.execute(
            f"DELETE FROM pilgrims WHERE family_id IN ({placeholders})",
            target_ids,
        )

        # Delete families
        con.execute(
            f"DELETE FROM families WHERE id IN ({placeholders})",
            target_ids,
        )

        con.commit()

    # 2. Record audit log
    details_str = f"Purged {deleted_fams_count} mock families and {deleted_pilgrims_count} mock pilgrims. IDs: {target_ids}"
    record_cleanup_audit(
        cleanup_id=cleanup_id,
        admin_user=admin_user,
        backup_path=str(backup_path),
        deleted_families_count=deleted_fams_count,
        deleted_pilgrims_count=deleted_pilgrims_count,
        details=details_str,
        db_path=db_path,
    )

    logger.info(f"Mock data cleanup completed: {details_str}")

    return {
        "status": "SUCCESS",
        "cleanup_id": cleanup_id,
        "deleted_families": deleted_fams_count,
        "deleted_pilgrims": deleted_pilgrims_count,
        "retained_legitimate": len(scan["legitimate_families"]),
        "retained_ambiguous": len(scan["ambiguous_families"]),
        "backup_path": str(backup_path),
        "message": f"Successfully purged {deleted_fams_count} mock families ({deleted_pilgrims_count} pilgrims). Pre-cleanup backup saved.",
    }


class DataCleanupDialog(tk.Toplevel):
    """
    Modern Windows GUI dialog for reviewing and executing safe mock data cleanup.
    Provides clear preview, lists reasons, shows backup path, and requires explicit confirmation.
    """

    def __init__(self, parent, app_controller, db_path: Optional[Path] = None, on_complete=None):
        super().__init__(parent)
        self.app = app_controller
        self.db_path = db_path or DB_PATH
        self.on_complete = on_complete

        self.title("🧹 Data Cleanup & Mock Data Purge — SRIVANI BOOKING MANAGER")
        self.geometry("880x620")
        self.minsize(780, 520)
        self.configure(bg="#F8FAFC")
        self.transient(parent)

        self._build_ui()
        self.refresh_scan()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(container, bg="#FFFFFF", padx=16, pady=12, bd=1, relief="solid")
        header.pack(fill="x", pady=(0, 12))

        tk.Label(
            header,
            text="🧹 DATABASE CLEANUP & MOCK DATA PURGE",
            font=("Segoe UI", 13, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Safely scan and purge development mock data while preserving real devotee records, admin accounts, and settings.",
            font=("Segoe UI", 9),
            fg="#64748B",
            bg="#FFFFFF",
        ).pack(anchor="w", pady=(2, 0))

        # KPI Summary Cards
        kpi_frame = tk.Frame(container, bg="#F8FAFC")
        kpi_frame.pack(fill="x", pady=(0, 12))

        self.card_mock = self._create_card(kpi_frame, "CONFIRMED MOCK", "0", "#DC2626")
        self.card_ambiguous = self._create_card(kpi_frame, "AMBIGUOUS / REVIEW", "0", "#D97706")
        self.card_legitimate = self._create_card(kpi_frame, "LEGITIMATE (PRESERVED)", "0", "#15803D")

        # Treeview for Preview
        tbl_box = ttk.LabelFrame(container, text=" Detected Mock & Sample Records (Preview) ", padding=10)
        tbl_box.pack(fill="both", expand=True, pady=(0, 12))

        cols = ("id", "code", "name", "phone", "email", "pils", "evidence")
        self.tree = ttk.Treeview(tbl_box, columns=cols, show="headings", height=8)
        self.tree.heading("id", text="#")
        self.tree.heading("code", text="Code")
        self.tree.heading("name", text="Family Name")
        self.tree.heading("phone", text="Phone")
        self.tree.heading("email", text="Email")
        self.tree.heading("pils", text="Devotees")
        self.tree.heading("evidence", text="Mock Evidence / Detection Reason")

        self.tree.column("id", width=35, anchor="center")
        self.tree.column("code", width=90, anchor="center")
        self.tree.column("name", width=160)
        self.tree.column("phone", width=95)
        self.tree.column("email", width=140)
        self.tree.column("pils", width=65, anchor="center")
        self.tree.column("evidence", width=240)

        scroll = ttk.Scrollbar(tbl_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Bottom Safety Notice & Actions
        safety_box = tk.Frame(container, bg="#EFF6FF", bd=1, relief="solid", padx=12, pady=8)
        safety_box.pack(fill="x", pady=(0, 12))

        tk.Label(
            safety_box,
            text="🛡️ Automatic Database Backup Guarantee:",
            font=("Segoe UI", 9, "bold"),
            fg="#1E40AF",
            bg="#EFF6FF",
        ).pack(anchor="w")

        tk.Label(
            safety_box,
            text="A full timestamped SQLite snapshot is automatically saved to data/backups/ before any records are modified. Legitimate records and administrative credentials will never be touched.",
            font=("Segoe UI", 8),
            fg="#1E3A8A",
            bg="#EFF6FF",
            wraplength=800,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        # Action Buttons
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x")

        ttk.Button(btn_bar, text="🔄 Re-Scan Database", command=self.refresh_scan).pack(side="left", padx=(0, 8))
        self.btn_purge = tk.Button(
            btn_bar,
            text="🗑️ Execute Safe Mock Purge (Auto Backup)",
            font=("Segoe UI", 9, "bold"),
            bg="#DC2626",
            fg="#FFFFFF",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.confirm_and_purge,
        )
        self.btn_purge.pack(side="left")

        ttk.Button(btn_bar, text="Close", command=self.destroy).pack(side="right")

    def _create_card(self, parent, title, val, color):
        box = tk.Frame(parent, bg="#FFFFFF", bd=1, relief="solid", padx=14, pady=8)
        box.pack(side="left", expand=True, fill="x", padx=4)
        tk.Label(box, text=title, font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#FFFFFF").pack(anchor="w")
        lbl_v = tk.Label(box, text=val, font=("Segoe UI", 16, "bold"), fg=color, bg="#FFFFFF")
        lbl_v.pack(anchor="w")
        return lbl_v

    def refresh_scan(self):
        scan = scan_for_mock_data(self.db_path)
        self.scan_result = scan

        self.card_mock.config(text=f"{len(scan['mock_families'])} families ({scan['total_mock_pilgrims']} p.)")
        self.card_ambiguous.config(text=f"{len(scan['ambiguous_families'])} families")
        self.card_legitimate.config(text=f"{len(scan['legitimate_families'])} families")

        for item in self.tree.get_children():
            self.tree.delete(item)

        if not scan["mock_families"]:
            self.btn_purge.config(state="disabled", bg="#94A3B8")
            self.tree.insert("", "end", values=("-", "-", "No mock records detected.", "-", "-", "-", "Database is clean!"))
            return

        self.btn_purge.config(state="normal", bg="#DC2626")

        for fam in scan["mock_families"]:
            evidence_str = "; ".join(fam.get("evidence", []))
            self.tree.insert(
                "",
                "end",
                values=(
                    fam["id"],
                    fam.get("family_code", ""),
                    fam.get("family_name", ""),
                    fam.get("phone", ""),
                    fam.get("email", ""),
                    fam["pilgrim_count"],
                    evidence_str,
                ),
            )

    def confirm_and_purge(self):
        scan = self.scan_result
        mock_count = len(scan["mock_families"])
        if mock_count == 0:
            messagebox.showinfo("Clean Database", "No mock records detected in database.")
            return

        confirm = messagebox.askyesno(
            "Confirm Mock Data Cleanup",
            f"Are you sure you want to permanently purge {mock_count} mock families "
            f"({scan['total_mock_pilgrims']} pilgrim records)?\n\n"
            f"A full database backup will be created automatically before cleanup.\n"
            f"All {len(scan['legitimate_families'])} real user records will be preserved.",
            parent=self,
        )
        if not confirm:
            return

        res = cleanup_mock_data(db_path=self.db_path)
        if res["status"] == "SUCCESS":
            messagebox.showinfo(
                "Cleanup Successful",
                f"{res['message']}\n\nBackup created at:\n{res['backup_path']}",
                parent=self,
            )
            self.refresh_scan()
            if self.on_complete:
                self.on_complete()
            if hasattr(self.app, "refresh"):
                self.app.refresh()
        else:
            messagebox.showerror("Cleanup Issue", res.get("message", "Operation failed."), parent=self)
