"""
Tests for Phase 6 Commercial Launch and Client Operations.
Validates:
- Client onboarding environment verification
- License expiry & renewal notification alerts
- License certificate export & hardware transfer deactivation
- Safe pre-update backups & migration rollback on error
- Non-PII diagnostic report generation & log scrubbing
- Version consistency & commercial support integration
"""
import pytest
import sqlite3
import datetime
from pathlib import Path

from config import DB_PATH, DATA_DIR, TICKETS_DIR, BACKUPS_DIR
from database import (
    init_db,
    get_connection,
    add_family_with_pilgrims,
    get_current_schema_version,
)
from auth import init_auth_db, create_admin_user
from licensing import (
    init_licensing_db,
    get_installation_id,
    generate_license_key,
    activate_license,
    activate_trial_license,
    get_license_info,
    export_license_certificate,
    deactivate_license_for_transfer,
)
from client_verification import (
    initialize_environment,
    run_full_client_verification,
    format_verification_report,
)
from update_manager import (
    prepare_pre_update_backup,
    validate_database_schema,
    execute_safe_migration,
    rollback_database,
    get_migration_history,
)
from support_diagnostics import (
    generate_diagnostic_report,
    export_diagnostic_report,
    _sanitize_log_line,
    APP_VERSION,
)
from settings import init_settings, get_setting, set_setting


@pytest.fixture
def phase6_db(tmp_path):
    """Provide a fresh isolated database with full Phase 6 initialization."""
    db_file = tmp_path / "test_phase6.db"
    init_db(db_file)
    init_auth_db(db_file)
    init_settings(db_file)
    init_licensing_db(db_file)
    create_admin_user("admin6", "Phase6Admin#2026", "Phase6 Administrator", db_path=db_file)
    return db_file


def test_client_verification_suite(phase6_db, tmp_path):
    """Verify that client onboarding verification checks pass on a properly initialized setup."""
    t_dir = tmp_path / "tickets"
    b_dir = tmp_path / "backups"
    t_dir.mkdir()
    b_dir.mkdir()

    results = run_full_client_verification(
        db_path=phase6_db,
        tickets_dir=t_dir,
        backups_dir=b_dir,
        auto_init=True,
    )

    assert results["all_passed"] is True
    assert len(results["critical_errors"]) == 0
    assert "ALL SYSTEMS OPERATIONAL" in results["summary"] or "READY" in results["summary"]

    report = format_verification_report(results)
    assert "SRIVANI BOOKING MANAGER" in report
    assert "Database Integrity Check" in report
    assert "Database Schema Structure" in report
    assert "Administrator Account Setup" in report


def test_license_warning_and_expiry_notification(phase6_db):
    """Test renewal & warning notifications when trial/license is expiring soon or expired."""
    inst_id = get_installation_id()
    client = "Acme Travels"

    # 1. Active license with 5 days remaining -> should trigger is_warning_period
    exp_date = (datetime.date.today() + datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    key = generate_license_key(client, inst_id, exp_date, "COMMERCIAL")
    ok, _ = activate_license(key, client, expiry_date=exp_date, db_path=phase6_db)
    assert ok is True

    info = get_license_info(phase6_db)
    assert info["is_licensed"] is True
    assert info["days_remaining"] == 5
    assert info["is_warning_period"] is True
    assert "5 day(s) remaining" in info["warning_message"]

    # 2. Expired license -> should trigger is_expired
    past_date = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    with get_connection(phase6_db) as con:
        con.execute("UPDATE license_info SET expiry_date = ? WHERE status = 'ACTIVE'", (past_date,))
        con.commit()

    exp_info = get_license_info(phase6_db)
    assert exp_info["is_licensed"] is False
    assert exp_info["is_expired"] is True
    assert exp_info["status"] == "EXPIRED"
    assert "expired on" in exp_info["warning_message"]


def test_license_certificate_export_and_deactivation(phase6_db, tmp_path):
    """Test exporting plain-text certificate and deactivating for device transfer."""
    inst_id = get_installation_id()
    client = "Devotee Trust"
    activate_trial_license(client, days=30, db_path=phase6_db)

    # Export Certificate
    cert_file = tmp_path / "license_cert.txt"
    out_path = export_license_certificate(cert_file, db_path=phase6_db)
    assert out_path.exists()
    content = cert_file.read_text(encoding="utf-8")
    assert client in content
    assert inst_id in content
    assert "LICENSE CONDITIONS" in content

    # Deactivate for Transfer
    ok, msg, details = deactivate_license_for_transfer(phase6_db)
    assert ok is True
    assert "DEACT-" in details["deactivation_proof"]
    assert details["client_name"] == client

    # Confirm status is TRANSFERRED
    info = get_license_info(phase6_db)
    assert info["status"] == "UNLICENSED" or info["is_licensed"] is False


def test_pre_update_backup_and_validation(phase6_db, tmp_path):
    """Test safe pre-update atomic snapshot and schema validation."""
    backup_dir = tmp_path / "pre_update_backups"
    snapshot = prepare_pre_update_backup(db_path=phase6_db, backup_dir=backup_dir)

    assert snapshot.exists()
    assert snapshot.stat().st_size > 0
    assert "srivani_pre_update_" in snapshot.name

    # Validate schema
    is_valid, reason, meta = validate_database_schema(phase6_db)
    assert is_valid is True
    assert meta["integrity"] == "ok"
    assert "families" in meta["tables"]


def test_safe_migration_and_rollback_on_error(phase6_db):
    """Test that safe migration runs within transaction and rolls back on failure."""
    orig_ver = get_current_schema_version(phase6_db)

    # 1. Successful migration
    def migration_success(con):
        con.execute("CREATE TABLE test_extension (id INTEGER PRIMARY KEY, note TEXT);")
        con.execute("INSERT INTO test_extension (note) VALUES ('Phase6 ready');")

    ok, msg = execute_safe_migration(99, "Test Safe Extension", migration_success, db_path=phase6_db)
    assert ok is True
    assert get_current_schema_version(phase6_db) == 99

    with get_connection(phase6_db) as con:
        r = con.execute("SELECT note FROM test_extension").fetchone()
        assert r["note"] == "Phase6 ready"

    # 2. Failing migration -> must roll back and preserve schema
    def migration_fail(con):
        con.execute("CREATE TABLE should_be_rolled_back (id INTEGER);")
        # Deliberate SQL error to trigger failure
        con.execute("INSERT INTO non_existent_table_xyz VALUES (1, 2, 3);")

    fail_ok, fail_msg = execute_safe_migration(100, "Faulty Migration", migration_fail, db_path=phase6_db)
    assert fail_ok is False
    assert "Migration failed and was safely rolled back" in fail_msg

    # Verify table does NOT exist and version is still 99
    assert get_current_schema_version(phase6_db) == 99
    with get_connection(phase6_db) as con:
        cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='should_be_rolled_back'")
        assert cur.fetchone() is None


def test_diagnostic_report_no_pii(phase6_db, tmp_path):
    """Verify that customer support diagnostic report excludes ALL sensitive personal details."""
    # Insert realistic donor and pilgrim
    fam_data = {
        "family_name": "Sharma VIP Family",
        "contact_name": "Ramesh Sharma",
        "phone": "9876543210",
        "donation_amount": 20000,
        "booking_type": "Current",
        "preferred_date": "2026-12-25",
    }
    pilgrims = [
        {"full_name": "Ramesh Sharma", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Sita Sharma", "age": 42, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]
    fam_id = add_family_with_pilgrims(fam_data, pilgrims, db_path=phase6_db)
    assert fam_id is not None

    # Generate diagnostic report
    report = generate_diagnostic_report(db_path=phase6_db)

    # CRITICAL: Verify NO PII leaked
    assert "Ramesh Sharma" not in report
    assert "Sita Sharma" not in report
    assert "Sharma VIP Family" not in report
    assert "9876543210" not in report

    # Verify aggregate count is reported
    assert "Total Family Records: 1" in report
    assert "Total Devotees:       2" in report
    assert "Integrity Status:     OK / Healthy" in report

    # Test file export
    diag_file = tmp_path / "diag.txt"
    export_diagnostic_report(diag_file, db_path=phase6_db)
    assert diag_file.exists()


def test_log_sanitization():
    """Verify regex scrubbing of phones, Aadhaar, and credentials in log tail."""
    raw_log = "User logged in with phone 9876543210 and Aadhaar 1234 5678 9012, email user@example.com, password=SecretPassword123"
    sanitized = _sanitize_log_line(raw_log)

    assert "9876543210" not in sanitized
    assert "[REDACTED-PHONE]" in sanitized
    assert "1234 5678 9012" not in sanitized
    assert "[REDACTED-ID-PROOF]" in sanitized
    assert "user@example.com" not in sanitized
    assert "[REDACTED-EMAIL]" in sanitized
    assert "SecretPassword123" not in sanitized
    assert "[REDACTED]" in sanitized
