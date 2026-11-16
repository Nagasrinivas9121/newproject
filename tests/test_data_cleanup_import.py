"""
SRIVANI BOOKING MANAGER - Phase 10 Automated Test Suite
Testing:
1. Data Cleanup & Mock Data Removal Engine
2. Universal Dataset Import & Column Mapping Engine
3. Validation Engine & Error Reporting
4. 3-Way Duplicate Handling (SKIP, UPDATE, CANCEL)
5. Transactional Rollback & Integrity Guarantees
6. Large Dataset Ingestion
7. Import History Logging
8. Clean Empty Database Experience & Zero Calculations
9. Preservation of Real Records, User Accounts & Settings
10. Prevention of Mock Data Seeding on Startup
"""

import os
import csv
import tempfile
import pytest
from pathlib import Path
import openpyxl

from config import (
    DB_PATH,
    STATUS_PENDING,
    STATUS_BOOKED,
    PAYMENT_PAID,
    PAYMENT_NOT_REQUESTED,
)
from database import (
    init_db,
    get_connection,
    get_stats,
    get_all_families,
    get_family_pilgrims,
    get_import_batches,
    get_import_batch,
    get_cleanup_audits,
    get_current_schema_version,
)
from auth import init_auth_db, create_admin_user, authenticate_admin
from settings import init_settings, get_setting, set_setting
from data_cleanup import scan_for_mock_data, cleanup_mock_data
from dataset_importer import (
    read_dataset_file,
    detect_column_mapping,
    validate_and_analyze_dataset,
    execute_dataset_import,
    export_validation_report_csv,
    DUP_POLICY_SKIP,
    DUP_POLICY_UPDATE,
    DUP_POLICY_CANCEL,
)


@pytest.fixture
def isolated_env():
    """Create a completely isolated test environment with fresh SQLite database."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        db_file = root / "isolated_srivani.db"
        init_db(db_file)
        init_auth_db(db_file)
        init_settings(db_file)
        yield {
            "root": root,
            "db_path": db_file,
        }


# =========================================================================
# TEST 1: CSV IMPORT WITH CUSTOM HEADERS & COLUMN MAPPING
# =========================================================================

def test_01_csv_import_with_custom_headers(isolated_env):
    db = isolated_env["db_path"]
    csv_file = isolated_env["root"] / "devotees.csv"

    # CSV with realistic non-standard custom column headers
    csv_file.write_text(
        "Household Name,Yatri Full Name,Contact Mobile,Devotee Age,Gender,ID Document,ID Reference,Contribution\n"
        "Tirupati Seva Trust,Sri Krishna Murthy,9849012345,54,Male,Aadhaar,4321,20000\n"
        "Tirupati Seva Trust,Rukmini Murthy,9849012345,50,Female,Aadhaar,8765,20000\n"
        "Chennai Darshan Samithi,Senthil Kumar,9840011223,42,Male,Passport,Z102,10000\n",
        encoding="utf-8",
    )

    headers, rows, size, fmt = read_dataset_file(csv_file)
    assert len(headers) == 8
    assert len(rows) == 3
    assert fmt == "CSV"

    # Verify auto-mapping handles custom aliases
    mapping = detect_column_mapping(headers)
    assert mapping["Household Name"] == "family_name"
    assert mapping["Yatri Full Name"] == "full_name"
    assert mapping["Contact Mobile"] == "phone"
    assert mapping["Devotee Age"] == "age"
    assert mapping["Gender"] == "gender"
    assert mapping["ID Document"] == "id_proof_type"
    assert mapping["ID Reference"] == "id_proof_last4"
    assert mapping["Contribution"] == "donation_amount"

    # Analyze & Validate
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)
    assert analysis["total_rows"] == 3
    assert analysis["valid_rows_count"] == 3
    assert analysis["new_families_count"] == 2
    assert analysis["new_pilgrims_count"] == 3
    assert len(analysis["validation_errors"]) == 0

    # Execute Transactional Import
    res = execute_dataset_import(analysis, csv_file.name, size, fmt, mapping, admin_user="test_admin", db_path=db)
    assert res["status"] == "COMPLETED"
    assert res["successful_records"] == 5  # 2 families + 3 pilgrims

    # Verify in DB
    with get_connection(db) as con:
        fams = con.execute("SELECT * FROM families").fetchall()
        pils = con.execute("SELECT * FROM pilgrims").fetchall()
        assert len(fams) == 2
        assert len(pils) == 3


# =========================================================================
# TEST 2: XLSX IMPORT WITH MULTI-DEVOTEE FAMILIES
# =========================================================================

def test_02_xlsx_import_multi_pilgrim_families(isolated_env):
    db = isolated_env["db_path"]
    xlsx_file = isolated_env["root"] / "groups.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pilgrim Roster"

    headers = ["Family Name", "Pilgrim Name", "Phone", "Age", "Sex", "ID Type", "ID Number", "Status"]
    ws.append(headers)

    data = [
        ("Kalyanam Devotee Roster", "Venkatesh Prasad", "9811122233", 45, "Male", "Aadhaar", "1122", "Pending"),
        ("Kalyanam Devotee Roster", "Latha Prasad", "9811122233", 42, "Female", "Aadhaar", "3344", "Pending"),
        ("Kalyanam Devotee Roster", "Anirudh Prasad", "9811122233", 16, "Male", "Aadhaar", "5566", "Pending"),
    ]
    for row in data:
        ws.append(row)
    wb.save(xlsx_file)

    headers_read, rows_read, size, fmt = read_dataset_file(xlsx_file)
    assert len(rows_read) == 3
    assert "Excel" in fmt

    mapping = detect_column_mapping(headers_read)
    analysis = validate_and_analyze_dataset(headers_read, rows_read, mapping, DUP_POLICY_SKIP, db_path=db)
    assert analysis["valid_rows_count"] == 3
    assert analysis["new_families_count"] == 1
    assert analysis["new_pilgrims_count"] == 3

    res = execute_dataset_import(analysis, xlsx_file.name, size, fmt, mapping, db_path=db)
    assert res["status"] == "COMPLETED"

    fams = get_all_families(db_path=db)
    assert len(fams) == 1
    pils = get_family_pilgrims(fams[0]["id"], db_path=db)
    assert len(pils) == 3


# =========================================================================
# TEST 3: REQUIRED-FIELD & DATA VALIDATION ENGINE
# =========================================================================

def test_03_required_field_and_invalid_data_validation(isolated_env):
    db = isolated_env["db_path"]
    csv_file = isolated_env["root"] / "bad_data.csv"

    # Row 1: Valid
    # Row 2: Missing Pilgrim Name
    # Row 3: Invalid Mobile Number (too short)
    # Row 4: Invalid Age (negative)
    # Row 5: Invalid Email Format
    csv_file.write_text(
        "Family Name,Pilgrim Name,Phone,Email,Age\n"
        "Good Family,Sri Devi,9848011223,sridevi@temple.org,35\n"
        "Missing Devotee,,9848011223,,40\n"
        "Bad Phone,Ramesh,123,,45\n"
        "Bad Age,Suresh,9848011224,,150\n"
        "Bad Email,Mahesh,9848011225,not_an_email,28\n",
        encoding="utf-8",
    )

    headers, rows, size, fmt = read_dataset_file(csv_file)
    mapping = detect_column_mapping(headers)

    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)
    assert analysis["total_rows"] == 5
    assert analysis["valid_rows_count"] == 1
    assert analysis["invalid_rows_count"] == 4
    assert len(analysis["validation_errors"]) >= 4

    # Verify downloadable error report generation
    err_report = isolated_env["root"] / "errors.csv"
    export_validation_report_csv(analysis["validation_errors"], err_report)
    assert err_report.exists()
    content = err_report.read_text(encoding="utf-8")
    assert "Problematic Value" in content
    assert "Invalid 10-digit mobile number" in content or "Age must be an integer" in content


# =========================================================================
# TEST 4: DUPLICATE DETECTION - SKIP POLICY
# =========================================================================

def test_04_duplicate_detection_skip_policy(isolated_env):
    db = isolated_env["db_path"]
    csv_file = isolated_env["root"] / "dup_data.csv"

    # Seed 1 initial family in DB
    from database import add_family_with_pilgrims
    add_family_with_pilgrims(
        {"family_name": "Existing Group", "phone": "9812345678", "status": STATUS_PENDING},
        [{"full_name": "Original Member", "age": 40, "gender": "Male"}],
        db_path=db,
    )

    # Ingestion dataset containing 1 existing duplicate member and 1 new member
    csv_file.write_text(
        "Family Name,Pilgrim Name,Phone\n"
        "Existing Group,Original Member,9812345678\n"
        "Existing Group,New Additional Member,9812345678\n",
        encoding="utf-8",
    )

    headers, rows, size, fmt = read_dataset_file(csv_file)
    mapping = detect_column_mapping(headers)

    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)
    assert analysis["duplicate_records_count"] == 1
    assert analysis["skipped_records_count"] == 1

    execute_dataset_import(analysis, "dup.csv", size, fmt, mapping, db_path=db)

    # In DB: Family still exists, with original member + 1 newly added member
    fams = get_all_families(db_path=db)
    assert len(fams) == 1
    pils = get_family_pilgrims(fams[0]["id"], db_path=db)
    assert len(pils) == 2
    names = {p["full_name"] for p in pils}
    assert "Original Member" in names
    assert "New Additional Member" in names


# =========================================================================
# TEST 5: DUPLICATE DETECTION - UPDATE POLICY
# =========================================================================

def test_05_duplicate_detection_update_policy(isolated_env):
    db = isolated_env["db_path"]
    csv_file = isolated_env["root"] / "update_data.csv"

    from database import add_family_with_pilgrims
    fid = add_family_with_pilgrims(
        {"family_name": "Old Family Name", "phone": "9870001122", "notes": "Initial Note"},
        [{"full_name": "Devotee One", "age": 30, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "0000"}],
        db_path=db,
    )

    # Updated data for same phone
    csv_file.write_text(
        "Family Name,Pilgrim Name,Phone,Age,Last 4 Digits\n"
        "Old Family Name,Devotee One,9870001122,31,9999\n",
        encoding="utf-8",
    )

    headers, rows, size, fmt = read_dataset_file(csv_file)
    mapping = detect_column_mapping(headers)

    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_UPDATE, db_path=db)
    assert analysis["updated_pilgrims_count"] == 1

    execute_dataset_import(analysis, "update.csv", size, fmt, mapping, db_path=db)

    pils = get_family_pilgrims(fid, db_path=db)
    assert len(pils) == 1
    assert pils[0]["age"] == 31
    assert pils[0]["id_proof_last4"] == "9999"


# =========================================================================
# TEST 6: DUPLICATE DETECTION - CANCEL POLICY
# =========================================================================

def test_06_duplicate_detection_cancel_policy(isolated_env):
    db = isolated_env["db_path"]
    csv_file = isolated_env["root"] / "cancel_dup.csv"

    from database import add_family_with_pilgrims
    add_family_with_pilgrims(
        {"family_name": "Strict Unique Group", "phone": "9899001122"},
        [{"full_name": "Strict Member", "age": 50}],
        db_path=db,
    )

    csv_file.write_text(
        "Family Name,Pilgrim Name,Phone\n"
        "Strict Unique Group,Strict Member,9899001122\n",
        encoding="utf-8",
    )

    headers, rows, size, fmt = read_dataset_file(csv_file)
    mapping = detect_column_mapping(headers)

    with pytest.raises(ValueError) as excinfo:
        validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_CANCEL, db_path=db)
    assert "Import aborted per policy DUP_POLICY_CANCEL" in str(excinfo.value)


# =========================================================================
# TEST 7: TRANSACTION ROLLBACK ON CRITICAL ERROR
# =========================================================================

def test_07_transaction_rollback_on_critical_error(isolated_env):
    db = isolated_env["db_path"]

    # Analysis with valid rows but simulate a broken database connection or table failure
    analysis = {
        "families_bundle": {
            "ERR_GROUP": {
                "action": "INSERT",
                "family_name": "Will Fail Group",
                "phone": "9812345678",
                "pilgrims": [
                    {"action": "INSERT", "pilgrim": {"full_name": None}}  # Will trigger NOT NULL failure
                ],
            }
        },
        "total_rows": 1,
        "valid_rows_count": 1,
    }

    initial_families_count = len(get_all_families(db_path=db))

    with pytest.raises(Exception):
        execute_dataset_import(
            analysis=analysis,
            file_name="faulty.csv",
            file_size=100,
            file_format="CSV",
            column_mapping={},
            db_path=db,
        )

    # Verify that database rolled back cleanly
    final_families_count = len(get_all_families(db_path=db))
    assert final_families_count == initial_families_count

    # Check that failed batch was logged for audit
    batches = get_import_batches(db_path=db)
    assert len(batches) == 1
    assert batches[0]["status"] == "FAILED"


# =========================================================================
# TEST 8: LARGE DATASET HANDLING (500+ RECORDS)
# =========================================================================

def test_08_large_dataset_handling(isolated_env):
    db = isolated_env["db_path"]
    large_csv = isolated_env["root"] / "large_dataset.csv"

    # Generate 100 families with 5 pilgrims each = 500 pilgrims
    with open(large_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Family Name", "Pilgrim Name", "Phone", "Age", "Gender", "ID Number"])
        for fam_idx in range(1, 101):
            phone = f"98765{fam_idx:05d}"
            for p_idx in range(1, 6):
                writer.writerow([
                    f"Roster Family {fam_idx}",
                    f"Pilgrim {fam_idx}_{p_idx}",
                    phone,
                    20 + p_idx,
                    "Male" if p_idx % 2 == 1 else "Female",
                    f"{1000 + p_idx}",
                ])

    headers, rows, size, fmt = read_dataset_file(large_csv)
    assert len(rows) == 500

    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)
    assert analysis["valid_rows_count"] == 500
    assert analysis["new_families_count"] == 100
    assert analysis["new_pilgrims_count"] == 500

    res = execute_dataset_import(analysis, large_csv.name, size, fmt, mapping, db_path=db)
    assert res["status"] == "COMPLETED"

    stats = get_stats(db_path=db)
    assert stats["total_families"] == 100
    assert stats["total_pilgrims"] == 500


# =========================================================================
# TEST 9: IMPORT HISTORY LOGGING & AUDIT TRAIL
# =========================================================================

def test_09_import_history_logging_and_retrieval(isolated_env):
    db = isolated_env["db_path"]

    csv_file = isolated_env["root"] / "history_test.csv"
    csv_file.write_text("Family Name,Pilgrim Name,Phone\nTest Family,Devotee A,9811002233\n", encoding="utf-8")

    headers, rows, size, fmt = read_dataset_file(csv_file)
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, db_path=db)

    res = execute_dataset_import(analysis, "history_test.csv", size, fmt, mapping, admin_user="chief_admin", db_path=db)
    batch_id = res["batch_id"]

    batches = get_import_batches(db_path=db)
    assert len(batches) == 1
    assert batches[0]["batch_id"] == batch_id
    assert batches[0]["admin_user"] == "chief_admin"
    assert batches[0]["status"] == "COMPLETED"

    single_batch = get_import_batch(batch_id, db_path=db)
    assert single_batch is not None
    assert single_batch["file_name"] == "history_test.csv"


# =========================================================================
# TEST 10: CLEAN EMPTY DATABASE EXPERIENCE & ZERO COUNTS
# =========================================================================

def test_10_empty_database_dashboard_experience(isolated_env):
    db = isolated_env["db_path"]

    # Verify completely empty DB statistics
    stats = get_stats(db_path=db)
    assert stats["total_families"] == 0
    assert stats["total_pilgrims"] == 0
    assert stats["pending_families"] == 0
    assert stats["booked"] == 0
    assert stats["paid_families"] == 0
    assert stats["ready_for_booking"] == 0
    assert stats["incomplete_profiles"] == 0

    # Ensure no automatic mock seeding happened
    scan = scan_for_mock_data(db_path=db)
    assert len(scan["mock_families"]) == 0
    assert len(scan["legitimate_families"]) == 0


# =========================================================================
# TEST 11: DATABASE BACKUP BEFORE CLEANUP & AUDIT LOGGING
# =========================================================================

def test_11_database_backup_before_cleanup(isolated_env):
    db = isolated_env["db_path"]

    # Insert 1 mock record matching template
    with get_connection(db) as con:
        con.execute("""
            INSERT INTO families (family_code, family_name, phone, email, status, created_at)
            VALUES ('FAM-001', 'Reddy Family', '9848022338', 'ramesh.reddy@example.com', 'Pending', '2026-11-16')
        """)
        con.commit()

    scan = scan_for_mock_data(db_path=db)
    assert len(scan["mock_families"]) == 1

    res = cleanup_mock_data(admin_user="super_admin", db_path=db)
    assert res["status"] == "SUCCESS"
    assert res["deleted_families"] == 1
    assert Path(res["backup_path"]).exists()

    # Check cleanup audit log
    audits = get_cleanup_audits(db_path=db)
    assert len(audits) == 1
    assert audits[0]["deleted_families_count"] == 1
    assert audits[0]["admin_user"] == "super_admin"


# =========================================================================
# TEST 12: PRESERVATION OF REAL USER RECORDS & ADMINISTRATOR ACCOUNTS
# =========================================================================

def test_12_preservation_of_real_records_and_admin_accounts(isolated_env):
    db = isolated_env["db_path"]

    # Create an admin user
    ok_admin, _ = create_admin_user("real_operator", "SecurePass#2026", "Real Operator", db_path=db)
    assert ok_admin is True

    # Insert 1 legitimate user family and 1 mock family
    with get_connection(db) as con:
        con.execute("""
            INSERT INTO families (family_code, family_name, phone, email, status, created_at)
            VALUES ('REAL-999', 'Srinivasa Devotee Trust', '9844005566', 'srinivasa@tirumala-trust.in', 'Pending', '2026-11-16')
        """)
        con.execute("""
            INSERT INTO families (family_code, family_name, phone, email, status, created_at)
            VALUES ('FAM-002', 'Sharma Family', '9440112233', 'v.sharma@example.com', 'Pending', '2026-11-16')
        """)
        con.commit()

    # Execute cleanup
    cleanup_mock_data(db_path=db)

    # Real family must remain untouched
    fams = get_all_families(db_path=db)
    assert len(fams) == 1
    assert fams[0]["family_code"] == "REAL-999"
    assert fams[0]["family_name"] == "Srinivasa Devotee Trust"

    # Admin user credentials must remain untouched and authenticatable
    auth_ok, _, user = authenticate_admin("real_operator", "SecurePass#2026", db_path=db)
    assert auth_ok is True
    assert user["username"] == "real_operator"


# =========================================================================
# TEST 13: PREVENTION OF MOCK DATA SEEDING DURING APPLICATION STARTUP
# =========================================================================

def test_13_prevention_of_mock_data_seeding_during_startup(isolated_env):
    db = isolated_env["db_path"]

    # Simulate fresh app launch
    init_db(db)
    init_auth_db(db)
    init_settings(db)

    # Check database has 0 families and 0 pilgrims
    with get_connection(db) as con:
        count_f = con.execute("SELECT COUNT(*) FROM families").fetchone()[0]
        count_p = con.execute("SELECT COUNT(*) FROM pilgrims").fetchone()[0]
        assert count_f == 0
        assert count_p == 0

    scan = scan_for_mock_data(db_path=db)
    assert scan["has_mock_data"] is False
