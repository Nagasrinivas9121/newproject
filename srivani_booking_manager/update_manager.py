"""
SRIVANI BOOKING MANAGER - Safe Application Update & Migration Engine
Ensures atomic pre-migration backups, migration integrity validation,
safe rollback mechanisms, and strict protection against silent data overwrites.
"""
import sys
import os
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List, Callable

from config import DB_PATH, BACKUPS_DIR
from database import get_connection, get_current_schema_version
from backup_manager import create_database_backup, validate_backup_file
from logger import get_logger

logger = get_logger("update_manager")


def prepare_pre_update_backup(
    db_path: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
) -> Path:
    """
    Perform a verified online snapshot before performing any schema update or application migration.
    Returns path to the verified snapshot.
    """
    src_db = db_path or DB_PATH
    dest_dir = backup_dir or BACKUPS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not src_db.exists():
        raise FileNotFoundError(f"Database file does not exist: {src_db}")

    ver = get_current_schema_version(src_db)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_path = dest_dir / f"srivani_pre_update_v{ver}_{timestamp}.db"

    # Online backup using backup_manager
    created_path = create_database_backup(dest_path=snapshot_path, db_path=src_db)
    logger.info(f"Pre-update snapshot created successfully at: {created_path}")
    return created_path


def validate_database_schema(db_path: Optional[Path] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate that the database schema is intact, free of corruption, and foreign keys pass.
    """
    src_db = db_path or DB_PATH
    if not src_db.exists():
        return False, f"Database file does not exist at {src_db}", {}

    try:
        with get_connection(src_db) as con:
            # 1. PRAGMA integrity_check
            chk = con.execute("PRAGMA integrity_check").fetchone()
            if not chk or chk[0] != "ok":
                return False, f"SQLite integrity check failed: {chk}", {}

            # 2. PRAGMA foreign_key_check
            fk_violations = con.execute("PRAGMA foreign_key_check").fetchall()
            if fk_violations:
                return False, f"Foreign key violations found: {len(fk_violations)} rows", {}

            # 3. Check core tables
            tables_cur = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r["name"] for r in tables_cur.fetchall()}
            required_tables = {"families", "pilgrims", "queue_history", "schema_version"}
            missing = required_tables - tables
            if missing:
                return False, f"Missing required core tables: {missing}", {}

            # 4. Get schema version
            ver_row = con.execute("SELECT MAX(version) AS ver FROM schema_version").fetchone()
            cur_ver = ver_row["ver"] if ver_row and ver_row["ver"] is not None else 0

            return True, "Database schema and integrity are healthy.", {
                "schema_version": cur_ver,
                "table_count": len(tables),
                "tables": sorted(list(tables)),
                "integrity": "ok",
            }
    except Exception as e:
        logger.error(f"Schema validation error: {e}")
        return False, f"Schema validation exception: {e}", {}


def execute_safe_migration(
    target_version: int,
    description: str,
    migration_fn: Callable[[sqlite3.Connection], None],
    db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Safely execute a schema migration:
    1. Creates atomic pre-migration backup.
    2. Runs migration function in a transaction.
    3. Verifies schema integrity post-migration.
    4. Automatically rolls back to snapshot if anything fails.
    """
    src_db = db_path or DB_PATH
    if not src_db.exists():
        return False, f"Target database does not exist: {src_db}"

    # Step 1: Pre-update snapshot
    try:
        snapshot = prepare_pre_update_backup(src_db)
    except Exception as e:
        logger.error(f"Failed to create pre-update backup: {e}")
        return False, f"Pre-update backup failed: {e}. Aborting migration to protect data."

    # Step 2: Run migration in transaction
    con = sqlite3.connect(str(src_db))
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        con.execute("BEGIN TRANSACTION;")

        # Execute migration operations
        migration_fn(con)

        # Record migration
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        con.execute(
            "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
            (target_version, now_str, description),
        )

        con.commit()
    except Exception as migration_err:
        con.rollback()
        con.close()
        logger.error(f"Migration to v{target_version} failed: {migration_err}. Restoring snapshot...")
        # Automatic recovery from snapshot
        rollback_database(snapshot, src_db)
        return False, f"Migration failed and was safely rolled back: {migration_err}"
    finally:
        try:
            con.close()
        except Exception:
            pass

    # Step 3: Verify post-migration integrity
    is_valid, reason, _ = validate_database_schema(src_db)
    if not is_valid:
        logger.error(f"Post-migration integrity check failed: {reason}. Rolling back...")
        rollback_database(snapshot, src_db)
        return False, f"Post-migration integrity check failed: {reason}. Restored to snapshot."

    logger.info(f"Migration to v{target_version} ({description}) completed and verified successfully.")
    return True, f"Migration to v{target_version} successfully applied and verified."


def rollback_database(
    snapshot_path: Path,
    target_db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Safely restore database from a snapshot with pre-rollback safety copy.
    """
    dest_db = target_db_path or DB_PATH
    snap = Path(snapshot_path)

    if not snap.exists():
        return False, f"Snapshot file not found: {snap}"

    # Validate snapshot before restoring
    is_valid, reason = validate_backup_file(snap)
    if not is_valid:
        return False, f"Cannot restore invalid snapshot: {reason}"

    # Create safety backup of current target if it exists
    if dest_db.exists():
        safety_path = dest_db.parent / f"srivani_safety_pre_rollback_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
        try:
            shutil.copy2(dest_db, safety_path)
        except Exception as e:
            return False, f"Could not create safety backup before rollback: {e}"

    # Restore using SQLite online backup
    try:
        src_con = sqlite3.connect(str(snap))
        dest_con = sqlite3.connect(str(dest_db))
        try:
            src_con.backup(dest_con)
        finally:
            dest_con.close()
            src_con.close()

        logger.info(f"Database safely restored from snapshot: {snap}")
        return True, f"Database restored successfully from: {snap.name}"
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False, f"Rollback failed: {e}"


def get_migration_history(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all applied migrations recorded in schema_version."""
    src_db = db_path or DB_PATH
    if not src_db.exists():
        return []

    try:
        with get_connection(src_db) as con:
            cur = con.execute("SELECT version, applied_at, description FROM schema_version ORDER BY version ASC")
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching migration history: {e}")
        return []
