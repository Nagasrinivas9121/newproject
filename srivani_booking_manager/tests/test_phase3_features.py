"""
Unit tests specifically verifying Phase 3 modules and requirements:
- Module 1: Family Booking Workspace & Document Readiness
- Module 4: Ticket PDF Management & Duplicate Checksum Prevention
- Module 5: Payment Tracking & Transaction Reference
- Module 6: Booking History & Audit Timestamps
- Module 7: Reports Generation & CSV Export
- Module 8: Database Backup and Disaster Recovery
"""
import pytest
from pathlib import Path
from database import (
    add_family_with_pilgrims,
    get_family,
    update_status_and_payment,
    assess_document_readiness,
    get_family_booking_history,
)
from ticket_manager import store_ticket_pdf
from reports import (
    get_daily_completed_report,
    get_pending_families_report,
    get_failed_or_unavailable_report,
    get_payment_status_report,
    get_total_pilgrims_report,
    export_report_to_csv,
)
from backup_manager import (
    create_database_backup,
    validate_backup_file,
    list_backups,
    restore_database_backup,
)

def test_document_readiness_assessment():
    # Ready family
    complete_pilgrims = [
        {"full_name": "Ramesh", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Sita", "age": 40, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]
    res1 = assess_document_readiness(complete_pilgrims)
    assert res1["is_ready"] is True
    assert res1["status"] == "Verified Ready"
    assert len(res1["missing_devotees"]) == 0

    # Incomplete family (missing last 4 and missing id proof type)
    incomplete_pilgrims = [
        {"full_name": "Ramesh", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": ""},
        {"full_name": "Sita", "age": 40, "gender": "Female", "id_proof_type": "", "id_proof_last4": "5678"},
    ]
    res2 = assess_document_readiness(incomplete_pilgrims)
    assert res2["is_ready"] is False
    assert res2["status"] == "Incomplete"
    assert len(res2["missing_devotees"]) == 2

    # Empty family
    res3 = assess_document_readiness([])
    assert res3["is_ready"] is False
    assert res3["status"] == "No Devotees"

def test_ticket_pdf_duplicate_prevention(temp_dir, test_db, monkeypatch):
    mock_tickets = temp_dir / "tickets"
    monkeypatch.setattr("ticket_manager.TICKETS_DIR", mock_tickets)

    # Valid dummy PDF
    pdf_file = temp_dir / "ticket_sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")

    f1 = add_family_with_pilgrims({"family_code": "FAM-TCK-1", "family_name": "Fam One"}, [], db_path=test_db)
    f2 = add_family_with_pilgrims({"family_code": "FAM-TCK-2", "family_name": "Fam Two"}, [], db_path=test_db)

    # First import for f1 should succeed
    stored_path = store_ticket_pdf(f1, "FAM-TCK-1", pdf_file, ticket_number="SRI-111", db_path=test_db)
    assert stored_path.exists()

    fam1 = get_family(f1, db_path=test_db)
    assert fam1["ticket_checksum"] is not None
    assert fam1["ticket_number"] == "SRI-111"

    # Attempting to import identical PDF for f2 MUST fail due to duplicate detection
    with pytest.raises(ValueError, match="Duplicate Ticket Error"):
        store_ticket_pdf(f2, "FAM-TCK-2", pdf_file, ticket_number="SRI-222", db_path=test_db)

    # Attempting to re-import identical PDF for f1 without override MUST also fail
    with pytest.raises(ValueError, match="Duplicate Ticket Error"):
        store_ticket_pdf(f1, "FAM-TCK-1", pdf_file, db_path=test_db)

    # Non-PDF file should be rejected
    not_pdf = temp_dir / "fake.txt"
    not_pdf.write_bytes(b"This is not a pdf file")
    with pytest.raises(ValueError, match="Invalid File Format"):
        store_ticket_pdf(f2, "FAM-TCK-2", not_pdf, db_path=test_db)

def test_payment_tracking_and_transaction_ref(test_db):
    fid = add_family_with_pilgrims({"family_name": "Payment Test", "family_code": "FAM-PAY"}, [], db_path=test_db)

    # Update with payment ref
    update_status_and_payment(
        fid,
        status="Booked",
        payment_status="Paid",
        notes="Confirmed via PhonePe UPI",
        payment_ref="UPI-UTR-998877665544",
        db_path=test_db,
    )

    fam = get_family(fid, db_path=test_db)
    assert fam["status"] == "Booked"
    assert fam["payment_status"] == "Paid"
    assert fam["payment_ref"] == "UPI-UTR-998877665544"
    assert fam["notes"] == "Confirmed via PhonePe UPI"

def test_booking_history_retrieval(test_db):
    fid = add_family_with_pilgrims(
        {"family_name": "History Fam", "family_code": "FAM-HIST-01", "booking_type": "Advance", "preferred_date": "2026-12-25"},
        [{"full_name": "Pilgrim A"}, {"full_name": "Pilgrim B"}],
        db_path=test_db,
    )
    update_status_and_payment(fid, "Booked", "Paid", payment_ref="REF-12345", db_path=test_db)

    history = get_family_booking_history(family_id=fid, db_path=test_db)
    assert len(history) == 1
    h = history[0]
    assert h["family_code"] == "FAM-HIST-01"
    assert h["pilgrim_count"] == 2
    assert h["status"] == "Booked"
    assert h["payment_status"] == "Paid"
    assert h["payment_ref"] == "REF-12345"
    assert h["booked_at"] is not None

def test_reports_and_csv_export(temp_dir, test_db):
    # Setup 3 families: 1 Booked, 1 Pending, 1 Unavailable
    f1 = add_family_with_pilgrims(
        {"family_code": "FAM-R1", "family_name": "Booked Fam", "donation_amount": 20000},
        [{"full_name": "P1", "age": 45, "gender": "Male"}, {"full_name": "P2", "age": 12, "gender": "Female"}],
        db_path=test_db,
    )
    update_status_and_payment(f1, "Booked", "Paid", payment_ref="REF-R1", db_path=test_db)

    add_family_with_pilgrims(
        {"family_code": "FAM-R2", "family_name": "Pending Fam", "donation_amount": 10000},
        [{"full_name": "P3", "age": 65, "gender": "Male"}],
        db_path=test_db,
    )

    f3 = add_family_with_pilgrims(
        {"family_code": "FAM-R3", "family_name": "Unavailable Fam", "donation_amount": 10000},
        [{"full_name": "P4", "age": 30, "gender": "Female"}],
        db_path=test_db,
    )
    update_status_and_payment(f3, "Unavailable", "Failed", notes="Quota full", db_path=test_db)

    # 1. Daily completed report
    daily_rep = get_daily_completed_report(db_path=test_db)
    assert len(daily_rep) == 1
    assert daily_rep[0]["families_booked"] == 1
    assert daily_rep[0]["pilgrims_booked"] == 2

    # 2. Pending families report
    pending_rep = get_pending_families_report(db_path=test_db)
    assert len(pending_rep) == 1
    assert pending_rep[0]["family_code"] == "FAM-R2"

    # 3. Failed/Unavailable report
    failed_rep = get_failed_or_unavailable_report(db_path=test_db)
    assert len(failed_rep) == 1
    assert failed_rep[0]["family_code"] == "FAM-R3"

    # 4. Payment status report
    pay_rep = get_payment_status_report(db_path=test_db)
    assert len(pay_rep) >= 2

    # 5. Total pilgrims demographics report
    p_rep = get_total_pilgrims_report(db_path=test_db)
    assert p_rep["total_pilgrims"] == 4
    assert p_rep["age_groups"]["Minors (<18)"] == 1
    assert p_rep["age_groups"]["Adults (18-59)"] == 2
    assert p_rep["age_groups"]["Seniors (60+)"] == 1

    # 6. CSV exports
    for rep_type in ["daily_completed", "pending_families", "failed_or_unavailable", "payment_status", "total_pilgrims"]:
        csv_out = temp_dir / f"report_{rep_type}.csv"
        cnt = export_report_to_csv(rep_type, csv_out, db_path=test_db)
        assert cnt > 0
        assert csv_out.exists()

def test_database_backup_and_restore(temp_dir, test_db, monkeypatch):
    mock_backups = temp_dir / "backups"
    monkeypatch.setattr("backup_manager.BACKUPS_DIR", mock_backups)

    # Populate test_db
    add_family_with_pilgrims({"family_code": "FAM-BKP", "family_name": "Backup Fam"}, [{"full_name": "Devotee B"}], db_path=test_db)

    # 1. Create backup
    backup_file = create_database_backup(db_path=test_db)
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0

    # 2. Validate backup
    is_valid, msg = validate_backup_file(backup_file)
    assert is_valid is True
    assert "Valid Srivani" in msg

    # 3. List backups
    b_list = list_backups()
    assert len(b_list) == 1
    assert b_list[0]["filename"] == backup_file.name

    # 4. Modify test_db
    add_family_with_pilgrims({"family_code": "FAM-NEW-AFTER-BKP", "family_name": "New Fam"}, [], db_path=test_db)
    assert get_family_booking_history(db_path=test_db)[0]["family_code"] == "FAM-NEW-AFTER-BKP"

    # 5. Restore database backup
    safety_snap = restore_database_backup(backup_file, db_path=test_db)
    assert safety_snap is not None
    assert safety_snap.exists()

    # Verify restored state: FAM-NEW-AFTER-BKP should not exist in restored DB
    history_after_restore = get_family_booking_history(db_path=test_db)
    codes = [h["family_code"] for h in history_after_restore]
    assert "FAM-BKP" in codes
    assert "FAM-NEW-AFTER-BKP" not in codes
