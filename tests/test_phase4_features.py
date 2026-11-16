"""
SRIVANI BOOKING MANAGER - Phase 4 Comprehensive Unit & Integration Tests
Tests: Admin Authentication, Bcrypt Hashing, Lockout Protection,
Settings Persistence, Database Integrity & Migrations,
Advanced Reports (Weekly, Monthly, Status Summary), Total Reconciliation,
and Printable PDF Generation.
"""
import pytest
from pathlib import Path
import sqlite3

from database import (
    init_db,
    get_connection,
    add_family_with_pilgrims,
    update_status_and_payment,
    check_database_integrity,
    get_current_schema_version,
)
from auth import (
    init_auth_db,
    hash_password,
    verify_password,
    has_admin_user,
    create_admin_user,
    authenticate_admin,
    change_admin_password,
    update_admin_profile,
    session,
    MAX_FAILED_ATTEMPTS,
)
from settings import (
    init_settings,
    get_setting,
    set_setting,
    get_all_settings,
    DEFAULT_SETTINGS,
)
from reports import (
    get_weekly_report,
    get_monthly_report,
    get_booking_status_summary_report,
    validate_report_totals,
    export_report_to_csv,
    generate_printable_pdf_report,
)
from themes import get_theme_palette, get_current_theme_name

@pytest.fixture
def test_db(tmp_path):
    """Fixture providing a fresh isolated database path for Phase 4 testing."""
    db_file = tmp_path / "test_phase4.db"
    init_db(db_file)
    init_auth_db(db_file)
    init_settings(db_file)
    return db_file

def test_password_hashing():
    """Test bcrypt hashing and verification correctness."""
    pwd = "SecureMasterPassword#2026"
    h = hash_password(pwd)
    assert h != pwd
    assert h.startswith("$2b$") or h.startswith("$2a$")
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPassword", h) is False

def test_admin_creation_and_lockout(test_db):
    """Test administrator creation, authentication, and lockout after repeated failures."""
    assert has_admin_user(test_db) is False

    # Create admin
    ok, msg = create_admin_user("superadmin", "AdminPass123", "Primary Admin", db_path=test_db)
    assert ok is True
    assert has_admin_user(test_db) is True

    # Duplicate creation rejected
    ok2, msg2 = create_admin_user("superadmin", "AnotherPass123", db_path=test_db)
    assert ok2 is False
    assert "already exists" in msg2

    # Successful login
    ok_auth, msg_auth, user = authenticate_admin("superadmin", "AdminPass123", db_path=test_db)
    assert ok_auth is True
    assert user is not None
    assert user["username"] == "superadmin"
    assert user["display_name"] == "Primary Admin"

    # Repeated failures leading to lockout
    for _ in range(MAX_FAILED_ATTEMPTS):
        ok_fail, msg_fail, _ = authenticate_admin("superadmin", "WrongGuess", db_path=test_db)
        assert ok_fail is False

    # Locked out attempt
    ok_locked, msg_locked, _ = authenticate_admin("superadmin", "AdminPass123", db_path=test_db)
    assert ok_locked is False
    assert "locked" in msg_locked.lower()

def test_admin_change_password_and_profile(test_db):
    """Test password update and profile name update."""
    create_admin_user("admin", "Initial123", db_path=test_db)

    # Change password failure on bad old password
    ok, msg = change_admin_password("admin", "IncorrectOld", "NewMaster456", db_path=test_db)
    assert ok is False
    assert "incorrect" in msg.lower()

    # Change password success
    ok_succ, msg_succ = change_admin_password("admin", "Initial123", "NewMaster456", db_path=test_db)
    assert ok_succ is True

    # Authenticate with new password
    ok_new, _, user = authenticate_admin("admin", "NewMaster456", db_path=test_db)
    assert ok_new is True

    # Update profile
    ok_prof, _ = update_admin_profile("admin", "Chief Manager", db_path=test_db)
    assert ok_prof is True
    ok_auth, _, u = authenticate_admin("admin", "NewMaster456", db_path=test_db)
    assert u["display_name"] == "Chief Manager"

def test_session_state_transitions():
    """Test session login, lock, unlock, and logout transitions."""
    sess = session
    sess.logout()
    assert sess.is_authenticated is False
    assert sess.is_locked is False

    sess.login({"id": 1, "username": "admin", "display_name": "SysAdmin"})
    assert sess.is_authenticated is True
    assert sess.is_locked is False
    assert sess.username == "admin"
    assert sess.display_name == "SysAdmin"

    sess.lock()
    assert sess.is_authenticated is True
    assert sess.is_locked is True

    sess.unlock({"id": 1, "username": "admin", "display_name": "SysAdmin"})
    assert sess.is_locked is False

    sess.logout()
    assert sess.is_authenticated is False

def test_settings_persistence(test_db):
    """Test reading, writing, and defaults in app_settings table."""
    all_s = get_all_settings(test_db)
    assert all_s["theme"] == "light"
    assert all_s["auto_backup"] == "true"

    # Modify settings
    set_setting("theme", "dark", test_db)
    set_setting("session_lock_minutes", "45", test_db)

    assert get_setting("theme", db_path=test_db) == "dark"
    assert get_setting("session_lock_minutes", db_path=test_db) == "45"

def test_database_integrity_and_schema_version(test_db):
    """Test database integrity verification and schema migration version tracking."""
    is_healthy, messages = check_database_integrity(test_db)
    assert is_healthy is True
    assert len(messages) >= 2

    v = get_current_schema_version(test_db)
    assert v >= 4

def test_weekly_monthly_and_status_reports(test_db):
    """Test weekly, monthly, and booking status aggregated operational reports."""
    # Add sample families
    f1 = {
        "family_name": "Rao Family",
        "contact_name": "Srinivas Rao",
        "phone": "9876543210",
        "booking_type": "Advance",
        "donation_amount": 20000,
    }
    p1 = [
        {"full_name": "Srinivas Rao", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Lalitha Rao", "age": 42, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]
    f1_id = add_family_with_pilgrims(f1, p1, db_path=test_db)
    update_status_and_payment(f1_id, "Booked", "Paid", notes="Manual TTD Portal success", payment_ref="TXN-1001", db_path=test_db)

    f2 = {
        "family_name": "Sharma Family",
        "contact_name": "Amit Sharma",
        "phone": "9123456789",
        "booking_type": "Current",
        "donation_amount": 10000,
    }
    p2 = [
        {"full_name": "Amit Sharma", "age": 35, "gender": "Male", "id_proof_type": "Voter ID", "id_proof_last4": "9999"}
    ]
    add_family_with_pilgrims(f2, p2, db_path=test_db)

    # 1. Weekly report
    w_rows = get_weekly_report(test_db)
    assert len(w_rows) >= 1
    assert any(r["booked_families"] == 1 for r in w_rows)

    # 2. Monthly report
    m_rows = get_monthly_report(test_db)
    assert len(m_rows) >= 1
    assert any(r["booked_families"] == 1 for r in m_rows)

    # 3. Status summary report
    st_rows = get_booking_status_summary_report(test_db)
    st_map = {r["status"]: r["family_count"] for r in st_rows}
    assert st_map.get("Booked") == 1
    assert st_map.get("Pending") == 1

def test_validate_report_totals(test_db):
    """Test totals reconciliation against underlying tables."""
    recon_empty = validate_report_totals(test_db)
    assert recon_empty["is_valid"] is True
    assert recon_empty["total_families"] == 0
    assert recon_empty["total_pilgrims"] == 0

    # Insert family
    f = {
        "family_name": "Verma Family",
        "contact_name": "Sunil Verma",
        "phone": "9811122233",
        "donation_amount": 30000,
    }
    p = [
        {"full_name": "Sunil Verma", "age": 40, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1111"},
        {"full_name": "Anita Verma", "age": 38, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "2222"},
        {"full_name": "Rahul Verma", "age": 12, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "3333"},
    ]
    add_family_with_pilgrims(f, p, db_path=test_db)

    recon = validate_report_totals(test_db)
    assert recon["is_valid"] is True
    assert recon["total_families"] == 1
    assert recon["total_pilgrims"] == 3
    assert recon["total_donation"] == 30000
    assert recon["orphaned_pilgrims"] == 0
    assert len(recon["anomalies"]) == 0

def test_printable_pdf_reports(test_db, tmp_path):
    """Test generating printable executive PDF reports using ReportLab."""
    f = {
        "family_name": "Gupta Family",
        "contact_name": "Rajesh Gupta",
        "phone": "9844455566",
        "donation_amount": 10000,
    }
    p = [
        {"full_name": "Rajesh Gupta", "age": 50, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "4444"}
    ]
    fid = add_family_with_pilgrims(f, p, db_path=test_db)
    update_status_and_payment(fid, "Booked", "Paid", db_path=test_db)

    report_types = [
        "daily_completed",
        "weekly",
        "monthly",
        "booking_status_summary",
        "pending_families",
        "payment_status",
    ]

    for rt in report_types:
        pdf_file = tmp_path / f"report_{rt}.pdf"
        ok, path_or_err = generate_printable_pdf_report(rt, pdf_file, db_path=test_db)
        assert ok is True, f"Failed for {rt}: {path_or_err}"
        assert pdf_file.exists()
        assert pdf_file.stat().st_size > 1000  # Generated valid non-empty PDF

def test_theming_palettes():
    """Test light and dark theme palette definitions and contrast keys."""
    light = get_theme_palette("light")
    dark = get_theme_palette("dark")

    for key in ["bg_app", "bg_card", "bg_sidebar", "fg_text", "primary", "border"]:
        assert key in light
        assert key in dark
        assert light[key].startswith("#")
        assert dark[key].startswith("#")
