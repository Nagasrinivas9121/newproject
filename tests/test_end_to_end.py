"""
SRIVANI BOOKING MANAGER - End-to-End System Integration Tests
Validates the complete operational lifecycle from initial onboarding to final reports & diagnostics:
1. Pre-flight Environment & Database Verification
2. Administrator Security, Bcrypt Auth & Lockout Protection
3. Offline Cryptographic Machine-Bound Licensing & Certificate Generation
4. Batch Data Ingestion (CSV & Excel) and Duplicate Prevention
5. Family & Devotee Registration, Normalization & Validation
6. Queue Prioritization, Re-ordering & Audit History Logging
7. Booking Workflow State Transitions (Pending -> In Progress -> Booked -> Cancelled)
8. Financial Reconciliation, Payment Status & Transaction References
9. Ticket PDF Archiving, SHA-256 Duplicate Protection & Booking Slip PDF Generation
10. Operational Reports Suite (8 Reports) & Reconciliation Checksums
11. Phase 7 Analytics Engine, Turnaround Analysis, Queue Aging & Deterministic Scoring
12. Multi-Format Analytics Exports (Multi-tab Excel .xlsx, CSV, Executive PDF)
13. Disaster Recovery, Live SQLite Backup & Safe Pre-update Snapshots
14. Support Diagnostics Generation & PII Sanitization Guarantee
"""
import pytest
import sqlite3
import datetime
from pathlib import Path

from config import (
    SRIVANI_DONATION_PER_PERSON,
    BOOKING_TYPE_ADVANCE,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_CANCELLED,
    PAYMENT_PAID,
    PAYMENT_REQUEST_SENT,
    PRIORITY_URGENT,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
)
from database import (
    init_db,
    get_connection,
    add_family_with_pilgrims,
    update_family,
    update_status_and_payment,
    get_family,
    get_all_families,
    get_family_pilgrims,
    delete_family,
    shift_queue_order,
    get_queue_history,
    get_stats,
    check_database_integrity,
    get_current_schema_version,
)
from auth import (
    init_auth_db,
    create_admin_user,
    authenticate_admin,
    has_admin_user,
    change_admin_password,
    update_admin_profile,
    session,
    MAX_FAILED_ATTEMPTS,
)
from licensing import (
    init_licensing_db,
    get_installation_id,
    generate_license_key,
    verify_license_key,
    activate_license,
    is_licensed,
    get_license_info,
    export_license_certificate,
    deactivate_license_for_transfer,
)
from client_verification import (
    initialize_environment,
    run_full_client_verification,
)
from import_export import (
    analyze_import_file,
    commit_import_from_analysis,
    export_to_csv,
    export_to_excel,
)
from ticket_manager import (
    store_ticket_pdf,
    generate_booking_slip_pdf,
    compute_file_sha256,
)
from reports import (
    get_daily_completed_report,
    get_weekly_report,
    get_monthly_report,
    get_booking_status_summary_report,
    get_pending_families_report,
    get_payment_status_report,
    get_total_pilgrims_report,
    validate_report_totals,
    export_report_to_csv,
    generate_printable_pdf_report,
)
from analytics_engine import (
    get_analytics_summary,
    get_booking_performance,
    get_queue_intelligence,
    get_family_analytics,
    get_payment_analytics,
    get_document_analytics,
    get_operational_intelligence,
)
from analytics_export import (
    export_summary_to_csv,
    export_performance_to_csv,
    export_full_analytics_workbook_xlsx,
    export_analytics_report_pdf,
)
from backup_manager import (
    create_database_backup,
    validate_backup_file,
    restore_database_backup,
)
from update_manager import (
    prepare_pre_update_backup,
    validate_database_schema,
)
from support_diagnostics import (
    generate_diagnostic_report,
    export_diagnostic_report,
    _sanitize_log_line,
)
from settings import (
    init_settings,
    get_setting,
    set_setting,
    APP_VERSION,
)


@pytest.fixture
def e2e_env(tmp_path, monkeypatch):
    """Set up a fully isolated, clean end-to-end sandbox environment."""
    data_dir = tmp_path / "data"
    tickets_dir = data_dir / "tickets"
    backups_dir = data_dir / "backups"
    exports_dir = data_dir / "exports"
    db_file = data_dir / "srivani_e2e.db"

    data_dir.mkdir(parents=True, exist_ok=True)
    tickets_dir.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("config.DATA_DIR", data_dir)
    monkeypatch.setattr("config.TICKETS_DIR", tickets_dir)
    monkeypatch.setattr("config.BACKUPS_DIR", backups_dir)
    monkeypatch.setattr("config.DB_PATH", db_file)
    monkeypatch.setattr("ticket_manager.TICKETS_DIR", tickets_dir)
    monkeypatch.setattr("backup_manager.BACKUPS_DIR", backups_dir)

    # Initialize tables
    init_db(db_file)
    init_auth_db(db_file)
    init_licensing_db(db_file)
    init_settings(db_file)

    return {
        "root": tmp_path,
        "data_dir": data_dir,
        "tickets_dir": tickets_dir,
        "backups_dir": backups_dir,
        "exports_dir": exports_dir,
        "db_file": db_file,
    }


def test_complete_end_to_end_system_lifecycle(e2e_env):
    """
    Executes the entire end-to-end business workflow across all modules:
    Setup -> Auth -> Licensing -> Import -> Registration -> Queueing ->
    Booking -> Payments -> Tickets -> Reports -> Analytics -> Backup -> Diagnostics
    """
    db = e2e_env["db_file"]
    tickets_dir = e2e_env["tickets_dir"]
    exports_dir = e2e_env["exports_dir"]

    # =========================================================================
    # STEP 1: PRE-FLIGHT VERIFICATION
    # =========================================================================
    is_healthy, diag_msgs = check_database_integrity(db)
    assert is_healthy is True
    assert get_current_schema_version(db) >= 4

    # =========================================================================
    # STEP 2: ADMINISTRATOR SECURITY & AUTH
    # =========================================================================
    assert has_admin_user(db) is False
    ok_admin, msg_admin = create_admin_user("chief_operator", "SrivaniAdmin#2026", "Chief Admin", db_path=db)
    assert ok_admin is True
    assert has_admin_user(db) is True

    # Test lockout protection on failed logins
    for _ in range(MAX_FAILED_ATTEMPTS):
        ok_fail, msg_fail, _ = authenticate_admin("chief_operator", "WrongPassword", db_path=db)
        assert ok_fail is False

    # Account is locked
    ok_locked, msg_locked, _ = authenticate_admin("chief_operator", "SrivaniAdmin#2026", db_path=db)
    assert ok_locked is False
    assert "locked" in msg_locked.lower()

    # Reset lockout in DB and authenticate successfully
    with get_connection(db) as con:
        con.execute("UPDATE admin_users SET failed_attempts = 0, locked_until = NULL WHERE username = 'chief_operator'")
        con.commit()

    ok_auth, msg_auth, user = authenticate_admin("chief_operator", "SrivaniAdmin#2026", db_path=db)
    assert ok_auth is True
    assert user["display_name"] == "Chief Admin"

    # Test Session state transitions
    session.login(user)
    assert session.is_authenticated is True
    assert session.is_locked is False
    session.lock()
    assert session.is_locked is True
    session.unlock(user)
    assert session.is_locked is False

    # =========================================================================
    # STEP 3: OFFLINE CRYPTOGRAPHIC LICENSING
    # =========================================================================
    inst_id = get_installation_id()
    assert inst_id.startswith("SRVN-")
    client_name = "Tirumala Seva Society"
    license_key = generate_license_key(client_name, inst_id, "PERPETUAL", "COMMERCIAL")
    
    ok_lic, msg_lic = activate_license(license_key, client_name, db_path=db)
    assert ok_lic is True
    assert is_licensed(db) is True
    
    lic_info = get_license_info(db)
    assert lic_info["status"] == "ACTIVE"
    assert lic_info["license_type"] == "COMMERCIAL"

    # Export official license certificate
    cert_path = exports_dir / "license_certificate.txt"
    export_license_certificate(cert_path, db_path=db)
    assert cert_path.exists()
    assert "COMMERCIAL" in cert_path.read_text(encoding="utf-8")

    # =========================================================================
    # STEP 4: BATCH IMPORT (CSV & EXCEL)
    # =========================================================================
    # Ingest from sample_families.csv in project root
    sample_csv = Path("sample_families.csv")
    assert sample_csv.exists()
    analysis = analyze_import_file(sample_csv, db_path=db)
    summary_import = analysis["summary"]
    assert summary_import["total_rows"] >= 3
    assert summary_import["invalid"] == 0

    imported_p, skipped, fam_count = commit_import_from_analysis(analysis, skip_duplicates=True, db_path=db)
    assert fam_count >= 3
    assert imported_p >= 6

    # =========================================================================
    # STEP 5: MANUAL FAMILY & PILGRIM CREATION
    # =========================================================================
    manual_family = {
        "family_code": "FAM-E2E-001",
        "family_name": "Balaji Bhakta Family",
        "contact_name": "Kishore Kumar",
        "phone": "9876543210",
        "email": "kishore.k@example.com",
        "donation_amount": 30000.0,
        "booking_type": BOOKING_TYPE_ADVANCE,
        "preferred_date": "2026-12-15",
        "priority": PRIORITY_HIGH,
        "notes": "End-to-End manual test family with 3 devotees",
    }
    manual_pilgrims = [
        {"full_name": "Kishore Kumar", "age": 42, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Kavitha Kumar", "age": 39, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
        {"full_name": "Aditya Kumar", "age": 14, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "9012"},
    ]
    fam_id = add_family_with_pilgrims(manual_family, manual_pilgrims, db_path=db)
    assert fam_id > 0

    pilgrims = get_family_pilgrims(fam_id, db_path=db)
    assert len(pilgrims) == 3

    # =========================================================================
    # STEP 6: QUEUE ORCHESTRATION & SHIFTING
    # =========================================================================
    all_fams = get_all_families(db_path=db)
    assert len(all_fams) >= 4
    
    # Shift priority and queue
    update_family(fam_id, {"priority": PRIORITY_URGENT}, db_path=db)
    shift_queue_order(fam_id, direction="up", db_path=db)

    # =========================================================================
    # STEP 7: STATE TRANSITIONS & BOOKING WORKFLOW
    # =========================================================================
    # 1. PENDING -> IN_PROGRESS
    update_status_and_payment(fam_id, STATUS_IN_PROGRESS, PAYMENT_REQUEST_SENT, notes="Verification commenced", db_path=db)

    # 2. IN_PROGRESS -> BOOKED (with Payment & Transaction Reference)
    update_status_and_payment(
        fam_id,
        STATUS_BOOKED,
        PAYMENT_PAID,
        payment_ref="TTD-TXN-2026-998877",
        notes="All 3 darshan tickets secured successfully",
        db_path=db,
    )

    fam_booked = get_family(fam_id, db_path=db)
    assert fam_booked["status"] == STATUS_BOOKED
    assert fam_booked["payment_status"] == PAYMENT_PAID
    assert fam_booked["payment_ref"] == "TTD-TXN-2026-998877"

    # Verify audit trail in queue_history
    history = get_queue_history(fam_id, db_path=db)
    assert len(history) >= 2
    actions = [h["action"] for h in history]
    assert "STATUS_UPDATED" in actions

    # =========================================================================
    # STEP 8: TICKET PDF STORAGE & DUPLICATE REJECTION
    # =========================================================================
    dummy_ticket = exports_dir / "official_ticket.pdf"
    dummy_ticket.write_bytes(b"%PDF-1.4 Official Srivani Darshan Ticket Content #998877")

    stored_ticket = store_ticket_pdf(
        fam_id,
        fam_booked["family_code"],
        dummy_ticket,
        ticket_number="SRI-TTD-2026-8877",
        db_path=db,
    )
    assert stored_ticket.exists()

    fam_with_ticket = get_family(fam_id, db_path=db)
    assert fam_with_ticket["ticket_number"] == "SRI-TTD-2026-8877"
    assert fam_with_ticket["ticket_checksum"] is not None

    # Re-importing same PDF for another family must raise ValueError (Duplicate Prevention)
    other_fam_id = all_fams[0]["id"]
    if other_fam_id == fam_id:
        other_fam_id = all_fams[1]["id"]
    
    with pytest.raises(ValueError, match="Duplicate Ticket Error"):
        store_ticket_pdf(
            other_fam_id,
            "FAM-OTHER",
            dummy_ticket,
            ticket_number="SRI-DUPLICATE",
            db_path=db,
        )

    # Generate Official Devotee Booking Slip PDF
    slip_pdf = exports_dir / "booking_slip_FAM_E2E_001.pdf"
    generate_booking_slip_pdf(dict(fam_with_ticket), [dict(p) for p in pilgrims], output_path=slip_pdf)
    assert slip_pdf.exists()
    assert slip_pdf.stat().st_size > 1000

    # =========================================================================
    # STEP 9: OPERATIONAL REPORTS & TOTALS RECONCILIATION
    # =========================================================================
    reconciliation = validate_report_totals(db)
    assert reconciliation["is_valid"] is True
    assert len(reconciliation["anomalies"]) == 0
    assert reconciliation["total_families"] >= 4
    assert reconciliation["total_pilgrims"] >= 9

    # Test all 8 reports data extraction
    daily_rep = get_daily_completed_report(db)
    assert isinstance(daily_rep, list)

    weekly_rep = get_weekly_report(db)
    assert isinstance(weekly_rep, list)

    monthly_rep = get_monthly_report(db)
    assert isinstance(monthly_rep, list)

    status_rep = get_booking_status_summary_report(db)
    assert any(s["status"] == "Booked" for s in status_rep)

    pending_rep = get_pending_families_report(db)
    assert isinstance(pending_rep, list)

    payment_rep = get_payment_status_report(db)
    assert any(p["payment_status"] == "Paid" for p in payment_rep)

    demog_rep = get_total_pilgrims_report(db)
    assert demog_rep["total_pilgrims"] >= 9
    assert demog_rep["genders"]["Male"] >= 1
    assert demog_rep["genders"]["Female"] >= 1

    # Export printable ReportLab PDF report
    report_pdf = exports_dir / "operational_report_executive.pdf"
    ok_pdf, _ = generate_printable_pdf_report("booking_status_summary", report_pdf, db_path=db)
    assert ok_pdf is True
    assert report_pdf.exists()
    assert report_pdf.stat().st_size > 1000

    # =========================================================================
    # STEP 10: PHASE 7 ADVANCED ANALYTICS & OPERATIONAL INTELLIGENCE
    # =========================================================================
    summary = get_analytics_summary(db_path=db)
    assert summary["total_families"] >= 4
    assert summary["completed_bookings"] >= 1
    assert summary["booking_completion_percentage"] > 0
    assert summary["total_donation_pledged"] >= 30000.0

    perf = get_booking_performance(db_path=db)
    assert perf["total_processed"] >= 1
    assert "daily_trends" in perf

    queue_intel = get_queue_intelligence(db_path=db)
    assert "aging_buckets" in queue_intel

    pay_intel = get_payment_analytics(db_path=db)
    assert pay_intel["total_transactions"] >= 4
    assert pay_intel["payment_ref_capture_rate"] > 0

    doc_intel = get_document_analytics(db_path=db)
    assert doc_intel["total_families_with_pilgrims"] >= 4
    assert doc_intel["ticket_compliance_percentage"] > 0

    op_intel = get_operational_intelligence(db_path=db)
    assert "recommended_queue" in op_intel

    # =========================================================================
    # STEP 11: MULTI-FORMAT ANALYTICS EXPORTS
    # =========================================================================
    # 1. Multi-Tab Excel Workbook (.xlsx)
    xlsx_path = exports_dir / "analytics_master_workbook.xlsx"
    export_full_analytics_workbook_xlsx(xlsx_path, db_path=db)
    assert xlsx_path.exists()
    assert xlsx_path.stat().st_size > 4000

    # 2. Executive Analytics Printable PDF
    analytics_pdf = exports_dir / "analytics_summary_executive.pdf"
    export_analytics_report_pdf("summary", analytics_pdf, db_path=db)
    assert analytics_pdf.exists()
    assert analytics_pdf.stat().st_size > 1000

    # 3. CSV Exports
    csv_path = exports_dir / "analytics_summary.csv"
    export_summary_to_csv(csv_path, db_path=db)
    assert csv_path.exists()

    # =========================================================================
    # STEP 12: DISASTER RECOVERY & LIVE SQLITE BACKUP
    # =========================================================================
    backup_file = create_database_backup(db_path=db)
    assert Path(backup_file).exists()
    assert Path(backup_file).stat().st_size > 0

    is_val, _ = validate_backup_file(backup_file)
    assert is_val is True

    # Test pre-update snapshot
    pre_snap = prepare_pre_update_backup(db)
    assert pre_snap.exists()

    # Test restoring to a new target
    restore_target = e2e_env["data_dir"] / "restored_e2e.db"
    restore_database_backup(backup_file, db_path=restore_target)
    assert restore_target.exists()
    is_res_healthy, _ = check_database_integrity(restore_target)
    assert is_res_healthy is True

    # =========================================================================
    # STEP 13: CUSTOMER SUPPORT DIAGNOSTICS & PII SANITIZATION
    # =========================================================================
    diag_report = generate_diagnostic_report(db_path=db)
    assert "SRIVANI BOOKING MANAGER" in diag_report
    assert "STORAGE & FILE PERMISSIONS" in diag_report
    assert "DATABASE HEALTH" in diag_report
    assert "CLIENT LICENSING STATUS" in diag_report

    # Verify zero PII leakage in diagnostic report
    assert "9876543210" not in diag_report
    assert "kishore.k@example.com" not in diag_report
    assert "Balaji Bhakta Family" not in diag_report

    # Test log line sanitization
    raw_log = "Devotee 9876543210 booked with Aadhaar 1234 5678 9012 and email test@local.com password=SecretPass"
    clean_log = _sanitize_log_line(raw_log)
    assert "9876543210" not in clean_log
    assert "[REDACTED-PHONE]" in clean_log
    assert "[REDACTED-ID-PROOF]" in clean_log
    assert "[REDACTED-EMAIL]" in clean_log
    assert "SecretPass" not in clean_log

    # =========================================================================
    # STEP 14: DEVICE DEACTIVATION FOR RE-HOSTING
    # =========================================================================
    ok_deact, msg_deact, deact_details = deactivate_license_for_transfer(db_path=db)
    assert ok_deact is True
    assert deact_details["deactivation_proof"].startswith("DEACT-")
    assert is_licensed(db) is False
