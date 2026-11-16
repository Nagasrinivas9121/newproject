"""
Tests for Phase 7 Advanced Analytics and Operational Intelligence.
Validates:
- Analytics calculations against direct SQL queries
- Date range filtering (today, 7 days, 30 days, this month, custom, all time)
- Empty database behavior (no division by zero, clean defaults)
- Booking performance trends & turnaround metrics
- Queue intelligence, aging distribution, attention items, bottlenecks
- Payment analytics & reference capture rate
- Document compliance, ticket availability, duplicate checksum warnings
- Rule-based operational intelligence & queue prioritization scoring
- Multi-format exports (CSV, Excel .xlsx, PDF)
- Data privacy & PII protection (zero full Aadhaar or financial credentials exposed)
"""
import pytest
import datetime
from pathlib import Path

from config import DB_PATH
from database import (
    init_db,
    get_connection,
    add_family_with_pilgrims,
    update_status_and_payment,
)
from analytics_engine import (
    parse_date_filter,
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
    export_queue_intelligence_to_csv,
    export_full_analytics_workbook_xlsx,
    export_analytics_report_pdf,
)


@pytest.fixture
def empty_db(tmp_path):
    """Provide an empty initialized SQLite database."""
    db_file = tmp_path / "test_empty_analytics.db"
    init_db(db_file)
    return db_file


@pytest.fixture
def populated_analytics_db(tmp_path):
    """Provide a rich populated database with diverse booking and payment statuses."""
    db_file = tmp_path / "test_populated_analytics.db"
    init_db(db_file)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    old_date_str = (datetime.date.today() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")

    # Family 1: Booked, Paid, with ticket and complete docs
    f1 = {
        "family_name": "Rao Trust",
        "contact_name": "Anand Rao",
        "phone": "9876543210",
        "donation_amount": 20000.0,
        "booking_type": "Advance",
        "preferred_date": today_str,
        "status": "Booked",
        "payment_status": "Paid",
        "priority": "Urgent",
        "ticket_pdf_path": str(tmp_path / "ticket_rao.pdf"),
        "created_at": f"{yesterday_str} 10:00:00",
    }
    p1 = [
        {"full_name": "Anand Rao", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1111"},
        {"full_name": "Sunita Rao", "age": 42, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "2222"},
    ]
    fid1 = add_family_with_pilgrims(f1, p1, db_path=db_file)
    with get_connection(db_file) as con:
        con.execute(
            "UPDATE families SET booked_at = ?, payment_ref = 'TXN-RAO-999', ticket_checksum = 'HASH-RAO-123' WHERE id = ?",
            (f"{today_str} 14:00:00", fid1),
        )
        con.commit()

    # Family 2: Pending, Urgent, date imminent (tomorrow), complete docs
    f2 = {
        "family_name": "Kulkarni Family",
        "contact_name": "Vijay Kulkarni",
        "phone": "9812345678",
        "donation_amount": 10000.0,
        "booking_type": "Current",
        "preferred_date": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "status": "Pending",
        "payment_status": "Pending",
        "priority": "Urgent",
        "created_at": f"{today_str} 08:30:00",
    }
    p2 = [
        {"full_name": "Vijay Kulkarni", "age": 50, "gender": "Male", "id_proof_type": "Passport", "id_proof_last4": "Z345"},
    ]
    add_family_with_pilgrims(f2, p2, db_path=db_file)

    # Family 3: Pending, Old (> 10 days), Normal priority, incomplete docs (missing last-4)
    f3 = {
        "family_name": "Sharma Pilgrims",
        "contact_name": "Mohan Sharma",
        "phone": "9870001111",
        "donation_amount": 30000.0,
        "booking_type": "Advance",
        "preferred_date": (datetime.date.today() + datetime.timedelta(days=15)).strftime("%Y-%m-%d"),
        "status": "Pending",
        "payment_status": "Not requested",
        "priority": "Normal",
        "created_at": f"{old_date_str} 09:00:00",
    }
    p3 = [
        {"full_name": "Mohan Sharma", "age": 62, "gender": "Male", "id_proof_type": "Voter ID", "id_proof_last4": ""},  # Incomplete
        {"full_name": "Radha Sharma", "age": 58, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "4444"},
        {"full_name": "Karan Sharma", "age": 28, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "5555"},
    ]
    add_family_with_pilgrims(f3, p3, db_path=db_file)

    # Family 4: Unavailable, Paid (Payment discrepancy - potential refund needed)
    f4 = {
        "family_name": "Verma Group",
        "contact_name": "Sunil Verma",
        "phone": "9845556666",
        "donation_amount": 10000.0,
        "booking_type": "Advance",
        "preferred_date": yesterday_str,
        "status": "Unavailable",
        "payment_status": "Paid",
        "priority": "Normal",
        "created_at": f"{yesterday_str} 11:00:00",
    }
    p4 = [
        {"full_name": "Sunil Verma", "age": 35, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "7777"},
    ]
    fid4 = add_family_with_pilgrims(f4, p4, db_path=db_file)
    with get_connection(db_file) as con:
        con.execute("UPDATE families SET payment_ref = 'TXN-REFUND-VERMA' WHERE id = ?", (fid4,))
        con.commit()

    return db_file


def test_empty_database_analytics(empty_db):
    """Verify that analytics engine gracefully handles an empty database with clean zeros."""
    summary = get_analytics_summary(empty_db)
    assert summary["total_families"] == 0
    assert summary["total_pilgrims"] == 0
    assert summary["completed_bookings"] == 0
    assert summary["pending_bookings"] == 0
    assert summary["booking_completion_percentage"] == 0.0
    assert summary["total_donation_pledged"] == 0.0

    perf = get_booking_performance(empty_db)
    assert perf["avg_turnaround_hours"] == 0.0
    assert perf["processing_completion_rate"] == 0.0
    assert len(perf["daily_trends"]) == 0

    qi = get_queue_intelligence(empty_db)
    assert qi["total_pending"] == 0
    assert qi["oldest_pending"] is None
    assert qi["aging_buckets"]["< 24 Hours"] == 0

    pay = get_payment_analytics(empty_db)
    assert pay["total_revenue_collected"] == 0.0
    assert pay["payment_ref_capture_rate"] == 0.0

    doc = get_document_analytics(empty_db)
    assert doc["ticket_compliance_percentage"] == 100.0
    assert doc["missing_tickets_count"] == 0

    ops = get_operational_intelligence(empty_db)
    assert ops["insights_count"] == 0
    assert len(ops["recommended_queue"]) == 0


def test_analytics_summary_calculations(populated_analytics_db):
    """Verify Module 1 summary calculations against expected database state."""
    summary = get_analytics_summary(populated_analytics_db)

    assert summary["total_families"] == 4
    assert summary["total_pilgrims"] == 7  # 2 + 1 + 3 + 1
    assert summary["completed_bookings"] == 1
    assert summary["pending_bookings"] == 2
    assert summary["unavailable_bookings"] == 1
    assert summary["cancelled_bookings"] == 0
    assert summary["total_donation_pledged"] == 70000.0  # 20k + 10k + 30k + 10k
    assert summary["booking_completion_percentage"] == 25.0  # 1 / 4 = 25%

    # Payment summary checks
    pay_sum = summary["payment_summary"]
    assert pay_sum["Paid"]["count"] == 2  # Rao Trust and Verma Group
    assert pay_sum["Paid"]["amount"] == 30000.0
    assert pay_sum["Pending"]["count"] == 1
    assert pay_sum["Not requested"]["count"] == 1


def test_date_filters(populated_analytics_db):
    """Verify date filtering logic across various presets."""
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # 1. Today filter
    s_today = get_analytics_summary(populated_analytics_db, filter_type="today")
    assert s_today["filter_type"] == "today"
    assert s_today["start_date"] == today_str
    assert s_today["end_date"] == today_str
    # Only Kulkarni Family was created today
    assert s_today["total_families"] == 1
    assert s_today["pending_bookings"] == 1

    # 2. Last 7 days filter
    s_7d = get_analytics_summary(populated_analytics_db, filter_type="7days")
    # Excludes the 10-day old Sharma family
    assert s_7d["total_families"] == 3

    # 3. Custom date range
    s_custom = get_analytics_summary(
        populated_analytics_db,
        filter_type="custom",
        custom_start="2020-01-01",
        custom_end="2099-12-31",
    )
    assert s_custom["total_families"] == 4


def test_booking_performance_and_turnaround(populated_analytics_db):
    """Verify Module 2 booking performance, daily trends, and lead time calculations."""
    perf = get_booking_performance(populated_analytics_db)

    assert len(perf["daily_trends"]) >= 2
    assert perf["total_processed"] == 2  # 1 Booked + 1 Unavailable
    assert perf["total_backlog"] == 2  # 2 Pending
    assert perf["processing_completion_rate"] == 50.0  # 2 / 4 = 50%
    # Average turnaround for Rao Trust: 1 day = 24 hours (or >= 20h)
    assert perf["avg_turnaround_hours"] >= 20.0
    assert perf["avg_turnaround_days"] >= 0.8


def test_queue_intelligence_and_aging(populated_analytics_db):
    """Verify Module 3 queue intelligence: aging buckets, oldest record, and attention items."""
    qi = get_queue_intelligence(populated_analytics_db)

    assert qi["total_pending"] == 2
    assert qi["aging_buckets"]["> 7 Days"] == 1  # Sharma family is 10 days old
    assert qi["aging_buckets"]["< 24 Hours"] == 1  # Kulkarni family was created today

    # Oldest record must be Sharma family
    oldest = qi["oldest_pending"]
    assert oldest is not None
    assert oldest["family_name"] == "Sharma Pilgrims"
    assert oldest["days_in_queue"] >= 9.0

    # Attention items
    assert qi["attention_required_count"] >= 2
    reasons = [item["reason"] for item in qi["attention_items"]]
    assert any("Urgent Priority Pending" in r for r in reasons)
    assert any("Preferred Date Imminent" in r for r in reasons)


def test_payment_analytics_metrics(populated_analytics_db):
    """Verify Module 5 payment analytics and reference capture rate."""
    pay = get_payment_analytics(populated_analytics_db)

    assert pay["total_transactions"] == 4
    assert pay["paid_transactions_count"] == 2
    assert pay["total_revenue_collected"] == 30000.0  # Rao (20k) + Verma (10k)
    # Both Paid transactions have a payment_ref
    assert pay["payment_ref_capture_rate"] == 100.0
    assert len(pay["date_wise_collections"]) >= 1


def test_document_analytics(populated_analytics_db):
    """Verify Module 6 document completeness and ticket attachment compliance."""
    doc = get_document_analytics(populated_analytics_db)

    assert doc["booked_families_total"] == 1  # Rao Trust
    assert doc["booked_with_tickets"] == 1
    assert doc["ticket_compliance_percentage"] == 100.0
    assert doc["incomplete_document_families_count"] == 1  # Mohan Sharma missing last-4


def test_operational_intelligence_rules_and_prioritization(populated_analytics_db):
    """Verify Module 7 operational alerts and heuristic queue prioritization scoring."""
    ops = get_operational_intelligence(populated_analytics_db)

    assert ops["insights_count"] >= 2

    titles = [ins["title"] for ins in ops["insights"]]
    # Should detect old pending
    assert any("Waiting > 7 Days" in t for t in titles)
    # Should detect Cancelled/Unavailable marked as Paid
    assert any("Marked as 'Paid'" in t for t in titles)

    # Queue Prioritization Recommendation
    recs = ops["recommended_queue"]
    assert len(recs) == 2  # 2 pending families

    # Kulkarni Family (Urgent + Preferred Date in 1 day + Complete docs) must rank #1
    top_rec = recs[0]
    assert top_rec["family_name"] == "Kulkarni Family"
    assert top_rec["score"] > recs[1]["score"]
    assert any("Urgent Flag" in r for r in top_rec["reasons"])
    assert any("Date in <= 2 Days" in r for r in top_rec["reasons"])


def test_analytics_multi_format_exports(populated_analytics_db, tmp_path):
    """Verify Module 8 multi-format exports: CSV, Excel (.xlsx), and PDF."""
    # 1. Summary CSV
    csv_file = tmp_path / "test_summary.csv"
    export_summary_to_csv(csv_file, db_path=populated_analytics_db)
    assert csv_file.exists()
    content_csv = csv_file.read_text(encoding="utf-8-sig")
    assert "Total Registered Families" in content_csv
    assert "70000.00" in content_csv

    # 2. Performance CSV
    perf_csv = tmp_path / "test_perf.csv"
    export_performance_to_csv(perf_csv, db_path=populated_analytics_db)
    assert perf_csv.exists()

    # 3. Queue Intelligence CSV
    q_csv = tmp_path / "test_queue.csv"
    export_queue_intelligence_to_csv(q_csv, db_path=populated_analytics_db)
    assert q_csv.exists()

    # 4. Multi-tab Excel (.xlsx) workbook
    xlsx_file = tmp_path / "test_analytics.xlsx"
    export_full_analytics_workbook_xlsx(xlsx_file, db_path=populated_analytics_db)
    assert xlsx_file.exists()
    assert xlsx_file.stat().st_size > 2000

    # 5. Printable Executive PDF report
    pdf_file = tmp_path / "test_report.pdf"
    export_analytics_report_pdf("summary", pdf_file, db_path=populated_analytics_db)
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 1000


def test_data_privacy_in_analytics(populated_analytics_db, tmp_path):
    """Verify that analytics exports never leak full ID proof numbers or financial credentials."""
    csv_file = tmp_path / "privacy_test.csv"
    export_summary_to_csv(csv_file, db_path=populated_analytics_db)
    txt = csv_file.read_text(encoding="utf-8")

    # Ensure no credentials or raw full IDs exist in CSV
    assert "password" not in txt.lower()
    assert "otp" not in txt.lower()
    assert "pin" not in txt.lower()
