"""
SRIVANI BOOKING MANAGER - Phase 5 Commercial Release Tests
Tests: Installation ID generation, Offline Cryptographic Licensing,
Trial Activation, Machine Binding, License Recovery,
First-Run Wizard Configuration Persistence, and Data Isolation.
"""
import pytest
from pathlib import Path
import datetime

from database import init_db, get_connection
from auth import init_auth_db, create_admin_user, authenticate_admin
from settings import init_settings, get_setting, set_setting, APP_VERSION
from licensing import (
    init_licensing_db,
    get_installation_id,
    generate_license_key,
    verify_license_key,
    activate_license,
    activate_trial_license,
    get_license_info,
    is_licensed,
    recover_license_details,
)
import config

@pytest.fixture
def test_db(tmp_path):
    """Isolated database fixture for Phase 5 release testing."""
    db_file = tmp_path / "test_phase5.db"
    init_db(db_file)
    init_auth_db(db_file)
    init_settings(db_file)
    init_licensing_db(db_file)
    return db_file

def test_installation_id_format_and_stability():
    """Verify that Installation ID is formatted as SRVN-XXXX-XXXX-XXXX and stable."""
    id1 = get_installation_id()
    id2 = get_installation_id()

    assert id1.startswith("SRVN-")
    assert len(id1) == 19  # SRVN-XXXX-XXXX-XXXX (4 + 1 + 4 + 1 + 4 + 1 + 4 = 19)
    assert id1 == id2  # Deterministic on same host

def test_license_key_generation_and_machine_binding():
    """Test generating and verifying machine-bound and site-wide license keys."""
    client = "Tirumala Devotee Services"
    inst_id = get_installation_id()

    # 1. Machine-bound commercial key
    key_bound = generate_license_key(client, inst_id, "PERPETUAL", "COMMERCIAL")
    assert key_bound.startswith("SRVN-")
    assert len(key_bound) == 24  # SRVN-XXXX-XXXX-XXXX-XXXX

    ok, msg, details = verify_license_key(key_bound, client, inst_id, "PERPETUAL", "COMMERCIAL")
    assert ok is True
    assert details["is_machine_bound"] is True
    assert details["client_name"] == client.upper()

    # 2. Key rejected on mismatched client name
    ok_bad_client, _, _ = verify_license_key(key_bound, "Different Client Name", inst_id)
    assert ok_bad_client is False

    # 3. Key rejected on mismatched machine ID
    ok_bad_machine, _, _ = verify_license_key(key_bound, client, "SRVN-9999-8888-7777")
    assert ok_bad_machine is False

    # 4. Multi-seat (ANY) commercial key
    key_any = generate_license_key(client, "ANY", "PERPETUAL", "COMMERCIAL")
    ok_any, _, details_any = verify_license_key(key_any, client, inst_id)
    assert ok_any is True
    assert details_any["is_machine_bound"] is False

def test_license_activation_and_sqlite_persistence(test_db):
    """Test full activation workflow and SQLite license state retrieval."""
    client = "Sri Venkateswara Seva Trust"
    inst_id = get_installation_id()
    key = generate_license_key(client, inst_id, "PERPETUAL", "COMMERCIAL")

    # Initial state should be unlicensed
    initial_info = get_license_info(test_db)
    assert initial_info["status"] == "UNLICENSED"
    assert is_licensed(test_db) is False

    # Activate license
    ok_act, msg_act = activate_license(key, client, db_path=test_db)
    assert ok_act is True

    # Verify active status
    info = get_license_info(test_db)
    assert info["is_licensed"] is True
    assert info["status"] == "ACTIVE"
    assert info["license_type"] == "COMMERCIAL"
    assert info["client_name"] == client.upper()
    assert info["expiry_date"] == "PERPETUAL"
    assert is_licensed(test_db) is True

def test_trial_license_activation(test_db):
    """Test 30-day evaluation trial activation."""
    ok_trial, msg_trial = activate_trial_license("Trial User", days=30, db_path=test_db)
    assert ok_trial is True
    assert "30 days" in msg_trial

    info = get_license_info(test_db)
    assert info["is_licensed"] is True
    assert info["status"] == "ACTIVE"
    assert info["license_type"] == "TRIAL"
    assert info["days_remaining"] >= 29
    assert info["is_expired"] is False

def test_license_recovery(test_db):
    """Test retrieving license information for disaster recovery."""
    client = "Recovery Test Client"
    key = generate_license_key(client, "ANY", "PERPETUAL", "COMMERCIAL")
    activate_license(key, client, db_path=test_db)

    rec = recover_license_details(test_db)
    assert rec is not None
    assert rec["client_name"] == client.upper()
    assert rec["license_key"] == key

def test_first_run_configuration_persistence(test_db, tmp_path):
    """Test configuration variables created during setup wizard."""
    custom_data = tmp_path / "custom_data"
    custom_tickets = tmp_path / "custom_tickets"
    custom_backups = tmp_path / "custom_backups"

    custom_data.mkdir()
    custom_tickets.mkdir()
    custom_backups.mkdir()

    # Save wizard settings
    set_setting("ticket_dir", str(custom_tickets), test_db)
    set_setting("backup_dir", str(custom_backups), test_db)
    set_setting("export_dir", str(custom_data / "exports"), test_db)
    set_setting("first_run_completed", "true", test_db)

    # Create admin
    ok_admin, _ = create_admin_user("wizardadmin", "WizardPass#2026", "Wizard Admin", db_path=test_db)
    assert ok_admin is True

    # Verify settings retrieved
    assert get_setting("ticket_dir", db_path=test_db) == str(custom_tickets)
    assert get_setting("backup_dir", db_path=test_db) == str(custom_backups)
    assert get_setting("first_run_completed", db_path=test_db) == "true"

    # Verify admin authenticates
    ok_auth, _, u = authenticate_admin("wizardadmin", "WizardPass#2026", db_path=test_db)
    assert ok_auth is True
    assert u["display_name"] == "Wizard Admin"

def test_application_version_consistency():
    """Verify application version is consistent (v5.0.0, v6.0.0, v7.0.0, or v7.1.0)."""
    assert APP_VERSION in ("5.0.0", "6.0.0", "7.0.0", "7.1.0")
