"""
SRIVANI BOOKING MANAGER - Multi-Format Analytics Export Engine
Exports operational analytics, booking trends, queue intelligence,
payment summaries, and document compliance to CSV, Excel (.xlsx), and PDF.
Strictly relies on real database records; never fabricates figures.
"""
import sys
import os
import csv
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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
from reports import NumberedCanvas
from logger import get_logger

logger = get_logger("analytics_export")


# -----------------------------------------------------------------------------
# CSV Export Functions
# -----------------------------------------------------------------------------

def export_summary_to_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Export KPI summary metrics to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = get_analytics_summary(db_path, filter_type, custom_start, custom_end)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — EXECUTIVE ANALYTICS SUMMARY"])
        w.writerow(["Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Date Filter", data["filter_label"]])
        w.writerow([])
        w.writerow(["Metric", "Value"])
        w.writerow(["Total Registered Families", data["total_families"]])
        w.writerow(["Total Devotees (Pilgrims)", data["total_pilgrims"]])
        w.writerow(["Completed Bookings", data["completed_bookings"]])
        w.writerow(["Pending Bookings in Queue", data["pending_bookings"]])
        w.writerow(["In Progress Bookings", data["in_progress_bookings"]])
        w.writerow(["Unavailable Bookings", data["unavailable_bookings"]])
        w.writerow(["Cancelled Bookings", data["cancelled_bookings"]])
        w.writerow(["Booking Completion Rate (%)", f"{data['booking_completion_percentage']}%"])
        w.writerow(["Total Donation Pledged (INR)", f"{data['total_donation_pledged']:.2f}"])
        w.writerow([])
        w.writerow(["PAYMENT STATUS SUMMARY"])
        w.writerow(["Payment Status", "Transaction Count", "Total Amount (INR)"])
        for st, item in data["payment_summary"].items():
            w.writerow([st, item["count"], f"{item['amount']:.2f}"])

    logger.info(f"Analytics summary exported to CSV: {out}")
    return out


def export_performance_to_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Export daily and weekly booking trends to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — BOOKING PERFORMANCE & TRENDS"])
        w.writerow(["Date Filter", perf["filter_label"]])
        w.writerow(["Average Turnaround (Hours)", perf["avg_turnaround_hours"]])
        w.writerow(["Average Turnaround (Days)", perf["avg_turnaround_days"]])
        w.writerow(["Processing Rate (%)", f"{perf['processing_completion_rate']}%"])
        w.writerow([])
        w.writerow(["DAILY ACTIVITY TRENDS"])
        w.writerow(["Date", "Total Families", "Booked", "Pending", "Unavailable", "Cancelled", "Pilgrims", "Revenue (INR)"])
        for r in perf["daily_trends"]:
            w.writerow([
                r["activity_date"],
                r["total_families"],
                r["booked"],
                r["pending"],
                r["unavailable"],
                r["cancelled"],
                r["pilgrims_count"],
                f"{r['booked_revenue']:.2f}",
            ])

    logger.info(f"Booking performance exported to CSV: {out}")
    return out


def export_queue_intelligence_to_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
) -> Path:
    """Export queue aging and attention-required records to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    qi = get_queue_intelligence(db_path)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — QUEUE INTELLIGENCE & ATTENTION AUDIT"])
        w.writerow(["Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Total Pending in Queue", qi["total_pending"]])
        w.writerow([])
        w.writerow(["QUEUE AGING DISTRIBUTION"])
        w.writerow(["Aging Bracket", "Family Count"])
        for b, count in qi["aging_buckets"].items():
            w.writerow([b, count])
        w.writerow([])
        w.writerow(["RECORDS REQUIRING IMMEDIATE ADMIN ATTENTION"])
        w.writerow(["Family Code", "Family Name", "Contact Phone", "Reason / Flag", "Created Date"])
        for item in qi["attention_items"]:
            w.writerow([
                item.get("family_code"),
                item.get("family_name"),
                item.get("phone", "—"),
                item.get("reason"),
                item.get("created_at"),
            ])

    logger.info(f"Queue intelligence exported to CSV: {out}")
    return out


def export_daily_report_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Export daily booking performance and revenue to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — DAILY BOOKING REPORT"])
        w.writerow(["Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Date Filter", perf["filter_label"]])
        w.writerow([])
        w.writerow(["Date", "Total Families", "Booked", "Pending", "Unavailable", "Cancelled", "Devotees", "Booked Revenue (INR)"])
        for r in perf["daily_trends"]:
            w.writerow([
                r["activity_date"],
                r["total_families"],
                r["booked"],
                r["pending"],
                r["unavailable"],
                r["cancelled"],
                r["pilgrims_count"],
                f"{r['booked_revenue']:.2f}",
            ])

    logger.info(f"Daily report exported to CSV: {out}")
    return out


def export_weekly_report_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Export weekly operational booking breakdown to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — WEEKLY OPERATIONAL REPORT"])
        w.writerow(["Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Date Filter", perf["filter_label"]])
        w.writerow([])
        w.writerow(["Calendar Week", "Total Families", "Booked", "Pending", "Devotees", "Booked Revenue (INR)"])
        for r in perf["weekly_trends"]:
            w.writerow([
                r["activity_week"],
                r["total_families"],
                r["booked"],
                r["pending"],
                r["pilgrims_count"],
                f"{r['booked_revenue']:.2f}",
            ])

    logger.info(f"Weekly report exported to CSV: {out}")
    return out


def export_monthly_report_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Export monthly executive booking and donation breakdown to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — MONTHLY BOOKING REPORT"])
        w.writerow(["Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Date Filter", perf["filter_label"]])
        w.writerow([])
        w.writerow(["Month (YYYY-MM)", "Total Families", "Booked", "Pending", "Cancelled", "Devotees", "Booked Revenue (INR)"])
        for r in perf["monthly_trends"]:
            w.writerow([
                r["activity_month"],
                r["total_families"],
                r["booked"],
                r["pending"],
                r["cancelled"],
                r["pilgrims_count"],
                f"{r['booked_revenue']:.2f}",
            ])

    logger.info(f"Monthly report exported to CSV: {out}")
    return out


def export_family_report_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    search_term: str = "",
    status_filter: str = "All",
    ticket_filter: str = "All",
) -> Path:
    """Export family-wise booking history and devotee records to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fam_data = get_family_analytics(
        db_path=db_path,
        search_term=search_term,
        status_filter=status_filter,
        ticket_filter=ticket_filter,
        limit=5000,
    )

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — FAMILY-WISE BOOKING REPORT"])
        w.writerow(["Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Status Filter", status_filter, "Ticket Filter", ticket_filter, "Search Term", search_term or "None"])
        w.writerow([])
        w.writerow([
            "Family Code",
            "Family Name",
            "Contact Name",
            "Contact Phone",
            "Devotees Count",
            "Donation (INR)",
            "Booking Type",
            "Preferred Date",
            "Booking Status",
            "Payment Status",
            "Priority",
            "Ticket PDF Attached",
            "Registration Date",
        ])
        for r in fam_data["family_records"]:
            w.writerow([
                r["family_code"],
                r["family_name"],
                r["contact_name"],
                r["phone"],
                r["pilgrim_count"],
                f"{r['donation_amount']:.2f}",
                r["booking_type"],
                r["preferred_date"] or "—",
                r["status"],
                r["payment_status"],
                r.get("priority", "Normal"),
                "Yes" if r.get("has_ticket") else "No",
                r["created_at"],
            ])

    logger.info(f"Family report exported to CSV: {out}")
    return out


def export_payment_report_csv(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Export payment reconciliation and transaction records to CSV."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pay = get_payment_analytics(db_path, filter_type, custom_start, custom_end)

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["SRIVANI BOOKING MANAGER — FINANCIAL & PAYMENT RECONCILIATION REPORT"])
        w.writerow(["Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        w.writerow(["Date Filter", pay["filter_label"]])
        w.writerow(["Total Revenue Collected (INR)", f"{pay['total_revenue_collected']:.2f}"])
        w.writerow(["Payment Reference Capture Rate", f"{pay['payment_ref_capture_rate']}%"])
        w.writerow([])
        w.writerow(["PAYMENT STATUS SUMMARY"])
        w.writerow(["Payment Status", "Transactions", "Total Amount (INR)", "With Ref Count"])
        for st, item in pay["payment_summary"].items():
            w.writerow([st, item["count"], f"{item['amount']:.2f}", item.get("with_ref", 0)])
        w.writerow([])
        w.writerow(["DATE-WISE PAYMENT RECEIPTS (PAID BOOKINGS)"])
        w.writerow(["Receipt Date", "Paid Bookings", "Daily Collection (INR)"])
        for r in pay["date_wise_collections"]:
            w.writerow([r["tx_date"], r["paid_count"], f"{r['daily_amount']:.2f}"])

    logger.info(f"Payment report exported to CSV: {out}")
    return out


# -----------------------------------------------------------------------------
# Excel (.xlsx) Multi-Tab Export Engine (OpenPyXL)
# -----------------------------------------------------------------------------

def export_full_analytics_workbook_xlsx(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """
    Generate a formatted, professional multi-tab Excel (.xlsx) workbook
    containing all operational analytics modules.
    """
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    summary_data = get_analytics_summary(db_path, filter_type, custom_start, custom_end)
    perf_data = get_booking_performance(db_path, filter_type, custom_start, custom_end)
    queue_data = get_queue_intelligence(db_path)
    payment_data = get_payment_analytics(db_path, filter_type, custom_start, custom_end)
    doc_data = get_document_analytics(db_path)
    ops_data = get_operational_intelligence(db_path)

    wb = openpyxl.Workbook()

    # Styles
    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    light_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    accent_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

    font_title = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
    font_regular = Font(name="Segoe UI", size=9, color="334155")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    # ---------------------------------------------------------
    # TAB 1: Executive KPI Overview
    # ---------------------------------------------------------
    ws_kpi = wb.active
    ws_kpi.title = "Executive KPIs"
    ws_kpi.views.sheetView[0].showGridLines = True

    # Title Banner
    ws_kpi.merge_cells("A1:E1")
    t_cell = ws_kpi["A1"]
    t_cell.value = "SRIVANI BOOKING MANAGER — EXECUTIVE ANALYTICS DASHBOARD"
    t_cell.font = font_title
    t_cell.fill = navy_fill
    t_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_kpi.row_dimensions[1].height = 36

    ws_kpi["A2"] = f"Filter Scope: {summary_data['filter_label']}  |  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ws_kpi["A2"].font = Font(name="Segoe UI", size=9, italic=True, color="64748B")

    kpi_rows = [
        ("Total Families Registered", summary_data["total_families"], "General"),
        ("Total Devotees (Pilgrims)", summary_data["total_pilgrims"], "General"),
        ("Completed Bookings (Booked)", summary_data["completed_bookings"], "General"),
        ("Pending Bookings in Queue", summary_data["pending_bookings"], "General"),
        ("In Progress Bookings", summary_data["in_progress_bookings"], "General"),
        ("Unavailable / Quota Full", summary_data["unavailable_bookings"], "General"),
        ("Cancelled Bookings", summary_data["cancelled_bookings"], "General"),
        ("Booking Completion Percentage", summary_data["booking_completion_percentage"] / 100.0, "0.0%"),
        ("Total Donation Pledged", summary_data["total_donation_pledged"], "₹#,##0.00"),
    ]

    ws_kpi.cell(row=4, column=1, value="Core Metric Indicator").font = font_header
    ws_kpi.cell(row=4, column=1).fill = header_fill
    ws_kpi.cell(row=4, column=2, value="Value").font = font_header
    ws_kpi.cell(row=4, column=2).fill = header_fill

    for idx, (label, val, fmt) in enumerate(kpi_rows, start=5):
        c1 = ws_kpi.cell(row=idx, column=1, value=label)
        c2 = ws_kpi.cell(row=idx, column=2, value=val)
        c1.font = font_regular
        c2.font = font_bold
        c1.border = thin_border
        c2.border = thin_border
        if fmt != "General":
            c2.number_format = fmt

    # Payment Summary Sub-Table
    start_r = len(kpi_rows) + 7
    ws_kpi.cell(row=start_r, column=1, value="Payment Status Summary").font = font_header
    ws_kpi.cell(row=start_r, column=1).fill = header_fill
    ws_kpi.cell(row=start_r, column=2, value="Transaction Count").font = font_header
    ws_kpi.cell(row=start_r, column=2).fill = header_fill
    ws_kpi.cell(row=start_r, column=3, value="Total Amount (INR)").font = font_header
    ws_kpi.cell(row=start_r, column=3).fill = header_fill

    curr_r = start_r + 1
    for st, pitem in summary_data["payment_summary"].items():
        c1 = ws_kpi.cell(row=curr_r, column=1, value=st)
        c2 = ws_kpi.cell(row=curr_r, column=2, value=pitem["count"])
        c3 = ws_kpi.cell(row=curr_r, column=3, value=pitem["amount"])
        c1.font = font_regular
        c2.font = font_regular
        c3.font = font_bold
        c1.border = thin_border
        c2.border = thin_border
        c3.border = thin_border
        c3.number_format = "₹#,##0.00"
        curr_r += 1

    # ---------------------------------------------------------
    # TAB 2: Booking Performance Trends
    # ---------------------------------------------------------
    ws_perf = wb.create_sheet(title="Booking Performance")
    ws_perf.views.sheetView[0].showGridLines = True

    ws_perf.merge_cells("A1:G1")
    p_t = ws_perf["A1"]
    p_t.value = f"BOOKING PERFORMANCE TRENDS ({perf_data['filter_label']})"
    p_t.font = font_title
    p_t.fill = navy_fill
    p_t.alignment = Alignment(horizontal="center", vertical="center")
    ws_perf.row_dimensions[1].height = 30

    ws_perf["A2"] = f"Average Lead Time: {perf_data['avg_turnaround_hours']} Hours ({perf_data['avg_turnaround_days']} Days)  |  Overall Processing Rate: {perf_data['processing_completion_rate']}%"
    ws_perf["A2"].font = font_bold

    p_headers = ["Date", "Total Families", "Booked", "Pending", "Unavailable", "Cancelled", "Pilgrims", "Revenue (INR)"]
    for c_idx, h_text in enumerate(p_headers, start=1):
        cell = ws_perf.cell(row=4, column=c_idx, value=h_text)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    p_r = 5
    for row in perf_data["daily_trends"]:
        ws_perf.cell(row=p_r, column=1, value=row["activity_date"]).font = font_regular
        ws_perf.cell(row=p_r, column=2, value=row["total_families"]).font = font_regular
        ws_perf.cell(row=p_r, column=3, value=row["booked"]).font = font_bold
        ws_perf.cell(row=p_r, column=4, value=row["pending"]).font = font_regular
        ws_perf.cell(row=p_r, column=5, value=row["unavailable"]).font = font_regular
        ws_perf.cell(row=p_r, column=6, value=row["cancelled"]).font = font_regular
        ws_perf.cell(row=p_r, column=7, value=row["pilgrims_count"]).font = font_regular
        rev_c = ws_perf.cell(row=p_r, column=8, value=row["booked_revenue"])
        rev_c.font = font_bold
        rev_c.number_format = "₹#,##0.00"

        for c_idx in range(1, 9):
            ws_perf.cell(row=p_r, column=c_idx).border = thin_border
        p_r += 1

    # ---------------------------------------------------------
    # TAB 3: Queue Intelligence & Aging
    # ---------------------------------------------------------
    ws_q = wb.create_sheet(title="Queue Intelligence")
    ws_q.views.sheetView[0].showGridLines = True

    ws_q.merge_cells("A1:E1")
    q_t = ws_q["A1"]
    q_t.value = "QUEUE INTELLIGENCE & BOTTLENECK ANALYSIS"
    q_t.font = font_title
    q_t.fill = navy_fill
    q_t.alignment = Alignment(horizontal="center", vertical="center")
    ws_q.row_dimensions[1].height = 30

    ws_q["A3"] = "Queue Aging Bracket"
    ws_q["B3"] = "Pending Families"
    ws_q["A3"].font = font_header
    ws_q["A3"].fill = header_fill
    ws_q["B3"].font = font_header
    ws_q["B3"].fill = header_fill

    r_idx = 4
    for b_name, b_count in queue_data["aging_buckets"].items():
        c1 = ws_q.cell(row=r_idx, column=1, value=b_name)
        c2 = ws_q.cell(row=r_idx, column=2, value=b_count)
        c1.font = font_regular
        c2.font = font_bold
        c1.border = thin_border
        c2.border = thin_border
        r_idx += 1

    r_idx += 2
    ws_q.cell(row=r_idx, column=1, value="Records Requiring Immediate Admin Attention").font = font_header
    ws_q.cell(row=r_idx, column=1).fill = header_fill
    ws_q.merge_cells(start_row=r_idx, start_column=1, end_row=r_idx, end_column=5)

    r_idx += 1
    att_headers = ["Family Code", "Family Name", "Phone", "Priority / Preferred Date", "Attention Reason"]
    for c_idx, h in enumerate(att_headers, start=1):
        cell = ws_q.cell(row=r_idx, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    r_idx += 1
    for item in queue_data["attention_items"]:
        ws_q.cell(row=r_idx, column=1, value=item.get("family_code")).font = font_regular
        ws_q.cell(row=r_idx, column=2, value=item.get("family_name")).font = font_regular
        ws_q.cell(row=r_idx, column=3, value=item.get("phone", "—")).font = font_regular
        ws_q.cell(row=r_idx, column=4, value=item.get("preferred_date") or item.get("priority", "Normal")).font = font_regular
        ws_q.cell(row=r_idx, column=5, value=item.get("reason")).font = font_bold
        for c_idx in range(1, 6):
            ws_q.cell(row=r_idx, column=c_idx).border = thin_border
        r_idx += 1

    # ---------------------------------------------------------
    # TAB 4: Queue Recommendations (Prioritization Score)
    # ---------------------------------------------------------
    ws_recs = wb.create_sheet(title="Prioritization Engine")
    ws_recs.views.sheetView[0].showGridLines = True

    ws_recs.merge_cells("A1:G1")
    rec_t = ws_recs["A1"]
    rec_t.value = "SUGGESTED SEQUENTIAL QUEUE PRIORITIZATION (RULE-BASED)"
    rec_t.font = font_title
    rec_t.fill = navy_fill
    rec_t.alignment = Alignment(horizontal="center", vertical="center")
    ws_recs.row_dimensions[1].height = 30

    ws_recs["A2"] = "Methodology: Deterministic rule-based scoring (Date Imminence + Flag Priority + Queue Aging + Document Readiness)"
    ws_recs["A2"].font = Font(name="Segoe UI", size=8, italic=True)

    rec_headers = ["Rank", "Score", "Family Code", "Family Name", "Devotees", "Preferred Date", "Reasoning Tags"]
    for c_idx, h in enumerate(rec_headers, start=1):
        cell = ws_recs.cell(row=4, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    rec_r = 5
    for rank, item in enumerate(ops_data["recommended_queue"], start=1):
        ws_recs.cell(row=rec_r, column=1, value=f"#{rank}").font = font_bold
        sc_c = ws_recs.cell(row=rec_r, column=2, value=item["score"])
        sc_c.font = font_bold
        sc_c.fill = accent_fill
        ws_recs.cell(row=rec_r, column=3, value=item["family_code"]).font = font_regular
        ws_recs.cell(row=rec_r, column=4, value=item["family_name"]).font = font_regular
        ws_recs.cell(row=rec_r, column=5, value=item["pilgrim_count"]).font = font_regular
        ws_recs.cell(row=rec_r, column=6, value=item["preferred_date"] or "—").font = font_regular
        ws_recs.cell(row=rec_r, column=7, value=", ".join(item["reasons"])).font = font_regular

        for c_idx in range(1, 8):
            ws_recs.cell(row=rec_r, column=c_idx).border = thin_border
        rec_r += 1

    # ---------------------------------------------------------
    # TAB 5: In-Progress Queue Tracking
    # ---------------------------------------------------------
    ws_inp = wb.create_sheet(title="In-Progress Queue")
    ws_inp.views.sheetView[0].showGridLines = True
    ws_inp.merge_cells("A1:G1")
    inp_t = ws_inp["A1"]
    inp_t.value = "CURRENTLY IN-PROGRESS FAMILIES TRACKING"
    inp_t.font = font_title
    inp_t.fill = navy_fill
    inp_t.alignment = Alignment(horizontal="center", vertical="center")
    ws_inp.row_dimensions[1].height = 30

    inp_headers = ["Family Code", "Family Name", "Contact Name", "Phone", "Devotees", "Preferred Date", "Hours In Progress"]
    for c_idx, h in enumerate(inp_headers, start=1):
        cell = ws_inp.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    inp_r = 4
    for item in queue_data.get("in_progress_tracking", []):
        ws_inp.cell(row=inp_r, column=1, value=item.get("family_code")).font = font_regular
        ws_inp.cell(row=inp_r, column=2, value=item.get("family_name")).font = font_regular
        ws_inp.cell(row=inp_r, column=3, value=item.get("contact_name", "—")).font = font_regular
        ws_inp.cell(row=inp_r, column=4, value=item.get("phone", "—")).font = font_regular
        ws_inp.cell(row=inp_r, column=5, value=item.get("pilgrim_count", 0)).font = font_regular
        ws_inp.cell(row=inp_r, column=6, value=item.get("preferred_date") or "—").font = font_regular
        ws_inp.cell(row=inp_r, column=7, value=item.get("hours_in_progress", 0.0)).font = font_bold
        for c_idx in range(1, 8):
            ws_inp.cell(row=inp_r, column=c_idx).border = thin_border
        inp_r += 1

    # ---------------------------------------------------------
    # TAB 6: Family Directory & History
    # ---------------------------------------------------------
    ws_fam = wb.create_sheet(title="Family Directory")
    ws_fam.views.sheetView[0].showGridLines = True
    ws_fam.merge_cells("A1:H1")
    fam_t = ws_fam["A1"]
    fam_t.value = "FAMILY ROSTER & BOOKING AUDIT"
    fam_t.font = font_title
    fam_t.fill = navy_fill
    fam_t.alignment = Alignment(horizontal="center", vertical="center")
    ws_fam.row_dimensions[1].height = 30

    fam_headers = ["Family Code", "Family Name", "Contact", "Phone", "Devotees", "Donation (INR)", "Status", "Ticket Attached"]
    for c_idx, h in enumerate(fam_headers, start=1):
        cell = ws_fam.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    fam_data = get_family_analytics(db_path=db_path, limit=2000)
    fam_r = 4
    for r in fam_data.get("family_records", []):
        ws_fam.cell(row=fam_r, column=1, value=r.get("family_code")).font = font_regular
        ws_fam.cell(row=fam_r, column=2, value=r.get("family_name")).font = font_regular
        ws_fam.cell(row=fam_r, column=3, value=r.get("contact_name", "—")).font = font_regular
        ws_fam.cell(row=fam_r, column=4, value=r.get("phone", "—")).font = font_regular
        ws_fam.cell(row=fam_r, column=5, value=r.get("pilgrim_count", 0)).font = font_regular
        c_don = ws_fam.cell(row=fam_r, column=6, value=r.get("donation_amount", 0.0))
        c_don.font = font_regular
        c_don.number_format = "₹#,##0.00"
        ws_fam.cell(row=fam_r, column=7, value=r.get("status", "—")).font = font_bold
        ws_fam.cell(row=fam_r, column=8, value="Yes" if r.get("has_ticket") else "No").font = font_regular
        for c_idx in range(1, 9):
            ws_fam.cell(row=fam_r, column=c_idx).border = thin_border
        fam_r += 1

    # Auto-adjust column widths across all worksheets
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or "")
                if cell.row == 1:
                    continue  # skip merged header for width calculation
                max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(str(out))
    logger.info(f"Full multi-tab analytics workbook exported to Excel: {out}")
    return out


# -----------------------------------------------------------------------------
# Dedicated Single-Module Excel (.xlsx) Exporters
# -----------------------------------------------------------------------------

def export_daily_report_xlsx(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate daily booking performance Excel (.xlsx) spreadsheet."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Daily Performance"
    ws.views.sheetView[0].showGridLines = True

    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    font_title = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Segoe UI", size=9, color="334155")
    font_bold = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
    thin_border = Border(left=Side(style="thin", color="CBD5E1"), right=Side(style="thin", color="CBD5E1"), top=Side(style="thin", color="CBD5E1"), bottom=Side(style="thin", color="CBD5E1"))

    ws.merge_cells("A1:H1")
    ws["A1"] = f"SRIVANI BOOKING MANAGER — DAILY BOOKING REPORT ({perf['filter_label']})"
    ws["A1"].font = font_title
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    headers = ["Date", "Total Families", "Booked", "Pending", "Unavailable", "Cancelled", "Devotees", "Booked Revenue (INR)"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    row_idx = 4
    for r in perf["daily_trends"]:
        ws.cell(row=row_idx, column=1, value=r["activity_date"]).font = font_regular
        ws.cell(row=row_idx, column=2, value=r["total_families"]).font = font_regular
        ws.cell(row=row_idx, column=3, value=r["booked"]).font = font_bold
        ws.cell(row=row_idx, column=4, value=r["pending"]).font = font_regular
        ws.cell(row=row_idx, column=5, value=r["unavailable"]).font = font_regular
        ws.cell(row=row_idx, column=6, value=r["cancelled"]).font = font_regular
        ws.cell(row=row_idx, column=7, value=r["pilgrims_count"]).font = font_regular
        rev_c = ws.cell(row=row_idx, column=8, value=r["booked_revenue"])
        rev_c.font = font_bold
        rev_c.number_format = "₹#,##0.00"
        for c in range(1, 9):
            ws.cell(row=row_idx, column=c).border = thin_border
        row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col if cell.row > 1) if ws.max_row > 1 else 10
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 12)

    wb.save(str(out))
    logger.info(f"Daily report exported to Excel: {out}")
    return out


def export_weekly_report_xlsx(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate weekly operational booking breakdown in Excel (.xlsx)."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Weekly Breakdown"
    ws.views.sheetView[0].showGridLines = True

    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    font_title = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Segoe UI", size=9, color="334155")
    font_bold = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
    thin_border = Border(left=Side(style="thin", color="CBD5E1"), right=Side(style="thin", color="CBD5E1"), top=Side(style="thin", color="CBD5E1"), bottom=Side(style="thin", color="CBD5E1"))

    ws.merge_cells("A1:F1")
    ws["A1"] = f"SRIVANI BOOKING MANAGER — WEEKLY OPERATIONAL REPORT ({perf['filter_label']})"
    ws["A1"].font = font_title
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    headers = ["Calendar Week", "Total Families", "Booked", "Pending", "Devotees", "Booked Revenue (INR)"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    row_idx = 4
    for r in perf["weekly_trends"]:
        ws.cell(row=row_idx, column=1, value=r["activity_week"]).font = font_regular
        ws.cell(row=row_idx, column=2, value=r["total_families"]).font = font_regular
        ws.cell(row=row_idx, column=3, value=r["booked"]).font = font_bold
        ws.cell(row=row_idx, column=4, value=r["pending"]).font = font_regular
        ws.cell(row=row_idx, column=5, value=r["pilgrims_count"]).font = font_regular
        rev_c = ws.cell(row=row_idx, column=6, value=r["booked_revenue"])
        rev_c.font = font_bold
        rev_c.number_format = "₹#,##0.00"
        for c in range(1, 7):
            ws.cell(row=row_idx, column=c).border = thin_border
        row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col if cell.row > 1) if ws.max_row > 1 else 10
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    wb.save(str(out))
    logger.info(f"Weekly report exported to Excel: {out}")
    return out


def export_monthly_report_xlsx(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate monthly executive booking and donation breakdown in Excel (.xlsx)."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly Summary"
    ws.views.sheetView[0].showGridLines = True

    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    font_title = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Segoe UI", size=9, color="334155")
    font_bold = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
    thin_border = Border(left=Side(style="thin", color="CBD5E1"), right=Side(style="thin", color="CBD5E1"), top=Side(style="thin", color="CBD5E1"), bottom=Side(style="thin", color="CBD5E1"))

    ws.merge_cells("A1:G1")
    ws["A1"] = f"SRIVANI BOOKING MANAGER — MONTHLY BOOKING REPORT ({perf['filter_label']})"
    ws["A1"].font = font_title
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    headers = ["Month (YYYY-MM)", "Total Families", "Booked", "Pending", "Cancelled", "Devotees", "Booked Revenue (INR)"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    row_idx = 4
    for r in perf["monthly_trends"]:
        ws.cell(row=row_idx, column=1, value=r["activity_month"]).font = font_regular
        ws.cell(row=row_idx, column=2, value=r["total_families"]).font = font_regular
        ws.cell(row=row_idx, column=3, value=r["booked"]).font = font_bold
        ws.cell(row=row_idx, column=4, value=r["pending"]).font = font_regular
        ws.cell(row=row_idx, column=5, value=r["cancelled"]).font = font_regular
        ws.cell(row=row_idx, column=6, value=r["pilgrims_count"]).font = font_regular
        rev_c = ws.cell(row=row_idx, column=7, value=r["booked_revenue"])
        rev_c.font = font_bold
        rev_c.number_format = "₹#,##0.00"
        for c in range(1, 8):
            ws.cell(row=row_idx, column=c).border = thin_border
        row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col if cell.row > 1) if ws.max_row > 1 else 10
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    wb.save(str(out))
    logger.info(f"Monthly report exported to Excel: {out}")
    return out


def export_family_report_xlsx(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    search_term: str = "",
    status_filter: str = "All",
    ticket_filter: str = "All",
) -> Path:
    """Generate family-wise booking history and devotee records in Excel (.xlsx)."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fam_data = get_family_analytics(
        db_path=db_path,
        search_term=search_term,
        status_filter=status_filter,
        ticket_filter=ticket_filter,
        limit=5000,
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Family Records"
    ws.views.sheetView[0].showGridLines = True

    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    font_title = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Segoe UI", size=9, color="334155")
    font_bold = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
    thin_border = Border(left=Side(style="thin", color="CBD5E1"), right=Side(style="thin", color="CBD5E1"), top=Side(style="thin", color="CBD5E1"), bottom=Side(style="thin", color="CBD5E1"))

    ws.merge_cells("A1:I1")
    ws["A1"] = f"SRIVANI BOOKING MANAGER — FAMILY BOOKING ROSTER (Found: {fam_data['total_found']})"
    ws["A1"].font = font_title
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    headers = ["Family Code", "Family Name", "Contact", "Phone", "Devotees", "Donation (INR)", "Preferred Date", "Status", "Ticket Attached"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    row_idx = 4
    for r in fam_data["family_records"]:
        ws.cell(row=row_idx, column=1, value=r["family_code"]).font = font_regular
        ws.cell(row=row_idx, column=2, value=r["family_name"]).font = font_regular
        ws.cell(row=row_idx, column=3, value=r["contact_name"]).font = font_regular
        ws.cell(row=row_idx, column=4, value=r["phone"]).font = font_regular
        ws.cell(row=row_idx, column=5, value=r["pilgrim_count"]).font = font_regular
        don_c = ws.cell(row=row_idx, column=6, value=r["donation_amount"])
        don_c.font = font_regular
        don_c.number_format = "₹#,##0.00"
        ws.cell(row=row_idx, column=7, value=r["preferred_date"] or "—").font = font_regular
        ws.cell(row=row_idx, column=8, value=r["status"]).font = font_bold
        ws.cell(row=row_idx, column=9, value="Yes" if r.get("has_ticket") else "No").font = font_regular
        for c in range(1, 10):
            ws.cell(row=row_idx, column=c).border = thin_border
        row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col if cell.row > 1) if ws.max_row > 1 else 10
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 13)

    wb.save(str(out))
    logger.info(f"Family report exported to Excel: {out}")
    return out


def export_payment_report_xlsx(
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate financial payment reconciliation and date collections in Excel (.xlsx)."""
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pay = get_payment_analytics(db_path, filter_type, custom_start, custom_end)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Payment Summary"
    ws.views.sheetView[0].showGridLines = True

    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    font_title = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    font_header = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Segoe UI", size=9, color="334155")
    font_bold = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
    thin_border = Border(left=Side(style="thin", color="CBD5E1"), right=Side(style="thin", color="CBD5E1"), top=Side(style="thin", color="CBD5E1"), bottom=Side(style="thin", color="CBD5E1"))

    ws.merge_cells("A1:D1")
    ws["A1"] = f"SRIVANI BOOKING MANAGER — PAYMENT RECONCILIATION ({pay['filter_label']})"
    ws["A1"].font = font_title
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    headers = ["Payment Status", "Transactions", "Total Amount (INR)", "With Reference"]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border

    row_idx = 4
    for st, item in pay["payment_summary"].items():
        ws.cell(row=row_idx, column=1, value=st).font = font_regular
        ws.cell(row=row_idx, column=2, value=item["count"]).font = font_regular
        amt_c = ws.cell(row=row_idx, column=3, value=item["amount"])
        amt_c.font = font_bold
        amt_c.number_format = "₹#,##0.00"
        ws.cell(row=row_idx, column=4, value=item.get("with_ref", 0)).font = font_regular
        for c in range(1, 5):
            ws.cell(row=row_idx, column=c).border = thin_border
        row_idx += 1

    # Date receipts
    row_idx += 2
    ws.cell(row=row_idx, column=1, value="Date-wise Paid Collections").font = font_header
    ws.cell(row=row_idx, column=1).fill = header_fill
    ws.cell(row=row_idx, column=2, value="Paid Bookings").font = font_header
    ws.cell(row=row_idx, column=2).fill = header_fill
    ws.cell(row=row_idx, column=3, value="Daily Amount (INR)").font = font_header
    ws.cell(row=row_idx, column=3).fill = header_fill

    row_idx += 1
    for r in pay["date_wise_collections"]:
        ws.cell(row=row_idx, column=1, value=r["tx_date"]).font = font_regular
        ws.cell(row=row_idx, column=2, value=r["paid_count"]).font = font_regular
        damt_c = ws.cell(row=row_idx, column=3, value=r["daily_amount"])
        damt_c.font = font_bold
        damt_c.number_format = "₹#,##0.00"
        for c in range(1, 4):
            ws.cell(row=row_idx, column=c).border = thin_border
        row_idx += 1

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col if cell.row > 1) if ws.max_row > 1 else 10
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    wb.save(str(out))
    logger.info(f"Payment report exported to Excel: {out}")
    return out


# -----------------------------------------------------------------------------
# Printable Executive PDF Report Generation (ReportLab)
# -----------------------------------------------------------------------------

def export_analytics_report_pdf(
    report_type: str,
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """
    Generate an executive, printable PDF analytics report via ReportLab.
    Includes running headers/footers, summary metric cards, tables, and compliance statement.
    """
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    summary = get_analytics_summary(db_path, filter_type, custom_start, custom_end)
    perf = get_booking_performance(db_path, filter_type, custom_start, custom_end)
    queue = get_queue_intelligence(db_path)
    pay = get_payment_analytics(db_path, filter_type, custom_start, custom_end)
    doc = get_document_analytics(db_path)
    ops = get_operational_intelligence(db_path)

    doc_pdf = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#1e3a8a"),
    )
    sub_style = ParagraphStyle(
        "ReportSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
    )
    sec_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6,
    )
    cell_bold = ParagraphStyle("CellB", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor("#0f172a"))
    cell_reg = ParagraphStyle("CellR", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#334155"))
    compliance_style = ParagraphStyle(
        "ComplianceNotice",
        fontName="Helvetica-Oblique",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748b"),
        alignment=1,
    )

    story = []

    # Title & Header
    story.append(Paragraph("SRIVANI BOOKING MANAGER", title_style))
    story.append(Paragraph(f"Advanced Operational Intelligence & Analytics Report  |  Filter Scope: {summary['filter_label']}", sub_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=10))

    # Executive KPI Summary Grid
    story.append(Paragraph("1. Executive Summary & Booking Metrics", sec_style))
    kpi_table_data = [
        [
            Paragraph("<b>Total Families</b>", cell_bold),
            Paragraph(str(summary["total_families"]), cell_bold),
            Paragraph("<b>Completed (Booked)</b>", cell_bold),
            Paragraph(f"{summary['completed_bookings']} ({summary['booking_completion_percentage']}%)", cell_bold),
        ],
        [
            Paragraph("<b>Total Devotees</b>", cell_bold),
            Paragraph(str(summary["total_pilgrims"]), cell_bold),
            Paragraph("<b>Pending in Queue</b>", cell_bold),
            Paragraph(str(summary["pending_bookings"]), cell_bold),
        ],
        [
            Paragraph("<b>Processing Rate</b>", cell_bold),
            Paragraph(f"{perf['processing_completion_rate']}%", cell_bold),
            Paragraph("<b>Unavailable / Cancelled</b>", cell_bold),
            Paragraph(f"{summary['unavailable_bookings']} / {summary['cancelled_bookings']}", cell_bold),
        ],
        [
            Paragraph("<b>Pledged Donations</b>", cell_bold),
            Paragraph(f"₹{summary['total_donation_pledged']:,.2f}", cell_bold),
            Paragraph("<b>Collected Revenue</b>", cell_bold),
            Paragraph(f"₹{pay['total_revenue_collected']:,.2f}", cell_bold),
        ],
    ]
    t_kpi = Table(kpi_table_data, colWidths=[130, 130, 130, 130])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 10))

    r_type = (report_type or "summary").lower().strip()

    if r_type == "daily":
        story.append(Paragraph("2. Daily Booking Activity Breakdown", sec_style))
        d_rows = [[
            Paragraph("<b>Date</b>", cell_bold),
            Paragraph("<b>Total</b>", cell_bold),
            Paragraph("<b>Booked</b>", cell_bold),
            Paragraph("<b>Pending</b>", cell_bold),
            Paragraph("<b>Devotees</b>", cell_bold),
            Paragraph("<b>Revenue (INR)</b>", cell_bold),
        ]]
        for r in perf["daily_trends"][:30]:
            d_rows.append([
                Paragraph(r["activity_date"], cell_reg),
                Paragraph(str(r["total_families"]), cell_reg),
                Paragraph(str(r["booked"]), cell_bold),
                Paragraph(str(r["pending"]), cell_reg),
                Paragraph(str(r["pilgrims_count"]), cell_reg),
                Paragraph(f"₹{r['booked_revenue']:,.2f}", cell_bold),
            ])
        t_daily = Table(d_rows, colWidths=[80, 70, 70, 70, 70, 160])
        t_daily.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_daily)
        story.append(Spacer(1, 10))

    elif r_type == "weekly":
        story.append(Paragraph("2. Weekly Operational Breakdown", sec_style))
        w_rows = [[
            Paragraph("<b>Calendar Week</b>", cell_bold),
            Paragraph("<b>Total Families</b>", cell_bold),
            Paragraph("<b>Booked</b>", cell_bold),
            Paragraph("<b>Pending</b>", cell_bold),
            Paragraph("<b>Devotees</b>", cell_bold),
            Paragraph("<b>Revenue (INR)</b>", cell_bold),
        ]]
        for r in perf["weekly_trends"][:26]:
            w_rows.append([
                Paragraph(r["activity_week"], cell_reg),
                Paragraph(str(r["total_families"]), cell_reg),
                Paragraph(str(r["booked"]), cell_bold),
                Paragraph(str(r["pending"]), cell_reg),
                Paragraph(str(r["pilgrims_count"]), cell_reg),
                Paragraph(f"₹{r['booked_revenue']:,.2f}", cell_bold),
            ])
        t_weekly = Table(w_rows, colWidths=[90, 80, 70, 70, 70, 140])
        t_weekly.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_weekly)
        story.append(Spacer(1, 10))

    elif r_type == "monthly":
        story.append(Paragraph("2. Monthly Booking Breakdown", sec_style))
        m_rows = [[
            Paragraph("<b>Month (YYYY-MM)</b>", cell_bold),
            Paragraph("<b>Total Families</b>", cell_bold),
            Paragraph("<b>Booked</b>", cell_bold),
            Paragraph("<b>Pending</b>", cell_bold),
            Paragraph("<b>Cancelled</b>", cell_bold),
            Paragraph("<b>Revenue (INR)</b>", cell_bold),
        ]]
        for r in perf["monthly_trends"][:24]:
            m_rows.append([
                Paragraph(r["activity_month"], cell_reg),
                Paragraph(str(r["total_families"]), cell_reg),
                Paragraph(str(r["booked"]), cell_bold),
                Paragraph(str(r["pending"]), cell_reg),
                Paragraph(str(r["cancelled"]), cell_reg),
                Paragraph(f"₹{r['booked_revenue']:,.2f}", cell_bold),
            ])
        t_monthly = Table(m_rows, colWidths=[90, 80, 70, 70, 70, 140])
        t_monthly.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_monthly)
        story.append(Spacer(1, 10))

    elif r_type in ("family", "families"):
        story.append(Paragraph("2. Registered Family Roster & Booking Statuses", sec_style))
        fam_d = get_family_analytics(db_path=db_path, limit=50)
        fam_rows = [[
            Paragraph("<b>Code</b>", cell_bold),
            Paragraph("<b>Family Name</b>", cell_bold),
            Paragraph("<b>Phone</b>", cell_bold),
            Paragraph("<b>Devotees</b>", cell_bold),
            Paragraph("<b>Donation</b>", cell_bold),
            Paragraph("<b>Status</b>", cell_bold),
            Paragraph("<b>Ticket</b>", cell_bold),
        ]]
        for r in fam_d["family_records"]:
            fam_rows.append([
                Paragraph(r["family_code"], cell_reg),
                Paragraph(r["family_name"], cell_reg),
                Paragraph(r["phone"], cell_reg),
                Paragraph(str(r["pilgrim_count"]), cell_reg),
                Paragraph(f"₹{r['donation_amount']:,.0f}", cell_reg),
                Paragraph(r["status"], cell_bold),
                Paragraph("Yes" if r.get("has_ticket") else "No", cell_reg),
            ])
        t_fam = Table(fam_rows, colWidths=[65, 120, 80, 50, 70, 75, 60])
        t_fam.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_fam)
        story.append(Spacer(1, 10))

    elif r_type == "payment":
        story.append(Paragraph("2. Payment Status Summary & Date Collections", sec_style))
        pay_rows = [[
            Paragraph("<b>Payment Status</b>", cell_bold),
            Paragraph("<b>Transactions</b>", cell_bold),
            Paragraph("<b>Total Amount (INR)</b>", cell_bold),
            Paragraph("<b>With Reference</b>", cell_bold),
        ]]
        for pst, pitem in pay["payment_summary"].items():
            pay_rows.append([
                Paragraph(pst, cell_reg),
                Paragraph(str(pitem["count"]), cell_reg),
                Paragraph(f"₹{pitem['amount']:,.2f}", cell_bold),
                Paragraph(str(pitem.get("with_ref", 0)), cell_reg),
            ])
        t_pay = Table(pay_rows, colWidths=[130, 110, 150, 130])
        t_pay.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_pay)
        story.append(Spacer(1, 10))

    # Queue Intelligence & Aging Section
    story.append(Paragraph("2. Queue Aging & Bottleneck Intelligence", sec_style))
    aging_data = [
        [Paragraph("<b>Aging Bracket</b>", cell_bold), Paragraph("<b>Pending Volume</b>", cell_bold), Paragraph("<b>Percentage of Queue</b>", cell_bold)]
    ]
    tot_pend = queue["total_pending"]
    for bracket, count in queue["aging_buckets"].items():
        pct = round((count / tot_pend * 100.0), 1) if tot_pend > 0 else 0.0
        aging_data.append([
            Paragraph(bracket, cell_reg),
            Paragraph(str(count), cell_reg),
            Paragraph(f"{pct}%", cell_bold),
        ])

    t_aging = Table(aging_data, colWidths=[200, 160, 160])
    t_aging.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_aging)
    story.append(Spacer(1, 10))

    # Operational Alerts Section
    story.append(Paragraph("3. Operational Intelligence & Actionable Insights", sec_style))
    if ops["insights"]:
        insight_rows = [
            [Paragraph("<b>Severity</b>", cell_bold), Paragraph("<b>Category</b>", cell_bold), Paragraph("<b>Operational Finding & Recommended Action</b>", cell_bold)]
        ]
        for ins in ops["insights"]:
            sev_color = "#dc2626" if ins["severity"] == "CRITICAL" else ("#ea580c" if ins["severity"] == "HIGH" else "#0284c7")
            insight_rows.append([
                Paragraph(f"<font color='{sev_color}'><b>{ins['severity']}</b></font>", cell_bold),
                Paragraph(ins["category"], cell_reg),
                Paragraph(f"<b>{ins['title']}</b><br/>{ins['description']}<br/><i>Action: {ins['action']}</i>", cell_reg),
            ])
        t_ins = Table(insight_rows, colWidths=[70, 110, 340])
        t_ins.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_ins)
    else:
        story.append(Paragraph("<i>No critical operational bottlenecks or discrepancies currently detected.</i>", cell_reg))

    story.append(Spacer(1, 12))

    # Suggested Prioritization Section
    story.append(Paragraph("4. Suggested Sequential Queue Order (Rule-Based Heuristic)", sec_style))
    rec_rows = [
        [Paragraph("<b>Rank</b>", cell_bold), Paragraph("<b>Score</b>", cell_bold), Paragraph("<b>Family Code</b>", cell_bold), Paragraph("<b>Family Name</b>", cell_bold), Paragraph("<b>Date</b>", cell_bold), Paragraph("<b>Key Reasoning</b>", cell_bold)]
    ]
    for r_idx, rec in enumerate(ops["recommended_queue"][:10], start=1):
        rec_rows.append([
            Paragraph(f"#{r_idx}", cell_bold),
            Paragraph(str(rec["score"]), cell_bold),
            Paragraph(rec["family_code"], cell_reg),
            Paragraph(rec["family_name"], cell_reg),
            Paragraph(rec["preferred_date"] or "—", cell_reg),
            Paragraph(", ".join(rec["reasons"]), cell_reg),
        ])
    t_recs = Table(rec_rows, colWidths=[40, 45, 95, 120, 75, 145])
    t_recs.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_recs)
    story.append(Spacer(1, 14))

    # Regulatory & Operational Compliance Disclaimer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
    comp_text = (
        "CONFIDENTIAL & COMPLIANCE NOTICE: This analytics report is generated strictly from local SQLite database records. "
        "The software operates solely as an assisted record-keeping tool and does not predict or guarantee TTD quota allocations. "
        "Official TTD portal login, CAPTCHA, and payments remain under manual client control. "
        "Full identity proof numbers and financial credentials are never stored or exposed."
    )
    story.append(Paragraph(comp_text, compliance_style))

    doc_pdf.build(story, canvasmaker=NumberedCanvas)
    logger.info(f"Analytics executive PDF report generated: {out}")
    return out


# -----------------------------------------------------------------------------
# Unified Multi-Format Dispatchers (CSV, Excel, PDF)
# -----------------------------------------------------------------------------

def export_daily_report(
    dest_path: str | Path,
    export_format: str = "csv",
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate Daily Report in CSV, Excel (.xlsx), or PDF format."""
    fmt = (export_format or "csv").lower().strip()
    if fmt == "xlsx":
        return export_daily_report_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
    elif fmt == "pdf":
        return export_analytics_report_pdf("daily", dest_path, db_path, filter_type, custom_start, custom_end)
    else:
        return export_daily_report_csv(dest_path, db_path, filter_type, custom_start, custom_end)


def export_weekly_report(
    dest_path: str | Path,
    export_format: str = "csv",
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate Weekly Report in CSV, Excel (.xlsx), or PDF format."""
    fmt = (export_format or "csv").lower().strip()
    if fmt == "xlsx":
        return export_weekly_report_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
    elif fmt == "pdf":
        return export_analytics_report_pdf("weekly", dest_path, db_path, filter_type, custom_start, custom_end)
    else:
        return export_weekly_report_csv(dest_path, db_path, filter_type, custom_start, custom_end)


def export_monthly_report(
    dest_path: str | Path,
    export_format: str = "csv",
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate Monthly Report in CSV, Excel (.xlsx), or PDF format."""
    fmt = (export_format or "csv").lower().strip()
    if fmt == "xlsx":
        return export_monthly_report_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
    elif fmt == "pdf":
        return export_analytics_report_pdf("monthly", dest_path, db_path, filter_type, custom_start, custom_end)
    else:
        return export_monthly_report_csv(dest_path, db_path, filter_type, custom_start, custom_end)


def export_family_report(
    dest_path: str | Path,
    export_format: str = "csv",
    db_path: Optional[Path] = None,
    search_term: str = "",
    status_filter: str = "All",
    ticket_filter: str = "All",
) -> Path:
    """Generate Family-Wise Report in CSV, Excel (.xlsx), or PDF format."""
    fmt = (export_format or "csv").lower().strip()
    if fmt == "xlsx":
        return export_family_report_xlsx(dest_path, db_path, search_term, status_filter, ticket_filter)
    elif fmt == "pdf":
        return export_analytics_report_pdf("family", dest_path, db_path)
    else:
        return export_family_report_csv(dest_path, db_path, search_term, status_filter, ticket_filter)


def export_performance_report(
    dest_path: str | Path,
    export_format: str = "csv",
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate Booking Performance Report in CSV, Excel (.xlsx), or PDF format."""
    fmt = (export_format or "csv").lower().strip()
    if fmt == "xlsx":
        return export_daily_report_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
    elif fmt == "pdf":
        return export_analytics_report_pdf("performance", dest_path, db_path, filter_type, custom_start, custom_end)
    else:
        return export_performance_to_csv(dest_path, db_path, filter_type, custom_start, custom_end)


def export_payment_report(
    dest_path: str | Path,
    export_format: str = "csv",
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Path:
    """Generate Payment Report in CSV, Excel (.xlsx), or PDF format."""
    fmt = (export_format or "csv").lower().strip()
    if fmt == "xlsx":
        return export_payment_report_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
    elif fmt == "pdf":
        return export_analytics_report_pdf("payment", dest_path, db_path, filter_type, custom_start, custom_end)
    else:
        return export_payment_report_csv(dest_path, db_path, filter_type, custom_start, custom_end)


def export_report(
    report_type: str,
    export_format: str,
    dest_path: str | Path,
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    search_term: str = "",
    status_filter: str = "All",
    ticket_filter: str = "All",
) -> Path:
    """
    Master Dispatcher for generating all reports across CSV, Excel (.xlsx), and PDF.
    Guarantees that numbers match underlying database records exactly.
    """
    rt = (report_type or "summary").lower().strip()
    fmt = (export_format or "csv").lower().strip()

    if rt == "daily":
        return export_daily_report(dest_path, fmt, db_path, filter_type, custom_start, custom_end)
    elif rt == "weekly":
        return export_weekly_report(dest_path, fmt, db_path, filter_type, custom_start, custom_end)
    elif rt == "monthly":
        return export_monthly_report(dest_path, fmt, db_path, filter_type, custom_start, custom_end)
    elif rt in ("family", "family_wise", "families"):
        return export_family_report(dest_path, fmt, db_path, search_term, status_filter, ticket_filter)
    elif rt in ("performance", "booking_performance"):
        return export_performance_report(dest_path, fmt, db_path, filter_type, custom_start, custom_end)
    elif rt in ("payment", "payments"):
        return export_payment_report(dest_path, fmt, db_path, filter_type, custom_start, custom_end)
    elif rt in ("queue", "queue_intelligence"):
        if fmt == "pdf":
            return export_analytics_report_pdf("queue", dest_path, db_path)
        elif fmt == "xlsx":
            return export_full_analytics_workbook_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
        else:
            return export_queue_intelligence_to_csv(dest_path, db_path)
    elif rt in ("workbook", "full_workbook"):
        return export_full_analytics_workbook_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
    else:
        # Default summary / executive
        if fmt == "pdf":
            return export_analytics_report_pdf("summary", dest_path, db_path, filter_type, custom_start, custom_end)
        elif fmt == "xlsx":
            return export_full_analytics_workbook_xlsx(dest_path, db_path, filter_type, custom_start, custom_end)
        else:
            return export_summary_to_csv(dest_path, db_path, filter_type, custom_start, custom_end)
