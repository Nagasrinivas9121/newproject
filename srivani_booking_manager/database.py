"""
SRIVANI BOOKING MANAGER - Database Layer & Schema Migrations
"""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Generator
from config import (
    DB_PATH,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_UNAVAILABLE,
    STATUS_CANCELLED,
    PAYMENT_NOT_REQUESTED,
    PRIORITY_NORMAL,
    BOOKING_TYPE_ADVANCE,
)

@contextmanager
def get_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Connect to SQLite with foreign keys enabled, Row factory, and guaranteed close."""
    path = db_path or DB_PATH
    if isinstance(path, str):
        path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    try:
        yield con
    finally:
        con.close()

def init_db(db_path: Optional[Path] = None):
    """Initialize database tables and run incremental migrations."""
    with get_connection(db_path) as con:
        # Create core tables if not existing
        con.execute("""
        CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_code TEXT UNIQUE,
            family_name TEXT NOT NULL,
            contact_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            donation_amount REAL DEFAULT 10000,
            booking_type TEXT DEFAULT 'Advance',
            preferred_date TEXT,
            status TEXT DEFAULT 'Pending',
            payment_status TEXT DEFAULT 'Not requested',
            priority TEXT DEFAULT 'Normal',
            queue_order INTEGER DEFAULT 0,
            ticket_pdf_path TEXT,
            ticket_number TEXT,
            booked_at TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )""")

        con.execute("""
        CREATE TABLE IF NOT EXISTS pilgrims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            id_proof_type TEXT,
            id_proof_last4 TEXT,
            FOREIGN KEY(family_id) REFERENCES families(id) ON DELETE CASCADE
        )""")

        con.execute("""
        CREATE TABLE IF NOT EXISTS queue_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            family_code TEXT,
            family_name TEXT,
            action TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT,
            old_priority TEXT,
            new_priority TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(family_id) REFERENCES families(id) ON DELETE SET NULL
        )""")

        # Incremental migration: Check if older DB has missing columns in families table
        cursor = con.execute("PRAGMA table_info(families)")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        new_columns = [
            ("email", "TEXT"),
            ("address", "TEXT"),
            ("priority", "TEXT DEFAULT 'Normal'"),
            ("queue_order", "INTEGER DEFAULT 0"),
            ("ticket_pdf_path", "TEXT"),
            ("ticket_number", "TEXT"),
            ("booked_at", "TEXT"),
            ("payment_ref", "TEXT"),
            ("document_status", "TEXT DEFAULT 'Pending Verification'"),
            ("ticket_imported_at", "TEXT"),
            ("ticket_checksum", "TEXT"),
        ]

        for col_name, col_def in new_columns:
            if col_name not in existing_cols:
                con.execute(f"ALTER TABLE families ADD COLUMN {col_name} {col_def};")

        # Schema version migration tracking
        con.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        );
        """)
        
        # Record migration records
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        v_rows = {r["version"] for r in con.execute("SELECT version FROM schema_version").fetchall()}
        
        if 1 not in v_rows:
            con.execute("INSERT INTO schema_version (version, applied_at, description) VALUES (1, ?, 'Initial Core Tables (families, pilgrims)');", (now_str,))
        if 2 not in v_rows:
            con.execute("INSERT INTO schema_version (version, applied_at, description) VALUES (2, ?, 'Phase 2: Queue History, Priority and Extended Fields');", (now_str,))
        if 3 not in v_rows:
            con.execute("INSERT INTO schema_version (version, applied_at, description) VALUES (3, ?, 'Phase 3: Ticket Checksums and Document Readiness');", (now_str,))
        if 4 not in v_rows:
            con.execute("INSERT INTO schema_version (version, applied_at, description) VALUES (4, ?, 'Phase 4: Composite Optimization Indexes & Settings Integration');", (now_str,))

        # Create indices for fast searching and queue sorting
        con.execute("CREATE INDEX IF NOT EXISTS idx_families_code ON families(family_code);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_families_status ON families(status);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_families_priority ON families(priority);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_families_queue_sort ON families(status, priority, queue_order);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_families_phone ON families(phone);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_families_date ON families(preferred_date);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_pilgrims_family_id ON pilgrims(family_id);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_pilgrims_name ON pilgrims(full_name);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_history_family_id ON queue_history(family_id);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_history_created_at ON queue_history(created_at);")
        con.commit()

def get_current_schema_version(db_path: Optional[Path] = None) -> int:
    """Return latest applied database schema version."""
    init_db(db_path)
    with get_connection(db_path) as con:
        row = con.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if (row and row[0] is not None) else 0

def check_database_integrity(db_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Run SQLite PRAGMA integrity_check, quick_check, and foreign_key_check.
    Returns (True, details) if healthy, or (False, issues) if corrupt.
    """
    issues = []
    with get_connection(db_path) as con:
        # 1. PRAGMA integrity_check
        rows = con.execute("PRAGMA integrity_check;").fetchall()
        for r in rows:
            msg = r[0]
            if msg.lower() != "ok":
                issues.append(f"Integrity check issue: {msg}")

        # 2. PRAGMA foreign_key_check
        fk_rows = con.execute("PRAGMA foreign_key_check;").fetchall()
        for r in fk_rows:
            issues.append(f"Foreign key violation: table={r[0]}, rowid={r[1]}, target={r[2]}, fkid={r[3]}")

    if not issues:
        return True, ["Database integrity verified: OK", "Foreign key constraints verified: OK"]
    return False, issues

def get_stats(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculate dashboard statistics."""
    with get_connection(db_path) as con:
        total_families = con.execute("SELECT COUNT(*) FROM families").fetchone()[0]
        pending = con.execute("SELECT COUNT(*) FROM families WHERE status=?", (STATUS_PENDING,)).fetchone()[0]
        in_progress = con.execute("SELECT COUNT(*) FROM families WHERE status=?", (STATUS_IN_PROGRESS,)).fetchone()[0]
        booked = con.execute("SELECT COUNT(*) FROM families WHERE status=?", (STATUS_BOOKED,)).fetchone()[0]
        unavailable = con.execute("SELECT COUNT(*) FROM families WHERE status=?", (STATUS_UNAVAILABLE,)).fetchone()[0]
        cancelled = con.execute("SELECT COUNT(*) FROM families WHERE status=?", (STATUS_CANCELLED,)).fetchone()[0]
        
        total_pilgrims = con.execute("SELECT COUNT(*) FROM pilgrims").fetchone()[0]
        paid_families = con.execute("SELECT COUNT(*) FROM families WHERE payment_status='Paid'").fetchone()[0]
        total_donation = con.execute("SELECT COALESCE(SUM(donation_amount), 0) FROM families").fetchone()[0]
        tickets_attached = con.execute("SELECT COUNT(*) FROM families WHERE ticket_pdf_path IS NOT NULL AND ticket_pdf_path != ''").fetchone()[0]

    return {
        "total_families": total_families,
        "total_pilgrims": total_pilgrims,
        "pending": pending,
        "pending_families": pending,
        "in_progress": in_progress,
        "booked": booked,
        "unavailable": unavailable,
        "cancelled": cancelled,
        "paid_families": paid_families,
        "total_donation": total_donation,
        "tickets_attached": tickets_attached,
    }

def get_family_booking_history(family_id: Optional[int] = None, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Retrieve comprehensive booking history records combining families, pilgrim counts,
    tickets, payment states, and admin activity timestamps.
    """
    query = """
    SELECT
        f.id,
        f.family_code,
        f.family_name,
        f.contact_name,
        f.phone,
        f.status,
        f.payment_status,
        f.payment_ref,
        f.booking_type,
        f.preferred_date,
        f.booked_at,
        f.ticket_pdf_path,
        f.ticket_number,
        f.ticket_imported_at,
        f.created_at,
        (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count
    FROM families f
    """
    params = []
    if family_id:
        query += " WHERE f.id = ?"
        params.append(family_id)
    query += " ORDER BY f.id DESC"
    with get_connection(db_path) as con:
        return [dict(r) for r in con.execute(query, params).fetchall()]

def log_queue_action(
    family_id: Optional[int],
    family_code: str,
    family_name: str,
    action: str,
    old_status: Optional[str] = None,
    new_status: Optional[str] = None,
    old_priority: Optional[str] = None,
    new_priority: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
):
    """Record an audit trail event in queue_history."""
    now_str = datetime.now().isoformat(timespec="seconds")
    with get_connection(db_path) as con:
        con.execute("""
            INSERT INTO queue_history (
                family_id, family_code, family_name, action,
                old_status, new_status, old_priority, new_priority, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            family_id, family_code, family_name, action,
            old_status, new_status, old_priority, new_priority, notes, now_str
        ))
        con.commit()

def get_queue_history(
    family_id: Optional[int] = None,
    limit: int = 100,
    db_path: Optional[Path] = None,
) -> List[sqlite3.Row]:
    """Retrieve queue history events."""
    query = "SELECT * FROM queue_history"
    params: List[Any] = []
    if family_id:
        query += " WHERE family_id = ?"
        params.append(family_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_connection(db_path) as con:
        return con.execute(query, params).fetchall()

def assess_document_readiness(pilgrims: List[sqlite3.Row | Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assess document readiness for a family based on its pilgrim roster.
    Returns readiness status, boolean flag, and missing items detail.
    """
    if not pilgrims:
        return {
            "is_ready": False,
            "status": "No Devotees",
            "details": "Family has no devotees registered",
            "missing_devotees": [],
        }

    missing_devotees = []
    for idx, p in enumerate(pilgrims, start=1):
        name = p.get("full_name") or f"Devotee #{idx}"
        issues = []
        if not p.get("id_proof_type"):
            issues.append("Missing ID Proof Type")
        if not p.get("id_proof_last4"):
            issues.append("Missing ID Last 4")
        if p.get("age") is None:
            issues.append("Missing Age")
        if not p.get("gender"):
            issues.append("Missing Gender")

        if issues:
            missing_devotees.append(f"{name} ({', '.join(issues)})")

    if not missing_devotees:
        return {
            "is_ready": True,
            "status": "Verified Ready",
            "details": f"All {len(pilgrims)} devotee(s) verified with ID proofs",
            "missing_devotees": [],
        }
    else:
        return {
            "is_ready": False,
            "status": "Incomplete",
            "details": f"Incomplete: {len(missing_devotees)} devotee(s) missing documentation",
            "missing_devotees": missing_devotees,
        }

def check_existing_family(
    phone: str,
    family_name: str,
    family_code: Optional[str] = None,
    exclude_id: Optional[int] = None,
    db_path: Optional[Path] = None,
) -> Optional[sqlite3.Row]:
    """
    Check if a family already exists with the same phone, name, or code.
    Used for duplicate prevention.
    """
    clean_phone = phone.strip() if phone else ""
    clean_name = family_name.strip() if family_name else ""
    clean_code = family_code.strip() if family_code else ""

    with get_connection(db_path) as con:
        if clean_code:
            query = "SELECT * FROM families WHERE lower(family_code) = lower(?)"
            params = [clean_code]
            if exclude_id:
                query += " AND id != ?"
                params.append(exclude_id)
            match = con.execute(query, params).fetchone()
            if match:
                return match

        if clean_phone and clean_name:
            query = "SELECT * FROM families WHERE phone = ? AND lower(family_name) = lower(?)"
            params = [clean_phone, clean_name]
            if exclude_id:
                query += " AND id != ?"
                params.append(exclude_id)
            match = con.execute(query, params).fetchone()
            if match:
                return match

        if clean_phone and len(clean_phone) >= 10:
            query = "SELECT * FROM families WHERE phone = ?"
            params = [clean_phone]
            if exclude_id:
                query += " AND id != ?"
                params.append(exclude_id)
            match = con.execute(query, params).fetchone()
            if match:
                return match

    return None

def get_all_families(
    search: str = "",
    status: str = "",
    payment_status: str = "",
    booking_type: str = "",
    priority: str = "",
    sort_by: str = "queue",
    db_path: Optional[Path] = None,
) -> List[sqlite3.Row]:
    """
    Retrieve families matching filters and search term.
    Queue sort puts Urgent > High > Normal > Low, Pending > In Progress > Booked, and queue_order.
    """
    query = """
    SELECT f.*,
           (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count
    FROM families f
    WHERE 1=1
    """
    params: List[Any] = []

    if status and status != "All":
        query += " AND f.status = ?"
        params.append(status)

    if payment_status and payment_status != "All":
        query += " AND f.payment_status = ?"
        params.append(payment_status)

    if booking_type and booking_type != "All":
        query += " AND f.booking_type = ?"
        params.append(booking_type)

    if priority and priority != "All":
        query += " AND f.priority = ?"
        params.append(priority)

    if search:
        search_pattern = f"%{search.strip()}%"
        query += """ AND (
            f.family_code LIKE ? OR
            f.family_name LIKE ? OR
            f.contact_name LIKE ? OR
            f.phone LIKE ? OR
            f.email LIKE ? OR
            EXISTS (SELECT 1 FROM pilgrims p WHERE p.family_id = f.id AND p.full_name LIKE ?)
        )"""
        params.extend([search_pattern] * 6)

    # Sorting
    if sort_by == "queue":
        # Status: Pending=0, In progress=1, Booked/Unavailable/Cancelled=2
        # Priority: Urgent=0, High=1, Normal=2, Low=3
        query += """ ORDER BY
            CASE f.status
                WHEN 'Pending' THEN 0
                WHEN 'In progress' THEN 1
                ELSE 2
            END,
            CASE f.priority
                WHEN 'Urgent' THEN 0
                WHEN 'High' THEN 1
                WHEN 'Normal' THEN 2
                WHEN 'Low' THEN 3
                ELSE 2
            END,
            f.queue_order ASC,
            f.created_at ASC
        """
    elif sort_by == "date_asc":
        query += " ORDER BY f.preferred_date ASC, f.created_at ASC"
    elif sort_by == "date_desc":
        query += " ORDER BY f.preferred_date DESC, f.created_at DESC"
    elif sort_by == "name":
        query += " ORDER BY f.family_name COLLATE NOCASE ASC"
    elif sort_by == "created_desc":
        query += " ORDER BY f.created_at DESC"
    else:
        query += " ORDER BY f.id DESC"

    with get_connection(db_path) as con:
        return con.execute(query, params).fetchall()

def get_family(family_id: int, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Fetch single family by ID."""
    with get_connection(db_path) as con:
        return con.execute("SELECT * FROM families WHERE id = ?", (family_id,)).fetchone()

def get_family_by_code(family_code: str, db_path: Optional[Path] = None) -> Optional[sqlite3.Row]:
    """Fetch single family by family_code."""
    with get_connection(db_path) as con:
        return con.execute("SELECT * FROM families WHERE family_code = ?", (family_code,)).fetchone()

def get_family_pilgrims(family_id: int, db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    """Fetch all pilgrims belonging to a family, ordered by ID."""
    with get_connection(db_path) as con:
        return con.execute("SELECT * FROM pilgrims WHERE family_id = ? ORDER BY id ASC", (family_id,)).fetchall()

def add_family_with_pilgrims(
    family_data: Dict[str, Any],
    pilgrims_data: List[Dict[str, Any]],
    db_path: Optional[Path] = None,
) -> int:
    """
    Atomically insert family and its multiple pilgrims.
    Returns the new family ID.
    """
    created_at = family_data.get("created_at") or datetime.now().isoformat(timespec="seconds")
    code = family_data.get("family_code") or f"FAM-{datetime.now():%y%m%d%H%M%S}-{uuid.uuid4().hex[:4].upper()}"
    
    with get_connection(db_path) as con:
        cur = con.execute("""
            INSERT INTO families (
                family_code, family_name, contact_name, phone, email, address,
                donation_amount, booking_type, preferred_date, status, payment_status,
                priority, queue_order, ticket_pdf_path, ticket_number, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            code,
            family_data["family_name"],
            family_data.get("contact_name", ""),
            family_data.get("phone", ""),
            family_data.get("email", ""),
            family_data.get("address", ""),
            family_data.get("donation_amount", 10000.0),
            family_data.get("booking_type", BOOKING_TYPE_ADVANCE),
            family_data.get("preferred_date", ""),
            family_data.get("status", STATUS_PENDING),
            family_data.get("payment_status", PAYMENT_NOT_REQUESTED),
            family_data.get("priority", PRIORITY_NORMAL),
            family_data.get("queue_order", 0),
            family_data.get("ticket_pdf_path", ""),
            family_data.get("ticket_number", ""),
            family_data.get("notes", ""),
            created_at,
        ))
        family_id = cur.lastrowid

        for p in pilgrims_data:
            if not p.get("full_name"):
                continue
            con.execute("""
                INSERT INTO pilgrims (
                    family_id, full_name, age, gender, id_proof_type, id_proof_last4
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                family_id,
                p["full_name"],
                p.get("age"),
                p.get("gender", ""),
                p.get("id_proof_type", ""),
                p.get("id_proof_last4", ""),
            ))

        # Log creation in queue history
        con.execute("""
            INSERT INTO queue_history (
                family_id, family_code, family_name, action,
                old_status, new_status, old_priority, new_priority, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            family_id, code, family_data["family_name"], "FAMILY_CREATED",
            None, family_data.get("status", STATUS_PENDING),
            None, family_data.get("priority", PRIORITY_NORMAL),
            f"Created with {len(pilgrims_data)} devotee(s)",
            created_at,
        ))

        con.commit()
        return family_id

def update_family(
    family_id: int,
    family_data: Dict[str, Any],
    db_path: Optional[Path] = None,
):
    """Update family details."""
    fields = [
        "family_name", "contact_name", "phone", "email", "address",
        "donation_amount", "booking_type", "preferred_date",
        "status", "payment_status", "priority", "notes",
        "ticket_pdf_path", "ticket_number", "booked_at",
        "payment_ref", "document_status", "ticket_imported_at", "ticket_checksum"
    ]
    updates = []
    values = []
    for f in fields:
        if f in family_data:
            updates.append(f"{f} = ?")
            values.append(family_data[f])

    if not updates:
        return

    values.append(family_id)
    with get_connection(db_path) as con:
        con.execute(f"UPDATE families SET {', '.join(updates)} WHERE id = ?", values)
        con.commit()

def delete_family(family_id: int, db_path: Optional[Path] = None):
    """Delete a family and all associated pilgrims (cascades)."""
    with get_connection(db_path) as con:
        fam = con.execute("SELECT * FROM families WHERE id = ?", (family_id,)).fetchone()
        if fam:
            con.execute("""
                INSERT INTO queue_history (
                    family_id, family_code, family_name, action,
                    old_status, new_status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                family_id, fam["family_code"], fam["family_name"], "FAMILY_DELETED",
                fam["status"], "Deleted", "Family record removed by admin",
                datetime.now().isoformat(timespec="seconds")
            ))
        con.execute("DELETE FROM families WHERE id = ?", (family_id,))
        con.commit()

def add_pilgrim(
    family_id: int,
    pilgrim_data: Dict[str, Any],
    db_path: Optional[Path] = None,
) -> int:
    """Add a single pilgrim to an existing family."""
    with get_connection(db_path) as con:
        cur = con.execute("""
            INSERT INTO pilgrims (family_id, full_name, age, gender, id_proof_type, id_proof_last4)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            family_id,
            pilgrim_data["full_name"],
            pilgrim_data.get("age"),
            pilgrim_data.get("gender", ""),
            pilgrim_data.get("id_proof_type", ""),
            pilgrim_data.get("id_proof_last4", ""),
        ))
        con.commit()
        return cur.lastrowid

def update_pilgrim(
    pilgrim_id: int,
    pilgrim_data: Dict[str, Any],
    db_path: Optional[Path] = None,
):
    """Update a pilgrim's details."""
    with get_connection(db_path) as con:
        con.execute("""
            UPDATE pilgrims
            SET full_name = ?, age = ?, gender = ?, id_proof_type = ?, id_proof_last4 = ?
            WHERE id = ?
        """, (
            pilgrim_data["full_name"],
            pilgrim_data.get("age"),
            pilgrim_data.get("gender", ""),
            pilgrim_data.get("id_proof_type", ""),
            pilgrim_data.get("id_proof_last4", ""),
            pilgrim_id,
        ))
        con.commit()

def delete_pilgrim(pilgrim_id: int, db_path: Optional[Path] = None):
    """Delete a pilgrim."""
    with get_connection(db_path) as con:
        con.execute("DELETE FROM pilgrims WHERE id = ?", (pilgrim_id,))
        con.commit()

def update_status_and_payment(
    family_id: int,
    status: str,
    payment_status: str,
    notes: Optional[str] = None,
    payment_ref: Optional[str] = None,
    document_status: Optional[str] = None,
    db_path: Optional[Path] = None,
):
    """Quick update for booking & payment status with audit history."""
    booked_at = datetime.now().isoformat(timespec="seconds") if status == STATUS_BOOKED else None
    now_str = datetime.now().isoformat(timespec="seconds")
    with get_connection(db_path) as con:
        old_fam = con.execute("SELECT * FROM families WHERE id = ?", (family_id,)).fetchone()
        old_status = old_fam["status"] if old_fam else None
        old_payment = old_fam["payment_status"] if old_fam else None
        curr_pref = payment_ref if payment_ref is not None else (old_fam["payment_ref"] if old_fam else None)
        curr_doc = document_status if document_status is not None else (old_fam["document_status"] if old_fam else None)

        updates = ["status = ?", "payment_status = ?", "payment_ref = ?", "document_status = ?"]
        params = [status, payment_status, curr_pref, curr_doc]

        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)

        if status == STATUS_BOOKED:
            updates.append("booked_at = CASE WHEN (booked_at IS NULL OR booked_at = '') THEN ? ELSE booked_at END")
            params.append(booked_at)

        params.append(family_id)
        con.execute(f"UPDATE families SET {', '.join(updates)} WHERE id = ?", params)

        if old_fam:
            audit_notes = f"Payment: {old_payment} -> {payment_status}."
            if payment_ref:
                audit_notes += f" Ref: {payment_ref}."
            if notes:
                audit_notes += f" Notes: {notes}."
            con.execute("""
                INSERT INTO queue_history (
                    family_id, family_code, family_name, action,
                    old_status, new_status, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                family_id, old_fam["family_code"], old_fam["family_name"],
                "STATUS_UPDATED", old_status, status,
                audit_notes,
                now_str,
            ))
        con.commit()

def set_priority(family_id: int, priority: str, db_path: Optional[Path] = None):
    """Set queue priority for a family and record in history."""
    now_str = datetime.now().isoformat(timespec="seconds")
    with get_connection(db_path) as con:
        old_fam = con.execute("SELECT * FROM families WHERE id = ?", (family_id,)).fetchone()
        old_priority = old_fam["priority"] if old_fam else None

        con.execute("UPDATE families SET priority = ? WHERE id = ?", (priority, family_id))

        if old_fam and old_priority != priority:
            con.execute("""
                INSERT INTO queue_history (
                    family_id, family_code, family_name, action,
                    old_priority, new_priority, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                family_id, old_fam["family_code"], old_fam["family_name"],
                "PRIORITY_CHANGED", old_priority, priority,
                f"Priority changed from {old_priority} to {priority}",
                now_str,
            ))
        con.commit()

def shift_queue_order(family_id: int, direction: str, db_path: Optional[Path] = None):
    """
    Move family up or down in queue relative to adjacent family.
    direction: 'up' or 'down'
    """
    families = get_all_families(sort_by="queue", db_path=db_path)
    ids = [f["id"] for f in families]
    if family_id not in ids:
        return
    idx = ids.index(family_id)
    target_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= target_idx < len(ids):
        other_id = ids[target_idx]
        with get_connection(db_path) as con:
            # Swap queue_order values or re-index
            for rank, fid in enumerate(ids):
                con.execute("UPDATE families SET queue_order = ? WHERE id = ?", (rank, fid))
            # Swap the two
            con.execute("UPDATE families SET queue_order = ? WHERE id = ?", (target_idx, family_id))
            con.execute("UPDATE families SET queue_order = ? WHERE id = ?", (idx, other_id))
            con.commit()
