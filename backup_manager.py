"""
SRIVANI BOOKING MANAGER - Database Backup and Disaster Recovery Engine
Supports verified SQLite online backups, integrity checks, and safe restore with pre-restore snapshots.
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from config import DB_PATH, BACKUPS_DIR
from database import get_connection

def create_database_backup(
    dest_path: Optional[str | Path] = None,
    db_path: Optional[Path] = None,
) -> Path:
    """
    Perform a safe, verified online SQLite backup.
    Guarantees consistent snapshot without table locking issues.
    """
    src_path = db_path or DB_PATH
    if not src_path.exists():
        raise FileNotFoundError(f"Source database file does not exist: {src_path}")

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    if dest_path:
        out_path = Path(dest_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = BACKUPS_DIR / f"srivani_backup_{timestamp}.db"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Use SQLite online backup API
    src_con = sqlite3.connect(str(src_path))
    dest_con = sqlite3.connect(str(out_path))
    try:
        src_con.backup(dest_con)
    finally:
        dest_con.close()
        src_con.close()

    # Verify backup integrity
    verify_con = sqlite3.connect(str(out_path))
    try:
        check = verify_con.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0] != "ok":
            raise ValueError(f"Integrity check failed on created backup: {check}")
    finally:
        verify_con.close()

    return out_path

def validate_backup_file(backup_path: str | Path) -> tuple[bool, str]:
    """Validate that a file is an authentic Srivani Manager SQLite database."""
    p = Path(backup_path)
    if not p.exists() or p.stat().st_size == 0:
        return False, "File does not exist or is empty"

    try:
        con = sqlite3.connect(str(p))
        try:
            cur = con.execute("PRAGMA integrity_check")
            row = cur.fetchone()
            if not row or row[0] != "ok":
                return False, "Database file failed SQLite integrity check"

            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "families" not in tables or "pilgrims" not in tables:
                return False, "Missing required tables (families, pilgrims)"

            return True, "Valid Srivani database backup"
        finally:
            con.close()
    except Exception as e:
        return False, f"Failed to read backup: {e}"

def list_backups() -> List[Dict[str, Any]]:
    """List all available backup files in the default backups directory."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    for f in sorted(BACKUPS_DIR.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
        size_kb = round(f.stat().st_size / 1024, 1)
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        is_valid, reason = validate_backup_file(f)
        backups.append({
            "path": f,
            "filename": f.name,
            "size_kb": size_kb,
            "modified": mtime,
            "is_valid": is_valid,
            "notes": reason,
        })
    return backups

def restore_database_backup(
    backup_path: str | Path,
    db_path: Optional[Path] = None,
) -> Path:
    """
    Restore the database from a verified backup file.
    Automatically creates a safety snapshot of the active database before overwriting.
    """
    b_path = Path(backup_path)
    is_valid, reason = validate_backup_file(b_path)
    if not is_valid:
        raise ValueError(f"Cannot restore invalid backup: {reason}")

    target_path = db_path or DB_PATH

    # Create safety pre-restore snapshot if target exists
    safety_path = None
    if target_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_path = BACKUPS_DIR / f"srivani_safety_pre_restore_{timestamp}.db"
        create_database_backup(dest_path=safety_path, db_path=target_path)

    # Restore backup using SQLite online backup API
    src_con = sqlite3.connect(str(b_path))
    dest_con = sqlite3.connect(str(target_path))
    try:
        src_con.backup(dest_con)
    finally:
        dest_con.close()
        src_con.close()

    return safety_path

class BackupRestoreDialog(tk.Toplevel):
    """Admin modal dialog to create, inspect, and safely restore database backups."""

    def __init__(self, parent, on_restore_callback: Callable[[], None]):
        super().__init__(parent)
        self.title("Database Backup & Recovery Manager")
        self.geometry("780x520")
        self.minsize(680, 440)
        self.transient(parent)
        self.grab_set()
        self.on_restore_callback = on_restore_callback

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Header
        hdr = ttk.Frame(container)
        hdr.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr, text="Database Backup & Recovery", font=("Segoe UI", 13, "bold"), foreground="#1B365D").pack(anchor="w")
        ttk.Label(hdr, text="Create verified database snapshots and restore data safely with automated pre-restore protection", font=("Segoe UI", 9), foreground="#64748B").pack(anchor="w")

        # Action Buttons
        top_bar = ttk.Frame(container)
        top_bar.pack(fill="x", pady=(0, 10))

        ttk.Button(top_bar, text="➕ Create New Backup Now", command=self._create_backup).pack(side="left", padx=(0, 8))
        ttk.Button(top_bar, text="📁 Restore from External File...", command=self._restore_from_file).pack(side="left")
        ttk.Button(top_bar, text="🔄 Refresh List", command=self.refresh).pack(side="right")

        # Treeview table
        tbl_frame = ttk.Frame(container)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("filename", "size", "date", "status")
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("filename", text="Backup Filename")
        self.tree.heading("size", text="Size (KB)")
        self.tree.heading("date", text="Date Created")
        self.tree.heading("status", text="Integrity Status")

        self.tree.column("filename", width=300)
        self.tree.column("size", width=90, anchor="center")
        self.tree.column("date", width=160, anchor="center")
        self.tree.column("status", width=160)

        y_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        # Bottom Bar
        bottom = ttk.Frame(container)
        bottom.pack(fill="x")
        self.lbl_info = ttk.Label(bottom, text="0 backup(s) available", font=("Segoe UI", 9), foreground="#64748B")
        self.lbl_info.pack(side="left")

        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right", padx=(8, 0))
        self.btn_restore = ttk.Button(bottom, text="⚠️ Restore Selected Backup", command=self._restore_selected)
        self.btn_restore.pack(side="right")

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        backups = list_backups()
        for idx, b in enumerate(backups):
            st_text = "✓ Valid & Verified" if b["is_valid"] else f"✕ Invalid ({b['notes']})"
            self.tree.insert("", "end", iid=str(idx), values=(
                b["filename"],
                b["size_kb"],
                b["modified"],
                st_text,
            ))

        self.lbl_info.config(text=f"{len(backups)} backup(s) stored in {BACKUPS_DIR.name}")

    def _create_backup(self):
        try:
            backup_file = create_database_backup()
            self.refresh()
            messagebox.showinfo("Backup Created", f"Successfully created database backup at:\n{backup_file}", parent=self)
        except Exception as e:
            messagebox.showerror("Backup Failed", f"Could not create backup:\n{e}", parent=self)

    def _restore_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Backup", "Please select a backup file from the list to restore.", parent=self)
            return

        idx = int(sel[0])
        backups = list_backups()
        if not (0 <= idx < len(backups)):
            return

        target_backup = backups[idx]
        if not target_backup["is_valid"]:
            messagebox.showerror("Cannot Restore", f"Selected backup is not valid:\n{target_backup['notes']}", parent=self)
            return

        msg = (
            f"WARNING: RESTORE DATABASE\n\n"
            f"Restoring will overwrite current database records with:\n"
            f"File: {target_backup['filename']}\n"
            f"Date: {target_backup['modified']}\n\n"
            f"A pre-restore safety copy of your active database will be made automatically before restoring.\n\n"
            f"Are you sure you want to proceed?"
        )
        if not messagebox.askyesno("Confirm Database Restore", msg, default="no", parent=self):
            return

        try:
            safety_path = restore_database_backup(target_backup["path"])
            self.on_restore_callback()
            self.refresh()
            res_msg = f"Database successfully restored from:\n{target_backup['filename']}"
            if safety_path:
                res_msg += f"\n\nPre-restore safety snapshot saved to:\n{safety_path.name}"
            messagebox.showinfo("Restore Complete", res_msg, parent=self)
        except Exception as e:
            messagebox.showerror("Restore Failed", f"Failed to restore database:\n{e}", parent=self)

    def _restore_from_file(self):
        custom_file = filedialog.askopenfilename(
            parent=self,
            title="Select Valid Srivani Database Backup File",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if not custom_file:
            return

        is_valid, reason = validate_backup_file(custom_file)
        if not is_valid:
            messagebox.showerror("Invalid File", f"Selected file is not a valid Srivani database:\n{reason}", parent=self)
            return

        msg = (
            f"WARNING: RESTORE FROM EXTERNAL FILE\n\n"
            f"Selected file: {custom_file}\n\n"
            f"This will replace all current database records. An automated safety snapshot will be created first.\n\n"
            f"Proceed with restoration?"
        )
        if not messagebox.askyesno("Confirm Restore", msg, default="no", parent=self):
            return

        try:
            safety_path = restore_database_backup(custom_file)
            self.on_restore_callback()
            self.refresh()
            res_msg = f"Database successfully restored from external file!"
            if safety_path:
                res_msg += f"\n\nSafety snapshot saved to:\n{safety_path.name}"
            messagebox.showinfo("Restore Complete", res_msg, parent=self)
        except Exception as e:
            messagebox.showerror("Restore Failed", f"Failed to restore database:\n{e}", parent=self)
