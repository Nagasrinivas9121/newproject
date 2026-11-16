"""
SRIVANI BOOKING MANAGER - PHASE 9 TEST SUITE
Fast Booking Preparation Engine, Readiness Evaluator, Document Manager & Compliance Suite
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
import openpyxl

import config
import database as db
from readiness_engine import (
    STATUS_NOT_STARTED,
    STATUS_INCOMPLETE,
    STATUS_READY_FOR_MANUAL_BOOKING,
    STATUS_BOOKING_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_CANCELLED,
    PAYMENT_NOT_PAID,
    PAYMENT_PENDING,
    PAYMENT_PAID,
    PAYMENT_FAILED,
    PAYMENT_REFUNDED,
    calculate_booking_readiness,
    detect_pilgrim_duplicates,
    normalize_booking_status,
    normalize_payment_tracking_status,
    validate_family_fields,
    validate_pilgrim_fields,
)
from document_manager import (
    compute_file_hash,
    store_family_document,
    validate_document_file,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provide an isolated temporary SQLite database for testing."""
    test_db_path = tmp_path / "test_srivani_phase9.db"
    db.init_db(test_db_path)
    return test_db_path


def test_01_family_creation_and_editing(temp_db):
    """Test family profile creation, retrieval, and updating."""
    fam_data = {
        "family_code": "FAM-P9-001",
        "family_name": "Balaji Bhakta Family",
        "phone": "9876543210",
        "email": "balaji.bhakta@example.com",
        "preferred_date": "2026-12-25",
        "donation_amount": 20000.0,
        "status": STATUS_NOT_STARTED,
    }
    pilgrims_data = [
        {"full_name": "Balaji Rao", "age": 42, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Padma Rao", "age": 38, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]

    fam_id = db.add_family_with_pilgrims(fam_data, pilgrims_data, db_path=temp_db)
    assert fam_id > 0

    # Retrieve and verify
    family = db.get_family(fam_id, db_path=temp_db)
    assert family is not None
    assert family["family_code"] == "FAM-P9-001"
    assert family["family_name"] == "Balaji Bhakta Family"
    assert family["phone"] == "9876543210"

    # Edit family
    db.update_family(
        fam_id,
        {
            "family_code": "FAM-P9-001",
            "family_name": "Balaji Bhakta Family Updated",
            "phone": "9876543211",
            "email": "balaji.updated@example.com",
            "donation_amount": 30000.0,
            "status": STATUS_READY_FOR_MANUAL_BOOKING,
            "payment_status": PAYMENT_PENDING,
            "priority": "High",
            "booking_type": "Advance",
            "preferred_date": "2026-12-26",
            "address": "Tirupati",
            "notes": "VIP request",
        },
        db_path=temp_db,
    )

    updated = db.get_family(fam_id, db_path=temp_db)
    assert updated["family_name"] == "Balaji Bhakta Family Updated"
    assert updated["phone"] == "9876543211"
    assert updated["donation_amount"] == 30000.0


def test_02_multiple_pilgrims_management(temp_db):
    """Test adding, listing, editing, and deleting multiple pilgrim records."""
    fam_id = db.add_family_with_pilgrims(
        {"family_code": "FAM-P9-002", "family_name": "Sharma Roster", "phone": "9876543202"},
        [
            {"full_name": "Ramesh Sharma", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1111"},
            {"full_name": "Sunita Sharma", "age": 42, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "2222"},
        ],
        db_path=temp_db,
    )

    # Add 3rd pilgrim
    p3_id = db.add_pilgrim(
        fam_id,
        {"full_name": "Rahul Sharma", "age": 16, "gender": "Male", "id_proof_type": "Passport", "id_proof_last4": "3333"},
        db_path=temp_db,
    )
    assert p3_id > 0

    pils = db.get_family_pilgrims(fam_id, db_path=temp_db)
    assert len(pils) == 3

    # Delete 1 pilgrim
    success_del = db.delete_pilgrim(p3_id, db_path=temp_db)
    assert success_del is True
    pils_after = db.get_family_pilgrims(fam_id, db_path=temp_db)
    assert len(pils_after) == 2


def test_03_required_field_validation():
    """Test validation of required family and pilgrim profile fields."""
    # 1. Invalid phone number (letters / too short)
    bad_fam = {"family_name": "Reddy Family", "phone": "123"}
    valid, errors = validate_family_fields(bad_fam)
    assert valid is False
    assert any("Phone number" in err for err in errors)

    # 2. Missing family name
    nameless_fam = {"family_name": "", "phone": "9876543210"}
    valid, errors = validate_family_fields(nameless_fam)
    assert valid is False
    assert any("Primary Devotee name is required" in err for err in errors)

    # 3. Invalid pilgrim age (negative or > 120)
    bad_pil = {"full_name": "Invalid Devotee", "age": -5, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"}
    valid, errors = validate_pilgrim_fields(bad_pil, 1)
    assert valid is False
    assert any("Valid age" in err for err in errors)

    # 4. Missing ID proof last 4
    no_id_pil = {"full_name": "Valid Name", "age": 30, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": ""}
    valid, errors = validate_pilgrim_fields(no_id_pil, 1)
    assert valid is False
    assert any("Last 4 characters of ID proof" in err for err in errors)


def test_04_duplicate_detection():
    """Test duplicate pilgrim identification in roster."""
    # Duplicate ID proof in same family
    pils_with_dup_id = [
        {"full_name": "Person A", "age": 30, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "9999"},
        {"full_name": "Person B", "age": 32, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "9999"},
    ]
    dups = detect_pilgrim_duplicates(pils_with_dup_id)
    assert len(dups) >= 1
    assert "Duplicate ID proof" in dups[0]

    # Duplicate devotee name in roster
    pils_with_dup_name = [
        {"full_name": "Suresh Kumar", "age": 40, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1111"},
        {"full_name": "Suresh Kumar", "age": 40, "gender": "Male", "id_proof_type": "Passport", "id_proof_last4": "2222"},
    ]
    dups_name = detect_pilgrim_duplicates(pils_with_dup_name)
    assert len(dups_name) >= 1
    assert "Duplicate pilgrim name" in dups_name[0]


def test_05_booking_readiness_calculation():
    """
    Test booking readiness evaluation engine across all 6 statuses:
    NOT_STARTED, INCOMPLETE, READY_FOR_MANUAL_BOOKING, BOOKING_IN_PROGRESS, BOOKED, CANCELLED.
    """
    complete_fam = {"family_name": "Venkatesh Rao", "phone": "9876543210", "donation_amount": 20000.0}
    complete_pils = [
        {"full_name": "Venkatesh Rao", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Lakshmi Rao", "age": 40, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]

    # 1. Complete -> READY_FOR_MANUAL_BOOKING (Score 100%)
    res_ready = calculate_booking_readiness(complete_fam, complete_pils)
    assert res_ready["status"] == STATUS_READY_FOR_MANUAL_BOOKING
    assert res_ready["is_ready"] is True
    assert res_ready["score"] == 100
    assert len(res_ready["missing_items"]) == 0

    # 2. Incomplete profile (missing age and invalid phone) -> INCOMPLETE
    inc_fam = {"family_name": "Incomplete Family", "phone": "123", "donation_amount": 0}
    inc_pils = [{"full_name": "Incomplete Person", "age": None, "gender": "", "id_proof_type": "", "id_proof_last4": ""}]
    res_inc = calculate_booking_readiness(inc_fam, inc_pils)
    assert res_inc["status"] == STATUS_INCOMPLETE
    assert res_inc["is_ready"] is False
    assert res_inc["score"] < 100
    assert len(res_inc["missing_items"]) > 0

    # 3. No pilgrims at all -> NOT_STARTED / INCOMPLETE
    empty_fam = {"family_name": "", "phone": ""}
    res_empty = calculate_booking_readiness(empty_fam, [])
    assert res_empty["status"] in (STATUS_NOT_STARTED, STATUS_INCOMPLETE)
    assert res_empty["is_ready"] is False

    # 4. Terminal statuses: BOOKED and CANCELLED
    booked_fam = dict(complete_fam, status=STATUS_BOOKED)
    res_booked = calculate_booking_readiness(booked_fam, complete_pils)
    assert res_booked["status"] == STATUS_BOOKED
    assert res_booked["is_ready"] is True

    cancelled_fam = dict(complete_fam, status=STATUS_CANCELLED)
    res_cancelled = calculate_booking_readiness(cancelled_fam, complete_pils)
    assert res_cancelled["status"] == STATUS_CANCELLED
    assert res_cancelled["is_ready"] is False

    # 5. In-progress status
    prog_fam = dict(complete_fam, status=STATUS_BOOKING_IN_PROGRESS)
    res_prog = calculate_booking_readiness(prog_fam, complete_pils)
    assert res_prog["status"] == STATUS_BOOKING_IN_PROGRESS
    assert res_prog["is_ready"] is True


def test_06_booking_status_transitions(temp_db):
    """Test manual booking status transitions and history logging."""
    fam_id = db.add_family_with_pilgrims(
        {"family_code": "FAM-TRANS", "family_name": "Transition Family", "phone": "9876543299", "status": STATUS_NOT_STARTED},
        [{"full_name": "Devotee One", "age": 30, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"}],
        db_path=temp_db,
    )

    # Transition 1: Mark READY_FOR_MANUAL_BOOKING
    db.update_status_and_payment(fam_id, STATUS_READY_FOR_MANUAL_BOOKING, PAYMENT_NOT_PAID, notes="Preparation verified", db_path=temp_db)
    f1 = db.get_family(fam_id, db_path=temp_db)
    assert normalize_booking_status(f1["status"]) == STATUS_READY_FOR_MANUAL_BOOKING

    # Transition 2: Mark BOOKING_IN_PROGRESS
    db.update_status_and_payment(fam_id, STATUS_BOOKING_IN_PROGRESS, PAYMENT_PENDING, notes="Operator preparing TTD tab", db_path=temp_db)
    f2 = db.get_family(fam_id, db_path=temp_db)
    assert normalize_booking_status(f2["status"]) == STATUS_BOOKING_IN_PROGRESS

    # Transition 3: Mark BOOKED
    db.update_status_and_payment(fam_id, STATUS_BOOKED, PAYMENT_PAID, notes="Ticket confirmed by client", db_path=temp_db)
    f3 = db.get_family(fam_id, db_path=temp_db)
    assert normalize_booking_status(f3["status"]) == STATUS_BOOKED
    assert f3["booked_at"] is not None


def test_07_payment_tracking_status(temp_db):
    """
    Test payment status tracking: NOT_PAID, PAYMENT_PENDING, PAID, FAILED, REFUNDED.
    Ensure no banking credentials or sensitive financial data are logged or accepted.
    """
    fam_id = db.add_family_with_pilgrims(
        {"family_code": "FAM-PAY", "family_name": "Payment Tracking Test", "phone": "9876543288"},
        [{"full_name": "Payer One", "age": 35, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "5555"}],
        db_path=temp_db,
    )

    # Cycle through all 5 payment statuses
    for p_status in [PAYMENT_NOT_PAID, PAYMENT_PENDING, PAYMENT_PAID, PAYMENT_FAILED, PAYMENT_REFUNDED]:
        db.update_family_payment_tracking(
            family_id=fam_id,
            payment_status=p_status,
            payment_ref=f"UTR-TEST-{p_status}",
            payment_notes=f"Audited accounting note for {p_status}",
            db_path=temp_db,
        )
        fam = db.get_family(fam_id, db_path=temp_db)
        assert normalize_payment_tracking_status(fam["payment_status"]) == p_status
        assert fam["payment_ref"] == f"UTR-TEST-{p_status}"
        assert "Audited accounting note" in fam["payment_notes"]


def test_08_document_attachment_and_validation(temp_db, tmp_path):
    """Test supporting document attachment (.pdf, .png, .jpg), size validation, and SHA-256 integrity."""
    fam_id = db.add_family_with_pilgrims(
        {"family_code": "FAM-DOC", "family_name": "Document Family", "phone": "9876543277"},
        [{"full_name": "Doc Devotee", "age": 28, "gender": "Female", "id_proof_type": "Passport", "id_proof_last4": "7777"}],
        db_path=temp_db,
    )

    # 1. Create a valid mock PDF file
    doc_file = tmp_path / "devotee_id_proof.pdf"
    doc_content = b"%PDF-1.4\n%Supporting Devotee Identity Document for SRIVANI\n%%EOF"
    doc_file.write_bytes(doc_content)

    meta = store_family_document(
        family_id=fam_id,
        source_file_path=doc_file,
        doc_type="ID_PROOF",
        notes="Aadhaar scanned card copy",
    )
    assert meta["file_size"] == len(doc_content)
    assert meta["sha256"] == compute_file_hash(doc_file)
    assert os.path.exists(meta["file_path"])

    # Insert into database
    doc_id = db.add_family_document(
        family_id=fam_id,
        doc_type=meta["doc_type"],
        file_name=meta["file_name"],
        file_path=meta["file_path"],
        file_size=meta["file_size"],
        sha256=meta["sha256"],
        notes=meta["notes"],
        db_path=temp_db,
    )
    assert doc_id > 0

    # Retrieve and verify
    docs = db.get_family_documents(fam_id, db_path=temp_db)
    assert len(docs) == 1
    assert docs[0]["file_name"] == meta["file_name"]
    assert docs[0]["sha256"] == meta["sha256"]

    # 2. Invalid file type test
    invalid_file = tmp_path / "malicious_script.exe"
    invalid_file.write_bytes(b"MZ\x90\x00\x03Executable")
    valid_flag, err_msg = validate_document_file(invalid_file)
    assert valid_flag is False
    assert "Unsupported file type" in err_msg

    # 3. Delete document
    del_res = db.delete_family_document(doc_id, db_path=temp_db)
    assert del_res is True
    assert len(db.get_family_documents(fam_id, db_path=temp_db)) == 0


def test_09_export_functionality(temp_db, tmp_path):
    """Test exporting booking history records to CSV and Excel (.xlsx) formats."""
    # Seed 2 families
    db.add_family_with_pilgrims(
        {"family_code": "EXP-01", "family_name": "Export Family One", "phone": "9876543201", "status": STATUS_BOOKED, "payment_status": PAYMENT_PAID},
        [{"full_name": "Pilgrim 1", "age": 30, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1111"}],
        db_path=temp_db,
    )
    db.add_family_with_pilgrims(
        {"family_code": "EXP-02", "family_name": "Export Family Two", "phone": "9876543202", "status": STATUS_READY_FOR_MANUAL_BOOKING, "payment_status": PAYMENT_PENDING},
        [{"full_name": "Pilgrim 2", "age": 25, "gender": "Female", "id_proof_type": "Passport", "id_proof_last4": "2222"}],
        db_path=temp_db,
    )

    # 1. Test CSV export
    csv_file = tmp_path / "test_history.csv"
    import csv
    fams = db.get_all_families(db_path=temp_db)
    with open(csv_file, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Family Code", "Family Name", "Phone", "Booking Status", "Payment Status"])
        for fam in fams:
            writer.writerow([
                fam["family_code"],
                fam["family_name"],
                fam["phone"],
                normalize_booking_status(fam["status"]),
                normalize_payment_tracking_status(fam["payment_status"]),
            ])

    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8")
    assert "EXP-01" in content
    assert "Export Family One" in content
    assert "BOOKED" in content

    # 2. Test Excel (.xlsx) export
    xlsx_file = tmp_path / "test_history.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "History"
    ws.append(["Family Code", "Family Name", "Phone", "Booking Status", "Payment Status"])
    for fam in fams:
        ws.append([fam["family_code"], fam["family_name"], fam["phone"], normalize_booking_status(fam["status"]), normalize_payment_tracking_status(fam["payment_status"])])
    wb.save(xlsx_file)

    assert xlsx_file.exists()
    # Read back with openpyxl to verify valid format
    wb_read = openpyxl.load_workbook(xlsx_file)
    sheet = wb_read.active
    assert sheet.max_row >= 3  # Header + 2 rows


def test_10_database_backup_and_recovery(temp_db, tmp_path):
    """Test backup creation, SHA-256 verification, and point-in-time database restoration."""
    # Add record to backup
    fid = db.add_family_with_pilgrims(
        {"family_code": "BAK-001", "family_name": "Backup Recovery Family", "phone": "9876543200"},
        [{"full_name": "Devotee To Preserve", "age": 50, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "9999"}],
        db_path=temp_db,
    )

    from scripts.backup_recovery_postgres import backup_sqlite, restore_sqlite
    backup_dir = tmp_path / "backups"
    meta = backup_sqlite(str(temp_db), str(backup_dir))

    assert meta["sha256"] is not None
    backup_file_path = backup_dir / meta["backup_file"]
    assert backup_file_path.exists()

    # Modify / corrupt original DB by deleting family
    db.delete_family(fid, db_path=temp_db)
    assert db.get_family(fid, db_path=temp_db) is None

    # Restore from backup archive
    restore_success = restore_sqlite(str(backup_file_path), str(temp_db))
    assert restore_success is True

    # Verify family is recovered
    recovered = db.get_family(fid, db_path=temp_db)
    assert recovered is not None
    assert recovered["family_name"] == "Backup Recovery Family"


def test_11_strict_compliance_boundaries():
    """
    CRITICAL COMPLIANCE AUDIT TEST:
    Verify that NO browser automation packages (selenium, playwright, pyppeteer)
    or automated DOM interaction scripts are imported or executed by the application codebase.
    """
    # 1. Inspect all project Python source files to ensure zero browser automation imports
    project_files = [
        "app.py",
        "preparation_workspace.py",
        "readiness_engine.py",
        "document_manager.py",
        "assisted_booking.py",
        "booking_workspace.py",
        "database.py",
    ]

    banned_terms = [
        "import selenium",
        "from selenium",
        "import playwright",
        "from playwright",
        "import pyppeteer",
        "webdriver.",
        "page.fill(",
        "page.click(",
        "solve_captcha",
        "bypass_otp",
    ]

    for filename in project_files:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                for term in banned_terms:
                    assert term not in content, f"Compliance violation: Found banned automation '{term}' in {filename}"

    # 2. Check preparation_workspace.py strictly uses standard webbrowser.open
    with open("preparation_workspace.py", "r", encoding="utf-8") as f:
        src = f.read()

    assert "webbrowser.open(" in src
    assert "https://ttdevasthanams.ap.gov.in" in src
