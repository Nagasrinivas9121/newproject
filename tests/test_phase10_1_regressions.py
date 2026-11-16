"""
SRIVANI BOOKING MANAGER — Phase 10.1 Dedicated Regression Verification Suite
Tests the three bug fixes:
1. Dataset import aliases ('yatri full name', 'yatri')
2. Duplicate family handling under SKIP, UPDATE, and CANCEL policies
3. Document readiness attribute error prevention with sqlite3.Row, dict, empty, and partial records
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path

from dataset_importer import (
    detect_column_mapping,
    validate_and_analyze_dataset,
    execute_dataset_import,
    DUP_POLICY_SKIP,
    DUP_POLICY_UPDATE,
    DUP_POLICY_CANCEL,
    COLUMN_ALIASES,
)
from database import (
    init_db,
    add_family_with_pilgrims,
    get_all_families,
    get_family_pilgrims,
    assess_document_readiness,
)
from config import STATUS_PENDING


@pytest.fixture
def isolated_db(tmp_path):
    db_file = tmp_path / "test_regressions.db"
    init_db(db_file)
    return db_file


# ------------------------------------------------------------------------------
# 1. DATASET IMPORT ALIAS TESTS
# ------------------------------------------------------------------------------

def test_full_name_aliases_yatri_and_yatri_full_name():
    """Verify COLUMN_ALIASES['full_name'] includes 'yatri full name' and 'yatri'."""
    assert "yatri full name" in COLUMN_ALIASES["full_name"]
    assert "yatri" in COLUMN_ALIASES["full_name"]
    assert "full_name" in COLUMN_ALIASES["full_name"]
    assert "pilgrim_name" in COLUMN_ALIASES["full_name"]

    # Test auto-detection on custom headers
    headers_1 = ["Household", "Yatri Full Name", "Mobile"]
    mapping_1 = detect_column_mapping(headers_1)
    assert mapping_1["Yatri Full Name"] == "full_name"
    assert mapping_1["Household"] == "family_name"
    assert mapping_1["Mobile"] == "phone"

    headers_2 = ["Family Name", "Yatri", "Contact No"]
    mapping_2 = detect_column_mapping(headers_2)
    assert mapping_2["Yatri"] == "full_name"
    assert mapping_2["Family Name"] == "family_name"
    assert mapping_2["Contact No"] == "phone"


# ------------------------------------------------------------------------------
# 2. DUPLICATE HANDLING POLICIES (SKIP, UPDATE, CANCEL)
# ------------------------------------------------------------------------------

def test_skip_policy_existing_family_with_new_pilgrim(isolated_db):
    """
    When SKIP policy is selected and an existing family is matched:
    - Reuse existing family ID
    - Do not create a duplicate family record
    - Insert new pilgrim under the existing family
    """
    fid = add_family_with_pilgrims(
        {"family_name": "Tirupati Group", "phone": "9845011111", "status": STATUS_PENDING},
        [{"full_name": "Member One", "age": 45, "gender": "Male"}],
        db_path=isolated_db,
    )

    headers = ["Family Name", "Pilgrim Name", "Phone"]
    rows = [
        {"_row_num": 2, "Family Name": "Tirupati Group", "Pilgrim Name": "Member Two", "Phone": "9845011111"},
    ]
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=isolated_db)

    assert analysis["valid_rows_count"] == 1
    assert analysis["new_families_count"] == 0  # Reuses existing family

    res = execute_dataset_import(analysis, "test.csv", 100, "CSV", mapping, db_path=isolated_db)
    assert res["successful_records"] == 1

    # In DB: Total families remains 1, pilgrims count becomes 2
    fams = get_all_families(db_path=isolated_db)
    assert len(fams) == 1
    assert fams[0]["id"] == fid

    pils = get_family_pilgrims(fid, db_path=isolated_db)
    assert len(pils) == 2
    pil_names = {p["full_name"] for p in pils}
    assert pil_names == {"Member One", "Member Two"}


def test_skip_policy_existing_family_with_duplicate_pilgrim(isolated_db):
    """
    When SKIP policy is selected and the pilgrim already exists in the family:
    - Skip duplicate pilgrim
    - Do not insert duplicate family
    """
    fid = add_family_with_pilgrims(
        {"family_name": "Venkateswara Seva", "phone": "9845022222", "status": STATUS_PENDING},
        [{"full_name": "Existing Pilgrim", "age": 50, "gender": "Male"}],
        db_path=isolated_db,
    )

    headers = ["Family Name", "Pilgrim Name", "Phone"]
    rows = [
        {"_row_num": 2, "Family Name": "Venkateswara Seva", "Pilgrim Name": "Existing Pilgrim", "Phone": "9845022222"},
    ]
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=isolated_db)

    assert analysis["duplicate_records_count"] == 1
    assert analysis["skipped_records_count"] == 1

    res = execute_dataset_import(analysis, "test.csv", 100, "CSV", mapping, db_path=isolated_db)
    assert res["successful_records"] == 0

    fams = get_all_families(db_path=isolated_db)
    assert len(fams) == 1
    pils = get_family_pilgrims(fid, db_path=isolated_db)
    assert len(pils) == 1


def test_new_family_with_multiple_pilgrims(isolated_db):
    """Import a brand new family with multiple pilgrims in one batch."""
    headers = ["Family Name", "Pilgrim Name", "Phone", "Age", "Gender"]
    rows = [
        {"_row_num": 2, "Family Name": "Ganesh Family", "Pilgrim Name": "Ganesh", "Phone": "9845033333", "Age": 40, "Gender": "Male"},
        {"_row_num": 3, "Family Name": "Ganesh Family", "Pilgrim Name": "Gauri", "Phone": "9845033333", "Age": 36, "Gender": "Female"},
        {"_row_num": 4, "Family Name": "Ganesh Family", "Pilgrim Name": "Kartik", "Phone": "9845033333", "Age": 12, "Gender": "Male"},
    ]
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_SKIP, db_path=isolated_db)

    assert analysis["new_families_count"] == 1
    assert analysis["new_pilgrims_count"] == 3

    res = execute_dataset_import(analysis, "batch.csv", 200, "CSV", mapping, db_path=isolated_db)
    assert res["successful_records"] == 4  # 1 family + 3 pilgrims

    fams = get_all_families(db_path=isolated_db)
    assert len(fams) == 1
    pils = get_family_pilgrims(fams[0]["id"], db_path=isolated_db)
    assert len(pils) == 3


def test_update_policy_updates_family_and_pilgrims(isolated_db):
    """Under UPDATE policy, matching records are updated in place."""
    fid = add_family_with_pilgrims(
        {"family_name": "Old Name", "phone": "9845044444", "status": STATUS_PENDING},
        [{"full_name": "Devotee One", "age": 30, "gender": "Male"}],
        db_path=isolated_db,
    )

    headers = ["Family Name", "Pilgrim Name", "Phone", "Age", "Gender", "Address"]
    rows = [
        {"_row_num": 2, "Family Name": "Updated Name", "Pilgrim Name": "Devotee One", "Phone": "9845044444", "Age": 31, "Gender": "Male", "Address": "Tirupati City"},
    ]
    mapping = detect_column_mapping(headers)
    analysis = validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_UPDATE, db_path=isolated_db)

    res = execute_dataset_import(analysis, "update.csv", 150, "CSV", mapping, db_path=isolated_db)
    assert res["updated_records"] >= 1

    fams = get_all_families(db_path=isolated_db)
    assert len(fams) == 1
    assert fams[0]["family_name"] == "Updated Name"

    pils = get_family_pilgrims(fid, db_path=isolated_db)
    assert len(pils) == 1
    assert pils[0]["age"] == 31


def test_cancel_policy_aborts_on_duplicate(isolated_db):
    """Under CANCEL policy, any duplicate pilgrim raises ValueError before import."""
    add_family_with_pilgrims(
        {"family_name": "Strict Family", "phone": "9845055555", "status": STATUS_PENDING},
        [{"full_name": "Locked Member", "age": 60, "gender": "Male"}],
        db_path=isolated_db,
    )

    headers = ["Family Name", "Pilgrim Name", "Phone"]
    rows = [
        {"_row_num": 2, "Family Name": "Strict Family", "Pilgrim Name": "Locked Member", "Phone": "9845055555"},
    ]
    mapping = detect_column_mapping(headers)

    with pytest.raises(ValueError, match="Duplicate record detected"):
        validate_and_analyze_dataset(headers, rows, mapping, DUP_POLICY_CANCEL, db_path=isolated_db)


# ------------------------------------------------------------------------------
# 3. DOCUMENT READINESS ATTRIBUTE ERROR PREVENTION TESTS
# ------------------------------------------------------------------------------

def test_document_readiness_with_sqlite3_row(isolated_db):
    """Verify assess_document_readiness works directly on sqlite3.Row objects from the DB."""
    fid = add_family_with_pilgrims(
        {"family_name": "Row Test Family", "phone": "9845066666", "status": STATUS_PENDING},
        [
            {"full_name": "Devotee Complete", "age": 35, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
            {"full_name": "Devotee Incomplete", "age": 28, "gender": "Female", "id_proof_type": "", "id_proof_last4": ""},
        ],
        db_path=isolated_db,
    )

    # Fetch actual sqlite3.Row objects from DB
    db_rows = get_family_pilgrims(fid, db_path=isolated_db)
    assert len(db_rows) == 2
    assert isinstance(db_rows[0], sqlite3.Row)

    # Must not raise AttributeError: 'sqlite3.Row' object has no attribute 'get'
    res = assess_document_readiness(db_rows)
    assert isinstance(res, dict)
    assert res["is_ready"] is False
    assert res["status"] == "Incomplete"
    assert len(res["missing_devotees"]) == 1
    assert "Devotee Incomplete" in res["missing_devotees"][0]


def test_document_readiness_with_dictionary_records():
    """Verify assess_document_readiness works with plain dictionaries."""
    complete_dict = [
        {"full_name": "Pilgrim A", "age": 42, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]
    res1 = assess_document_readiness(complete_dict)
    assert res1["is_ready"] is True
    assert res1["status"] == "Verified Ready"


def test_document_readiness_with_empty_and_none_records():
    """Verify assess_document_readiness handles empty lists and records with missing keys."""
    # Empty list
    res_empty = assess_document_readiness([])
    assert res_empty["is_ready"] is False
    assert res_empty["status"] == "No Devotees"

    # None and empty dictionaries
    res_sparse = assess_document_readiness([{}, None])
    assert res_sparse["is_ready"] is False
    assert res_sparse["status"] == "Incomplete"
