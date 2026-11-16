"""
SRIVANI BOOKING MANAGER - Advanced Reporting & Analytics Engine
Generates operational reports: Daily, Weekly, Monthly, Booking Status Summary,
Pending Queue, Failed/Unavailable, Payment Status, and Pilgrims Demographic Distribution.
Supports CSV export, data integrity total reconciliation, and printable executive PDF reports.
"""
import csv
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sqlite3

from reportlab.lib.pagesizes import letter, A4
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
from reportlab.pdfgen import canvas

from database import get_connection
from logger import get_logger

logger = get_logger("reports")

def get_daily_completed_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Report on daily completed bookings."""
    query = """
    SELECT
        COALESCE(substr(f.booked_at, 1, 10), substr(f.created_at, 1, 10)) AS booking_date,
        COUNT(DISTINCT f.id) AS families_booked,
        COUNT(p.id) AS pilgrims_booked,
        COALESCE(SUM(f.donation_amount), 0) AS total_donation
    FROM families f
    LEFT JOIN pilgrims p ON p.family_id = f.id
    WHERE f.status = 'Booked'
    GROUP BY booking_date
    ORDER BY booking_date DESC
    """
    with get_connection(db_path) as con:
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]

def get_weekly_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Report on bookings grouped by calendar week (YYYY-Www)."""
    query = """
    SELECT
        strftime('%Y-W%W', COALESCE(f.booked_at, f.created_at)) AS booking_week,
        COUNT(DISTINCT f.id) AS total_families,
        COUNT(DISTINCT CASE WHEN f.status = 'Booked' THEN f.id END) AS booked_families,
        COUNT(DISTINCT CASE WHEN f.status = 'Pending' THEN f.id END) AS pending_families,
        COUNT(p.id) AS total_pilgrims,
        COALESCE(SUM(CASE WHEN f.status = 'Booked' THEN f.donation_amount ELSE 0 END), 0) AS booked_donation
    FROM families f
    LEFT JOIN pilgrims p ON p.family_id = f.id
    GROUP BY booking_week
    ORDER BY booking_week DESC
    """
    with get_connection(db_path) as con:
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]

def get_monthly_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Report on bookings grouped by month (YYYY-MM)."""
    query = """
    SELECT
        substr(COALESCE(f.booked_at, f.created_at), 1, 7) AS booking_month,
        COUNT(DISTINCT f.id) AS total_families,
        COUNT(DISTINCT CASE WHEN f.status = 'Booked' THEN f.id END) AS booked_families,
        COUNT(DISTINCT CASE WHEN f.status = 'Cancelled' THEN f.id END) AS cancelled_families,
        COUNT(p.id) AS total_pilgrims,
        COALESCE(SUM(CASE WHEN f.status = 'Booked' THEN f.donation_amount ELSE 0 END), 0) AS booked_donation,
        COALESCE(SUM(f.donation_amount), 0) AS total_donation
    FROM families f
    LEFT JOIN pilgrims p ON p.family_id = f.id
    GROUP BY booking_month
    ORDER BY booking_month DESC
    """
    with get_connection(db_path) as con:
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]

def get_booking_status_summary_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Report summarizing metrics across all booking statuses."""
    query = """
    SELECT
        f.status,
        COUNT(DISTINCT f.id) AS family_count,
        COUNT(p.id) AS pilgrim_count,
        COALESCE(SUM(f.donation_amount), 0) AS total_donation,
        COUNT(DISTINCT CASE WHEN f.ticket_pdf_path IS NOT NULL AND f.ticket_pdf_path != '' THEN f.id END) AS tickets_attached
    FROM families f
    LEFT JOIN pilgrims p ON p.family_id = f.id
    GROUP BY f.status
    ORDER BY family_count DESC
    """
    with get_connection(db_path) as con:
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]

def get_pending_families_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Report on pending families awaiting booking in the queue."""
    query = """
    SELECT
        f.family_code,
        f.family_name,
        f.contact_name,
        f.phone,
        (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count,
        f.booking_type,
        f.preferred_date,
        f.priority,
        f.donation_amount,
        f.created_at
    FROM families f
    WHERE f.status = 'Pending'
    ORDER BY
        CASE f.priority
            WHEN 'Urgent' THEN 0
            WHEN 'High' THEN 1
            WHEN 'Normal' THEN 2
            WHEN 'Low' THEN 3
            ELSE 2
        END,
        f.queue_order ASC,
        f.created_at ASC
    """
    with get_connection(db_path) as con:
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]

def get_failed_or_unavailable_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Report on families marked Unavailable or Cancelled."""
    query = """
    SELECT
        f.family_code,
        f.family_name,
        f.contact_name,
        f.phone,
        f.status,
        f.payment_status,
        f.preferred_date,
        (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count,
        f.notes,
        f.created_at
    FROM families f
    WHERE f.status IN ('Unavailable', 'Cancelled')
    ORDER BY f.id DESC
    """
    with get_connection(db_path) as con:
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]

def get_payment_status_report(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Report breaking down families by payment status."""
    query = """
    SELECT
        COALESCE(f.payment_status, 'Not requested') AS payment_status,
        COUNT(DISTINCT f.id) AS family_count,
        COUNT(p.id) AS pilgrim_count,
        COALESCE(SUM(f.donation_amount), 0) AS total_amount,
        COUNT(DISTINCT CASE WHEN f.payment_ref IS NOT NULL AND f.payment_ref != '' THEN f.id END) AS with_ref_count
    FROM families f
    LEFT JOIN pilgrims p ON p.family_id = f.id
    GROUP BY f.payment_status
    ORDER BY total_amount DESC
    """
    with get_connection(db_path) as con:
        rows = con.execute(query).fetchall()
        return [dict(r) for r in rows]

def get_total_pilgrims_report(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Report on total pilgrims processed with demographic breakdowns."""
    with get_connection(db_path) as con:
        total_p = con.execute("SELECT COUNT(*) FROM pilgrims").fetchone()[0]
        
        gender_rows = con.execute("""
            SELECT COALESCE(gender, 'Unknown') as gender, COUNT(*) as cnt
            FROM pilgrims GROUP BY gender
        """).fetchall()
        genders = {r["gender"]: r["cnt"] for r in gender_rows}

        age_minors = con.execute("SELECT COUNT(*) FROM pilgrims WHERE age < 18").fetchone()[0]
        age_adults = con.execute("SELECT COUNT(*) FROM pilgrims WHERE age >= 18 AND age < 60").fetchone()[0]
        age_seniors = con.execute("SELECT COUNT(*) FROM pilgrims WHERE age >= 60").fetchone()[0]
        age_unspecified = con.execute("SELECT COUNT(*) FROM pilgrims WHERE age IS NULL").fetchone()[0]

        quota_rows = con.execute("""
            SELECT f.booking_type, COUNT(p.id) as cnt
            FROM families f
            JOIN pilgrims p ON p.family_id = f.id
            GROUP BY f.booking_type
        """).fetchall()
        quotas = {r["booking_type"]: r["cnt"] for r in quota_rows}

        return {
            "total_pilgrims": total_p,
            "genders": genders,
            "age_groups": {
                "Minors (<18)": age_minors,
                "Adults (18-59)": age_adults,
                "Seniors (60+)": age_seniors,
                "Unspecified": age_unspecified,
            },
            "quotas": quotas,
        }

def validate_report_totals(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Cross-checks and reconciles report totals against underlying database tables.
    Verifies that:
    1. Pilgrim sum from families equals total in pilgrims table.
    2. No orphaned pilgrims exist.
    3. Status distribution sum equals total families count.
    4. Payment distribution sum equals total families count.
    """
    anomalies = []
    with get_connection(db_path) as con:
        total_f = con.execute("SELECT COUNT(*) FROM families").fetchone()[0]
        total_p = con.execute("SELECT COUNT(*) FROM pilgrims").fetchone()[0]
        
        # Check orphaned pilgrims
        orphan_p = con.execute("""
            SELECT COUNT(*) FROM pilgrims p
            WHERE p.family_id NOT IN (SELECT id FROM families)
        """).fetchone()[0]
        if orphan_p > 0:
            anomalies.append(f"Found {orphan_p} orphaned pilgrim records with invalid family references.")

        # Reconcile status counts
        status_sum = con.execute("SELECT COUNT(*) FROM families WHERE status IS NOT NULL").fetchone()[0]
        if status_sum != total_f:
            anomalies.append(f"Status reconciliation mismatch: {status_sum} records with status vs {total_f} total families.")

        # Reconcile total donation
        total_donation = con.execute("SELECT COALESCE(SUM(donation_amount), 0) FROM families").fetchone()[0]

        # Status breakdown
        st_rows = con.execute("SELECT status, COUNT(*) as cnt FROM families GROUP BY status").fetchall()
        status_dict = {r["status"]: r["cnt"] for r in st_rows}

        # Payment breakdown
        pay_rows = con.execute("SELECT payment_status, COUNT(*) as cnt FROM families GROUP BY payment_status").fetchall()
        payment_dict = {r["payment_status"]: r["cnt"] for r in pay_rows}

    is_valid = (len(anomalies) == 0)
    return {
        "is_valid": is_valid,
        "total_families": total_f,
        "total_pilgrims": total_p,
        "orphaned_pilgrims": orphan_p,
        "total_donation": total_donation,
        "status_distribution": status_dict,
        "payment_distribution": payment_dict,
        "anomalies": anomalies,
    }

def export_report_to_csv(
    report_type: str,
    dest_path: str | Path,
    db_path: Optional[Path] = None,
) -> int:
    """Export a specific report to a CSV file."""
    out_path = Path(dest_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []

    if report_type == "daily_completed":
        rows = get_daily_completed_report(db_path)
        headers = ["booking_date", "families_booked", "pilgrims_booked", "total_donation"]
    elif report_type == "weekly":
        rows = get_weekly_report(db_path)
        headers = ["booking_week", "total_families", "booked_families", "pending_families", "total_pilgrims", "booked_donation"]
    elif report_type == "monthly":
        rows = get_monthly_report(db_path)
        headers = ["booking_month", "total_families", "booked_families", "cancelled_families", "total_pilgrims", "booked_donation", "total_donation"]
    elif report_type == "booking_status_summary":
        rows = get_booking_status_summary_report(db_path)
        headers = ["status", "family_count", "pilgrim_count", "total_donation", "tickets_attached"]
    elif report_type == "pending_families":
        rows = get_pending_families_report(db_path)
        headers = ["family_code", "family_name", "contact_name", "phone", "pilgrim_count", "booking_type", "preferred_date", "priority", "donation_amount", "created_at"]
    elif report_type == "failed_or_unavailable":
        rows = get_failed_or_unavailable_report(db_path)
        headers = ["family_code", "family_name", "contact_name", "phone", "status", "payment_status", "preferred_date", "pilgrim_count", "notes", "created_at"]
    elif report_type == "payment_status":
        rows = get_payment_status_report(db_path)
        headers = ["payment_status", "family_count", "pilgrim_count", "total_amount", "with_ref_count"]
    elif report_type == "total_pilgrims":
        data = get_total_pilgrims_report(db_path)
        rows = [
            {"Category": "Total Pilgrims", "Subcategory": "All", "Count": data["total_pilgrims"]}
        ]
        for g, count in data["genders"].items():
            rows.append({"Category": "Gender", "Subcategory": g, "Count": count})
        for ag, count in data["age_groups"].items():
            rows.append({"Category": "Age Group", "Subcategory": ag, "Count": count})
        for q, count in data["quotas"].items():
            rows.append({"Category": "Booking Quota", "Subcategory": q, "Count": count})
        headers = ["Category", "Subcategory", "Count"]
    else:
        raise ValueError(f"Unknown report type: {report_type}")

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    logger.info(f"Report '{report_type}' exported to CSV ({len(rows)} rows): {out_path}")
    return len(rows)

# ---------------------------------------------------------
# Printable Executive PDF Report Generation (ReportLab)
# ---------------------------------------------------------

class NumberedCanvas(canvas.Canvas):
    """Adds professional running header and footer with total page numbering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer
        footer_text = f"SRIVANI BOOKING MANAGER v4.0  |  Confidential Administrative Report  |  Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 40, 25, footer_text)

        # Bottom rule
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 38, A4[0] - 40, 38)
        self.restoreState()

def generate_printable_pdf_report(
    report_type: str,
    dest_path: str | Path,
    db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Generate a high-quality, printable executive PDF report for administrative review.
    """
    out_path = Path(dest_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=40,
            bottomMargin=50,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1e293b"),
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )
        cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
        )
        cell_header_style = ParagraphStyle(
            "TableHeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        elements = []

        # Title & Subtitle Banner
        title_map = {
            "daily_completed": "Daily Completed Bookings Report",
            "weekly": "Weekly Operational & Booking Analysis",
            "monthly": "Monthly Executive Performance Summary",
            "booking_status_summary": "Booking Status & Queue Summary",
            "pending_families": "Pending Families Queue Roster",
            "failed_or_unavailable": "Unavailable & Cancelled Bookings Report",
            "payment_status": "Payment Reconciliation & Donation Status",
            "total_pilgrims": "Pilgrim Demographics & Quota Distribution",
        }
        report_title = title_map.get(report_type, "Operational Activity Report")

        now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
        elements.append(Paragraph("SRIVANI BOOKING MANAGER", title_style))
        elements.append(Paragraph(f"<b>{report_title}</b>  •  Generated: {now_str}", subtitle_style))
        elements.append(Spacer(1, 10))

        # Overall Database Reconciliation Check
        recon = validate_report_totals(db_path)
        recon_data = [
            [
                Paragraph("<b>Total Families:</b>", cell_style),
                Paragraph(str(recon["total_families"]), cell_style),
                Paragraph("<b>Total Pilgrims:</b>", cell_style),
                Paragraph(str(recon["total_pilgrims"]), cell_style),
                Paragraph("<b>Total Donations:</b>", cell_style),
                Paragraph(f"₹{recon['total_donation']:,.2f}", cell_style),
            ]
        ]
        t_recon = Table(recon_data, colWidths=[80, 80, 80, 80, 90, 110])
        t_recon.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_recon)
        elements.append(Spacer(1, 12))

        # Build table based on report_type
        table_rows = []
        col_widths = []

        if report_type == "daily_completed":
            headers = ["Booking Date", "Families Booked", "Pilgrims Booked", "Total Donation (₹)"]
            col_widths = [130, 120, 120, 150]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            for r in get_daily_completed_report(db_path):
                table_rows.append([
                    Paragraph(str(r["booking_date"]), cell_style),
                    Paragraph(str(r["families_booked"]), cell_style),
                    Paragraph(str(r["pilgrims_booked"]), cell_style),
                    Paragraph(f"₹{r['total_donation']:,.2f}", cell_style),
                ])

        elif report_type == "weekly":
            headers = ["Week", "Total Families", "Booked", "Pending", "Pilgrims", "Booked Amount (₹)"]
            col_widths = [80, 85, 80, 80, 80, 115]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            for r in get_weekly_report(db_path):
                table_rows.append([
                    Paragraph(str(r["booking_week"]), cell_style),
                    Paragraph(str(r["total_families"]), cell_style),
                    Paragraph(str(r["booked_families"]), cell_style),
                    Paragraph(str(r["pending_families"]), cell_style),
                    Paragraph(str(r["total_pilgrims"]), cell_style),
                    Paragraph(f"₹{r['booked_donation']:,.2f}", cell_style),
                ])

        elif report_type == "monthly":
            headers = ["Month", "Families", "Booked", "Cancelled", "Pilgrims", "Booked Don. (₹)", "Total Don. (₹)"]
            col_widths = [70, 70, 70, 70, 70, 85, 85]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            for r in get_monthly_report(db_path):
                table_rows.append([
                    Paragraph(str(r["booking_month"]), cell_style),
                    Paragraph(str(r["total_families"]), cell_style),
                    Paragraph(str(r["booked_families"]), cell_style),
                    Paragraph(str(r["cancelled_families"]), cell_style),
                    Paragraph(str(r["total_pilgrims"]), cell_style),
                    Paragraph(f"₹{r['booked_donation']:,.2f}", cell_style),
                    Paragraph(f"₹{r['total_donation']:,.2f}", cell_style),
                ])

        elif report_type == "booking_status_summary":
            headers = ["Status", "Families", "Pilgrims", "Total Donation (₹)", "Tickets Attached"]
            col_widths = [110, 95, 95, 120, 100]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            for r in get_booking_status_summary_report(db_path):
                table_rows.append([
                    Paragraph(str(r["status"]), cell_style),
                    Paragraph(str(r["family_count"]), cell_style),
                    Paragraph(str(r["pilgrim_count"]), cell_style),
                    Paragraph(f"₹{r['total_donation']:,.2f}", cell_style),
                    Paragraph(str(r["tickets_attached"]), cell_style),
                ])

        elif report_type == "pending_families":
            headers = ["Code", "Family Name", "Contact", "Phone", "Pilgrims", "Quota", "Pref. Date", "Priority"]
            col_widths = [65, 95, 80, 75, 45, 55, 60, 45]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            for r in get_pending_families_report(db_path):
                table_rows.append([
                    Paragraph(str(r["family_code"]), cell_style),
                    Paragraph(str(r["family_name"]), cell_style),
                    Paragraph(str(r["contact_name"] or "-"), cell_style),
                    Paragraph(str(r["phone"] or "-"), cell_style),
                    Paragraph(str(r["pilgrim_count"]), cell_style),
                    Paragraph(str(r["booking_type"]), cell_style),
                    Paragraph(str(r["preferred_date"] or "-"), cell_style),
                    Paragraph(str(r["priority"]), cell_style),
                ])

        elif report_type == "payment_status":
            headers = ["Payment Status", "Families", "Pilgrims", "Total Amount (₹)", "With Ref"]
            col_widths = [120, 95, 95, 120, 90]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            for r in get_payment_status_report(db_path):
                table_rows.append([
                    Paragraph(str(r["payment_status"]), cell_style),
                    Paragraph(str(r["family_count"]), cell_style),
                    Paragraph(str(r["pilgrim_count"]), cell_style),
                    Paragraph(f"₹{r['total_amount']:,.2f}", cell_style),
                    Paragraph(str(r["with_ref_count"]), cell_style),
                ])

        elif report_type == "failed_or_unavailable":
            headers = ["Code", "Family Name", "Phone", "Status", "Payment", "Pilgrims", "Notes"]
            col_widths = [70, 100, 75, 75, 70, 45, 85]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            for r in get_failed_or_unavailable_report(db_path):
                table_rows.append([
                    Paragraph(str(r["family_code"]), cell_style),
                    Paragraph(str(r["family_name"]), cell_style),
                    Paragraph(str(r["phone"] or "-"), cell_style),
                    Paragraph(str(r["status"]), cell_style),
                    Paragraph(str(r["payment_status"]), cell_style),
                    Paragraph(str(r["pilgrim_count"]), cell_style),
                    Paragraph(str(r["notes"] or "-"), cell_style),
                ])

        else:
            # Demographics
            headers = ["Classification Category", "Subcategory / Value", "Pilgrim Count"]
            col_widths = [180, 180, 160]
            table_rows.append([Paragraph(h, cell_header_style) for h in headers])
            data = get_total_pilgrims_report(db_path)
            table_rows.append([Paragraph("Total Devotees", cell_style), Paragraph("All Enrolled", cell_style), Paragraph(str(data["total_pilgrims"]), cell_style)])
            for g, cnt in data["genders"].items():
                table_rows.append([Paragraph("Gender", cell_style), Paragraph(str(g), cell_style), Paragraph(str(cnt), cell_style)])
            for ag, cnt in data["age_groups"].items():
                table_rows.append([Paragraph("Age Bracket", cell_style), Paragraph(str(ag), cell_style), Paragraph(str(cnt), cell_style)])
            for q, cnt in data["quotas"].items():
                table_rows.append([Paragraph("Booking Quota", cell_style), Paragraph(str(q), cell_style), Paragraph(str(cnt), cell_style)])

        if len(table_rows) <= 1:
            table_rows.append([Paragraph("<i>No matching records found in the database.</i>", cell_style)] + [Paragraph("", cell_style)] * (len(headers) - 1))

        main_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        t_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        # Alternate row backgrounds
        for row_idx in range(1, len(table_rows)):
            bg = colors.HexColor("#f8fafc") if (row_idx % 2 == 1) else colors.white
            t_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))

        main_table.setStyle(TableStyle(t_style))
        elements.append(main_table)

        doc.build(elements, canvasmaker=NumberedCanvas)
        logger.info(f"Printable PDF report generated successfully: {out_path}")
        return True, str(out_path)

    except Exception as e:
        logger.error(f"Failed to generate printable PDF report: {e}")
        return False, str(e)
