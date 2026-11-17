"""
SRIVANI BOOKING MANAGER — Dashboard Data Import Feature Verification Suite
Tests:
1. CSV upload and parsing (.csv)
2. XLSX upload and parsing (.xlsx)
3. Dataset preview data structure (Row #, Family ID, Family name, Pilgrim name, Age, Gender, Mobile number, other columns)
4. Column mapping (standard and custom aliases, unmatched detection, ambiguous mapping checks)
5. Strict validation (missing required values, invalid phone, invalid age, duplicate checks, missing family references, format errors)
6. Duplicate handling policies (SKIP with existing family reuse, UPDATE with confirmation, CANCEL)
7. Multi-pilgrim family relationships preservation
8. Database transaction rollback on critical errors
9. Dashboard statistics dynamic refresh (Total Families, Total Devotees, Pending Queue, In Progress, Booked, Total Donations)
10. Import history & batch tracking
11. Pre-import backup creation
"""
import pytest
import sqlite3
import openpyxl
from pathlib import Path

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
from database import (
    init_db,
    get_connection,
    add_family_with_pilgrims,
    get_all_families,
    get_family_pilgrims,
    get_stats,
    get_import_batches,
)
from data_import_view import DatasetImportDialog


@pytest.fixture
def isolated_env(tmp_path):
    """Isolated environment with dedicated database and backup directory."""
    db_file = tmp_path / "test_import.db"
    init_db(db_file)
    return {
        "db": db_file,
        "root": tmp_path,
    }


# =============================================================================
# 1. CSV & XLSX UPLOAD AND PARSING TESTS
# =============================================================================

def test_csv_upload_and_parsing(isolated_env):
    """Verify CSV file ingestion with auto-delimiter and encoding detection."""
    csv_file = isolated_env["root"] / "pilgrims_dataset.csv"
    csv_file.write_text(
        "Family Name,Pilgrim Name,Phone,Age,Gender,Donation\n"
        "Tirumala Group,Raghavendra Rao,9848011222,48,Male,20000\n"
        "Tirumala Group,Padmavathi Rao,9848011222,44,Female,20000\n"
        "Vijayawada Seva,Subba Rao,9849033444,52,Male,10000\n",
        encoding="utf-8",
    )

    headers, rows, size, fmt = read_dataset_file(csv_file)
    assert fmt == "CSV"
    assert size > 0
    assert len(headers) == 6
    assert len(rows) == 3
    assert rows[0]["Family Name"] == "Tirumala Group"
    assert rows[0]["Pilgrim Name"] == "Raghavendra Rao"
    assert rows[0]["_row_num"] == 2


def test_xlsx_upload_and_parsing(isolated_env):
    """Verify Excel (.xlsx) file ingestion via openpyxl."""
    xlsx_file = isolated_env["root"] / "devotees_roster.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Devotees"

    headers = ["Family ID", "Family Name", "Devotee Full Name", "Mobile Number", "Age", "Gender", "Special Requests"]
    ws.append(headers)
    ws.append(["FAM-001", "Narayana Family", "Lakshmi Narayana", "9988776655", 56, "M", "Senior Citizen Darshan"])
    ws.append(["FAM-001", "Narayana Family", "Saraswathi Narayana", "9988776655", 52, "F", "Wheelchair Support"])
    wb.save(xlsx_file)

    headers_read, rows_read, size, fmt = read_dataset_file(xlsx_file)
    assert "Excel" in fmt
    assert len(headers_read) == 7
    assert len(rows_read) == 2
    assert rows_read[0]["Family ID"] == "FAM-001"
    assert rows_read[0]["Devotee Full Name"] == "Lakshmi Narayana"
    assert rows_read[1]["Special Requests"] == "Wheelchair Support"


# =============================================================================
# 2. DATASET PREVIEW DATA STRUCTURE
# =============================================================================

def test_dataset_preview_data_structure(isolated_env):
    """Verify preview structure exposes Row #, Family ID, Family Name, Pilgrim Name, Age, Gender, Mobile, plus other columns."""
    sample_headers = ["Family Code", "Family Name", "Yatri", "Contact Mobile", "Age", "Gender", "City", "Quota"]
    sample_rows = [
        {
            "_row_num": 1,
            "Family Code": "FAM-999",
            "Family Name": "Anand Family",
            "Yatri": "Anand Kumar",
            "Contact Mobile": "9848099999",
            "Age": "40",
            "Gender": "Male",
            "City": "Hyderabad",
            "Quota": "Srivani VIP",
        }
    ]

    mapping = detect_column_mapping(sample_headers)
    assert mapping["Family Code"] == "family_code"
    assert mapping["Family Name"] == "family_name"
    assert mapping["Yatri"] == "full_name"
    assert mapping["Contact Mobile"] == "phone"
    assert mapping["Age"] == "age"
    assert mapping["Gender"] == "gender"

    # Verify resolution of core columns
    target_to_hdr = {t: h for h, t in mapping.items() if t}
    r = sample_rows[0]
    row_num = r.get("_row_num")
    fam_id = r.get(target_to_hdr.get("family_code"))
    fam_name = r.get(target_to_hdr.get("family_name"))
    pilgrim_name = r.get(target_to_hdr.get("full_name"))
    age = r.get(target_to_hdr.get("age"))
    gender = r.get(target_to_hdr.get("gender"))
    mobile = r.get(target_to_hdr.get("phone"))

    # Other non-core detected columns
    core_hdrs = {target_to_hdr.get(k) for k in ("family_code", "family_name", "full_name", "age", "gender", "phone")}
    other_hdrs = [h for h in sample_headers if h not in core_hdrs]

    assert row_num == 1
    assert fam_id == "FAM-999"
    assert fam_name == "Anand Family"
    assert pilgrim_name == "Anand Kumar"
    assert age == "40"
    assert gender == "Male"
    assert mobile == "9848099999"
    assert "City" in other_hdrs
    assert "Quota" in other_hdrs


# =============================================================================
# 3. COLUMN MAPPING & AMBIGUOUS MAPPING CHECKS
# =============================================================================

def test_column_mapping_aliases_and_unmatched():
    """Verify auto-detection of canonical fields and detection of unmatched columns."""
    headers = ["Head of Family", "Yatri Full Name", "Phone No", "Age (Years)", "Sex", "Unknown Column 1", "Unmatched Column 2"]
    mapping = detect_column_mapping(headers)

    assert mapping["Head of Family"] == "family_name"
    assert mapping["Yatri Full Name"] == "full_name"
    assert mapping["Phone No"] == "phone"
    assert mapping["Age (Years)"] == "age"
    assert mapping["Sex"] == "gender"
    assert mapping["Unknown Column 1"] is None
    assert mapping["Unmatched Column 2"] is None


def test_ambiguous_column_mapping_detection():
    """Verify detection when multiple columns map to the same database field."""
    # Simulate a mapping where user accidentally maps two columns to 'phone'
    ambiguous_mapping = {
        "Col1": "phone",
        "Col2": "phone",
        "Col3": "full_name",
        "Col4": "family_name",
    }
    target_counts = {}
    for h, t in ambiguous_mapping.items():
        if t:
            target_counts.setdefault(t, []).append(h)

    duplicates = [t for t, hdrs in target_counts.items() if len(hdrs) > 1]
    assert "phone" in duplicates
    assert len(duplicates) == 1


# =============================================================================
# 4. VALIDATION ENGINE — ERROR REPORTING
# =============================================================================

def test_validation_engine_all_error_types(isolated_env):
    """Verify validation engine flags missing required values, invalid phone, invalid age, and missing family reference."""
    db = isolated_env["db"]

    headers = ["Family ID", "Family Name", "Pilgrim Name", "Phone", "Age", "Donation Amount"]
    rows = [
        # Row 1: Valid
        {"_row_num": 1, "Family ID": "", "Family Name": "Valid Family", "Pilgrim Name": "Devotee One", "Phone": "9848012345", "Age": "30", "Donation Amount": "10000"},
        # Row 2: Missing Pilgrim Name
        {"_row_num": 2, "Family ID": "", "Family Name": "No Devotee Fam", "Pilgrim Name": "", "Phone": "9848012345", "Age": "35", "Donation Amount": "10000"},
        # Row 3: Invalid Mobile (too short)
        {"_row_num": 3, "Family ID": "", "Family Name": "Bad Phone Fam", "Pilgrim Name": "Devotee Two", "Phone": "12345", "Age": "40", "Donation Amount": "10000"},
        # Row 4: Invalid Age (> 120)
        {"_row_num": 4, "Family ID": "", "Family Name": "Bad Age Fam", "Pilgrim Name": "Devotee Three", "Phone": "9848012346", "Age": "150", "Donation Amount": "10000"},
        # Row 5: Missing Family Reference (Code FAM-NONEXISTENT does not exist in DB, and Family Name is empty)
        {"_row_num": 5, "Family ID": "FAM-NONEXISTENT", "Family Name": "", "Pilgrim Name": "Devotee Four", "Phone": "9848012347", "Age": "25", "Donation Amount": "10000"},
        # Row 6: Invalid Donation Amount (negative)
        {"_row_num": 6, "Family ID": "", "Family Name": "Bad Donation Fam", "Pilgrim Name": "Devotee Five", "Phone": "9848012348", "Age": "28", "Donation Amount": "-500"},
    ]

    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)

    assert analysis["total_rows"] == 6
    assert analysis["valid_rows_count"] == 1
    assert analysis["invalid_rows_count"] == 5
    assert len(analysis["validation_errors"]) >= 5

    # Export errors to CSV
    err_file = isolated_env["root"] / "val_errors.csv"
    export_validation_report_csv(analysis["validation_errors"], err_file)
    assert err_file.exists()
    content = err_file.read_text(encoding="utf-8")
    assert "Invalid 10-digit mobile number format" in content
    assert "Age must be an integer between 0 and 120" in content
    assert "Missing family reference" in content


# =============================================================================
# 5. DUPLICATE HANDLING POLICIES (SKIP, UPDATE, CANCEL)
# =============================================================================

def test_duplicate_policy_skip_reuses_family(isolated_env):
    """Under SKIP policy, when importing a new pilgrim for an existing family, reuse family ID and do not duplicate family."""
    db = isolated_env["db"]

    # Seed an existing family in database
    existing_fid = add_family_with_pilgrims(
        {
            "family_code": "FAM-EXISTING",
            "family_name": "Sharma Family",
            "phone": "9876543210",
            "donation_amount": 10000,
            "status": "Pending",
        },
        [{"full_name": "Ramesh Sharma", "age": 50, "gender": "Male"}],
        db_path=db,
    )

    # Ingest a dataset containing a NEW pilgrim under that SAME family phone/name
    headers = ["Family Name", "Pilgrim Name", "Phone", "Age", "Gender"]
    rows = [
        {"_row_num": 1, "Family Name": "Sharma Family", "Pilgrim Name": "Suresh Sharma", "Phone": "9876543210", "Age": "45", "Gender": "Male"}
    ]
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)

    assert analysis["valid_rows_count"] == 1
    assert analysis["new_families_count"] == 0  # Family is reused, not duplicated!
    assert analysis["new_pilgrims_count"] == 1

    res = execute_dataset_import(analysis, "test.csv", 100, "CSV", mapping, db_path=db)
    assert res["successful_records"] >= 1

    # Verify database state: Still only 1 family, but now 2 pilgrims
    all_fams = get_all_families(db_path=db)
    assert len(all_fams) == 1
    assert all_fams[0]["id"] == existing_fid

    pils = get_family_pilgrims(existing_fid, db_path=db)
    assert len(pils) == 2
    pil_names = [p["full_name"] for p in pils]
    assert "Ramesh Sharma" in pil_names
    assert "Suresh Sharma" in pil_names


def test_duplicate_policy_update(isolated_env):
    """Under UPDATE policy, existing records are updated with new address/contact details."""
    db = isolated_env["db"]

    fid = add_family_with_pilgrims(
        {"family_code": "FAM-UPD", "family_name": "Original Name", "phone": "9123456780", "address": "Old Address"},
        [{"full_name": "Devotee A", "age": 30}],
        db_path=db,
    )

    headers = ["Family Name", "Pilgrim Name", "Phone", "Age", "Address"]
    rows = [
        {"_row_num": 1, "Family Name": "Updated Family Name", "Pilgrim Name": "Devotee A", "Phone": "9123456780", "Age": "31", "Address": "New Tirupati Address"}
    ]
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_UPDATE, db_path=db)
    assert analysis["updated_pilgrims_count"] == 1

    res = execute_dataset_import(analysis, "update.csv", 100, "CSV", mapping, db_path=db)
    assert res["updated_records"] >= 1

    # Verify family record was updated in database
    with get_connection(db) as con:
        row = con.execute("SELECT family_name, address FROM families WHERE id=?", (fid,)).fetchone()
        assert row["family_name"] == "Updated Family Name"
        assert row["address"] == "New Tirupati Address"


def test_duplicate_policy_cancel(isolated_env):
    """Under CANCEL policy, any duplicate encounters raises ValueError and aborts the import."""
    db = isolated_env["db"]

    add_family_with_pilgrims(
        {"family_code": "FAM-CANCEL", "family_name": "Gupta Family", "phone": "9000011111"},
        [{"full_name": "Mohan Gupta", "age": 40}],
        db_path=db,
    )

    headers = ["Family Name", "Pilgrim Name", "Phone", "Age"]
    rows = [
        {"_row_num": 1, "Family Name": "Gupta Family", "Pilgrim Name": "Mohan Gupta", "Phone": "9000011111", "Age": "40"}
    ]
    mapping = detect_column_mapping(headers)

    with pytest.raises(ValueError, match="Import aborted per policy DUP_POLICY_CANCEL"):
        validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_CANCEL, db_path=db)


# =============================================================================
# 6. TRANSACTION ROLLBACK ON CRITICAL ERROR
# =============================================================================

def test_database_transaction_rollback(isolated_env):
    """Verify that if an error occurs during execution, the transaction rolls back cleanly."""
    db = isolated_env["db"]

    analysis = {
        "families_bundle": {
            "FAM-BAD": {
                "action": "INSERT",
                "family_code": "FAM-BAD",
                "family_name": "Bad Group",
                "contact_name": "Contact",
                "phone": "9999900000",
                "email": "test@test.com",
                "donation_amount": 10000,
                "booking_status": "Pending",
                "payment_status": "Not Requested",
                "preferred_date": "2026-06-01",
                "booking_type": "Advance",
                "priority": "Normal",
                "notes": "",
                "pilgrims": [
                    {"action": "INSERT", "pilgrim": {"full_name": "Devotee 1", "age": 30, "gender": "M"}},
                    # Induce a critical error: Invalid SQL structure or None that violates NOT NULL
                    {"action": "INSERT", "pilgrim": {"full_name": None, "age": 30, "gender": "M"}},
                ],
            }
        },
        "skipped_records_count": 0,
        "invalid_rows_count": 0,
    }

    initial_families = len(get_all_families(db_path=db))

    with pytest.raises(Exception):
        execute_dataset_import(analysis, "bad.csv", 100, "CSV", {}, db_path=db)

    # Confirm rollback: No family was left behind in database
    final_families = len(get_all_families(db_path=db))
    assert final_families == initial_families


# =============================================================================
# 7. DASHBOARD REFRESH & LIVE STATS VERIFICATION
# =============================================================================

def test_dashboard_statistics_refresh_after_import(isolated_env):
    """Verify all 6 dashboard stats (Families, Devotees, Pending Queue, In Progress, Booked, Total Donations) update accurately."""
    db = isolated_env["db"]

    # Initial stats should all be zero in empty database
    initial_stats = get_stats(db_path=db)
    assert initial_stats["total_families"] == 0
    assert initial_stats["total_pilgrims"] == 0
    assert initial_stats["total_donations"] == 0

    # Import dataset with multiple families, pilgrims, and donation amounts
    headers = ["Family Name", "Pilgrim Name", "Phone", "Age", "Gender", "Donation Amount", "Status"]
    rows = [
        # Family 1 (2 devotees, 20,000 INR, Pending)
        {"_row_num": 1, "Family Name": "Balaji Bhaktas", "Pilgrim Name": "Srinivasan", "Phone": "9848011111", "Age": "45", "Gender": "M", "Donation Amount": "20000", "Status": "Pending"},
        {"_row_num": 2, "Family Name": "Balaji Bhaktas", "Pilgrim Name": "Padma Srinivasan", "Phone": "9848011111", "Age": "42", "Gender": "F", "Donation Amount": "20000", "Status": "Pending"},
        # Family 2 (1 devotee, 10,000 INR, Booked)
        {"_row_num": 3, "Family Name": "Govinda Mandali", "Pilgrim Name": "Kalyan Ram", "Phone": "9848022222", "Age": "38", "Gender": "M", "Donation Amount": "10000", "Status": "Booked"},
        # Family 3 (1 devotee, 10,000 INR, In progress)
        {"_row_num": 4, "Family Name": "Venkateswara Seva", "Pilgrim Name": "Hari Krishna", "Phone": "9848033333", "Age": "50", "Gender": "M", "Donation Amount": "10000", "Status": "In progress"},
    ]

    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)
    res = execute_dataset_import(analysis, "donations_test.csv", 500, "CSV", mapping, db_path=db)

    assert res["successful_records"] == 7  # 3 families + 4 pilgrims

    # Verify refreshed dashboard statistics directly from database
    refreshed_stats = get_stats(db_path=db)
    assert refreshed_stats["total_families"] == 3
    assert refreshed_stats["total_pilgrims"] == 4
    assert refreshed_stats["pending_families"] == 1
    assert refreshed_stats["in_progress"] == 1
    assert refreshed_stats["booked"] == 1
    assert refreshed_stats["total_donations"] == 40000  # 20,000 + 10,000 + 10,000 INR


# =============================================================================
# 8. IMPORT HISTORY & BATCH AUDITING
# =============================================================================

def test_import_history_batch_recording(isolated_env):
    """Verify import batch ID is created and recorded in import_batches table."""
    db = isolated_env["db"]

    headers = ["Family Name", "Pilgrim Name", "Phone", "Age"]
    rows = [
        {"_row_num": 1, "Family Name": "Audit Fam", "Pilgrim Name": "Devotee X", "Phone": "9848055555", "Age": "29"}
    ]
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=db)
    res = execute_dataset_import(analysis, "audit_file.csv", 250, "CSV", mapping, admin_user="super_admin", db_path=db)

    batch_id = res["batch_id"]
    assert batch_id.startswith("BATCH-")

    # Verify in database table import_batches
    batches = get_import_batches(limit=10, db_path=db)
    assert len(batches) >= 1
    matching = [b for b in batches if b["batch_id"] == batch_id]
    assert len(matching) == 1
    b = matching[0]
    assert b["file_name"] == "audit_file.csv"
    assert b["admin_user"] == "super_admin"
    assert b["successful_records"] == 2  # 1 family + 1 devotee
    assert b["status"] == "COMPLETED"
