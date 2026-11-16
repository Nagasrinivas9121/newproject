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
