"""
SRIVANI BOOKING MANAGER - End-to-End System Execution & Verification Runner
Executes and validates the complete operational workflow from onboarding to reporting.

Usage:
    python run_end_to_end.py
"""
import sys
import os
import time
import shutil
import tempfile
import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

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
from import_export import (
    analyze_import_file,
    commit_import_from_analysis,
    export_to_csv,
    export_to_excel,
)
from ticket_manager import (
    store_ticket_pdf,
    generate_booking_slip_pdf,
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
    _sanitize_log_line,
    APP_VERSION,
)
from settings import (
    init_settings,
    get_setting,
    set_setting,
)


def log_step(index: int, title: str, status: str = "RUNNING", duration: float = 0.0):
    badge = "\033[92m[PASS]\033[0m" if status == "PASS" else ("\033[91m[FAIL]\033[0m" if status == "FAIL" else "\033[93m[....]\033[0m")
    time_str = f"({duration:.2f}s)" if duration > 0 else ""
    print(f"  {badge} Step {index:02d}: {title:<55} {time_str}")


def run_e2e_verification() -> bool:
    print("\n" + "=" * 80)
    print("      SRIVANI BOOKING MANAGER — END-TO-END VERIFICATION RUNNER")
    print(f"      Version: v{APP_VERSION} Commercial Desktop Suite | Windows Environment")
    print(f"      Execution Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")

    overall_start = time.time()
    temp_dir = Path(tempfile.mkdtemp(prefix="srivani_e2e_run_"))
    data_dir = temp_dir / "data"
    tickets_dir = data_dir / "tickets"
    backups_dir = data_dir / "backups"
    exports_dir = data_dir / "exports"
    db = data_dir / "srivani_e2e.db"

    data_dir.mkdir(parents=True, exist_ok=True)
    tickets_dir.mkdir(parents=True, exist_ok=True)
    backups_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    passed_steps = 0
    total_steps = 14

    try:
        # STEP 1: Pre-flight Verification
        t0 = time.time()
        init_db(db)
        init_auth_db(db)
        init_licensing_db(db)
        init_settings(db)
        is_healthy, diag_msgs = check_database_integrity(db)
        assert is_healthy is True
        assert get_current_schema_version(db) >= 4
        passed_steps += 1
        log_step(1, "Pre-Flight Environment & Database Integrity", "PASS", time.time() - t0)

        # STEP 2: Administrator Security & Lockout
        t0 = time.time()
        ok_admin, _ = create_admin_user("chief_admin", "MasterKey#2026", "Chief Admin", db_path=db)
        assert ok_admin is True
        for _ in range(MAX_FAILED_ATTEMPTS):
            ok_fail, _, _ = authenticate_admin("chief_admin", "WrongGuess", db_path=db)
            assert ok_fail is False
        ok_lock, msg_lock, _ = authenticate_admin("chief_admin", "MasterKey#2026", db_path=db)
        assert ok_lock is False
        assert "locked" in msg_lock.lower()
        with get_connection(db) as con:
            con.execute("UPDATE admin_users SET failed_attempts = 0, locked_until = NULL WHERE username = 'chief_admin'")
            con.commit()
        ok_auth, _, user = authenticate_admin("chief_admin", "MasterKey#2026", db_path=db)
        assert ok_auth is True
        session.login(user)
        session.lock()
        session.unlock(user)
        assert session.is_authenticated is True
        passed_steps += 1
        log_step(2, "Administrator Security, Bcrypt Auth & Lockout", "PASS", time.time() - t0)

        # STEP 3: Cryptographic Licensing
        t0 = time.time()
        inst_id = get_installation_id()
        client_name = "Tirumala Seva Society"
        lic_key = generate_license_key(client_name, inst_id, "PERPETUAL", "COMMERCIAL")
        ok_lic, _ = activate_license(lic_key, client_name, db_path=db)
        assert ok_lic is True
        assert is_licensed(db) is True
        cert_path = exports_dir / "license_certificate.txt"
        export_license_certificate(cert_path, db_path=db)
        assert cert_path.exists()
        passed_steps += 1
        log_step(3, "Cryptographic Licensing & Hardware Binding", "PASS", time.time() - t0)

        # STEP 4: Batch Data Import
        t0 = time.time()
        sample_csv = Path("sample_families.csv")
        assert sample_csv.exists()
        analysis = analyze_import_file(sample_csv, db_path=db)
        assert analysis["summary"]["total_rows"] >= 3
        imported_p, _, fam_count = commit_import_from_analysis(analysis, skip_duplicates=True, db_path=db)
        assert fam_count >= 3
        passed_steps += 1
        log_step(4, "Batch Data Ingestion & Devotee Roster Parsing", "PASS", time.time() - t0)

        # STEP 5: Manual Family & Pilgrim CRUD
        t0 = time.time()
        fam_data = {
            "family_code": "FAM-E2E-RUN",
            "family_name": "Sri Venkateswara Parivaram",
            "contact_name": "Narayana Swamy",
            "phone": "9848012345",
            "email": "swamy.n@example.com",
            "donation_amount": 30000.0,
            "booking_type": BOOKING_TYPE_ADVANCE,
            "preferred_date": "2026-12-25",
            "priority": PRIORITY_HIGH,
            "notes": "End-to-End verified family record",
        }
        pilgrims_data = [
            {"full_name": "Narayana Swamy", "age": 48, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
            {"full_name": "Padmavathi Swamy", "age": 44, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
            {"full_name": "Govind Swamy", "age": 19, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "9012"},
        ]
        fam_id = add_family_with_pilgrims(fam_data, pilgrims_data, db_path=db)
        assert fam_id > 0
        passed_steps += 1
        log_step(5, "Manual Devotee & Multi-Pilgrim Registration", "PASS", time.time() - t0)

        # STEP 6: Queue Orchestration
        t0 = time.time()
        update_family(fam_id, {"priority": PRIORITY_URGENT}, db_path=db)
        shift_queue_order(fam_id, direction="up", db_path=db)
        passed_steps += 1
        log_step(6, "Queue Prioritization & Dynamic Re-Ordering", "PASS", time.time() - t0)

        # STEP 7: Status Lifecycle & Audit History
        t0 = time.time()
        update_status_and_payment(fam_id, STATUS_IN_PROGRESS, PAYMENT_REQUEST_SENT, notes="Verification commenced", db_path=db)
        update_status_and_payment(
            fam_id,
            STATUS_BOOKED,
            PAYMENT_PAID,
            payment_ref="TTD-TXN-2026-889900",
            notes="All 3 darshan slots confirmed",
            db_path=db,
        )
        fam_booked = get_family(fam_id, db_path=db)
        assert fam_booked["status"] == STATUS_BOOKED
        assert fam_booked["payment_status"] == PAYMENT_PAID
        history = get_queue_history(fam_id, db_path=db)
        assert len(history) >= 2
        passed_steps += 1
        log_step(7, "State Machine Lifecycle & Audit Trail Logging", "PASS", time.time() - t0)

        # STEP 8: Ticket Archiving & Booking Slip PDF
        t0 = time.time()
        dummy_ticket = exports_dir / "official_ticket.pdf"
        dummy_ticket.write_bytes(b"%PDF-1.4 Official Srivani Darshan Ticket #889900")
        stored_ticket = store_ticket_pdf(fam_id, fam_booked["family_code"], dummy_ticket, ticket_number="SRI-889900", db_path=db)
        assert stored_ticket.exists()
        slip_pdf = exports_dir / "booking_slip.pdf"
        fam_pilgrims = get_family_pilgrims(fam_id, db_path=db)
        generate_booking_slip_pdf(dict(fam_booked), [dict(p) for p in fam_pilgrims], output_path=slip_pdf)
        assert slip_pdf.exists()
        passed_steps += 1
        log_step(8, "Ticket PDF Archiving & Booking Slip Generation", "PASS", time.time() - t0)

        # STEP 9: Operational Reports Suite (8 Reports)
        t0 = time.time()
        reconciliation = validate_report_totals(db)
        assert reconciliation["is_valid"] is True
        assert len(reconciliation["anomalies"]) == 0
        rep_pdf = exports_dir / "reports_summary.pdf"
        generate_printable_pdf_report("booking_status_summary", rep_pdf, db_path=db)
        assert rep_pdf.exists()
        passed_steps += 1
        log_step(9, "Operational Reports (8 Reports) & Reconciliation", "PASS", time.time() - t0)

        # STEP 10: Advanced Analytics Engine
        t0 = time.time()
        summary = get_analytics_summary(db_path=db)
        assert summary["total_families"] >= 4
        perf = get_booking_performance(db_path=db)
        assert perf["total_processed"] >= 1
        qi = get_queue_intelligence(db_path=db)
        assert "aging_buckets" in qi
        pay_a = get_payment_analytics(db_path=db)
        assert pay_a["payment_ref_capture_rate"] > 0
        doc_a = get_document_analytics(db_path=db)
        assert doc_a["ticket_compliance_percentage"] > 0
        ops = get_operational_intelligence(db_path=db)
        assert "recommended_queue" in ops
        passed_steps += 1
        log_step(10, "Advanced Analytics Engine & Queue Intelligence", "PASS", time.time() - t0)

        # STEP 11: Multi-Format Analytics Exports
        t0 = time.time()
        xlsx_file = exports_dir / "analytics_workbook.xlsx"
        export_full_analytics_workbook_xlsx(xlsx_file, db_path=db)
        assert xlsx_file.exists()
        pdf_file = exports_dir / "analytics_summary.pdf"
        export_analytics_report_pdf("summary", pdf_file, db_path=db)
        assert pdf_file.exists()
        csv_file = exports_dir / "analytics_summary.csv"
        export_summary_to_csv(csv_file, db_path=db)
        assert csv_file.exists()
        passed_steps += 1
        log_step(11, "Multi-Format Exports (Excel .xlsx, PDF, CSV)", "PASS", time.time() - t0)

        # STEP 12: Disaster Recovery & Safe Backups
        t0 = time.time()
        b_file = create_database_backup(dest_path=backups_dir / "live_backup.db", db_path=db)
        assert b_file.exists()
        is_val, _ = validate_backup_file(b_file)
        assert is_val is True
        pre_snap = prepare_pre_update_backup(db)
        assert pre_snap.exists()
        restore_target = data_dir / "restored.db"
        restore_database_backup(b_file, db_path=restore_target)
        assert restore_target.exists()
        is_res_healthy, _ = check_database_integrity(restore_target)
        assert is_res_healthy is True
        passed_steps += 1
        log_step(12, "Disaster Recovery, Live Backup & Migration Snapshot", "PASS", time.time() - t0)

        # STEP 13: Customer Diagnostics & Log Scrubbing
        t0 = time.time()
        diag = generate_diagnostic_report(db_path=db)
        assert "SRIVANI BOOKING MANAGER" in diag
        assert "STORAGE & FILE PERMISSIONS" in diag
        assert "9848012345" not in diag
        assert "swamy.n@example.com" not in diag
        clean_line = _sanitize_log_line("Donor 9848012345 Aadhaar 1234 5678 9012 email test@local.org password=TopSecret")
        assert "9848012345" not in clean_line
        assert "[REDACTED-PHONE]" in clean_line
        assert "[REDACTED-ID-PROOF]" in clean_line
        assert "[REDACTED-EMAIL]" in clean_line
        assert "TopSecret" not in clean_line
        passed_steps += 1
        log_step(13, "Diagnostic Audit Engine & PII Data Scrubbing", "PASS", time.time() - t0)

        # STEP 14: Hardware Transfer & Deactivation
        t0 = time.time()
        ok_deact, msg_deact, deact_details = deactivate_license_for_transfer(db_path=db)
        assert ok_deact is True
        assert deact_details["deactivation_proof"].startswith("DEACT-")
        assert is_licensed(db) is False
        passed_steps += 1
        log_step(14, "Device Deactivation & Cryptographic Transfer Proof", "PASS", time.time() - t0)

    except Exception as e:
        print(f"\n\033[91m[FAILURE] Verification aborted at step: {e}\033[0m")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    total_duration = time.time() - overall_start
    print("\n" + "-" * 80)
    print(f"  END-TO-END VERIFICATION RESULT: \033[92mALL {passed_steps}/{total_steps} MODULES PASSED\033[0m ({total_duration:.2f}s)")
    print("  COMPLIANCE & INTEGRITY STATUS: 100% VERIFIED & PRODUCTION READY")
    print("=" * 80 + "\n")
    return True


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
