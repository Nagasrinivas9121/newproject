"""
SRIVANI BOOKING MANAGER - Ticket PDF Storage, Organization & Slip Generator
"""
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from config import TICKETS_DIR
from database import get_connection, update_family, log_queue_action

def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for duplicate detection."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def sanitize_filename(name: str) -> str:
    """Sanitize string for safe filenames."""
    keepchars = ('-', '_', '.', ' ')
    return "".join(c for c in name if c.isalnum() or c in keepchars).rstrip()

def store_ticket_pdf(
    family_id: int,
    family_code: str,
    source_pdf_path: str | Path,
    ticket_number: Optional[str] = None,
    allow_reimport_same_family: bool = False,
    db_path: Optional[Path] = None,
) -> Path:
    """
    Copy and organize ticket PDF into data/tickets/<family_code>/ directory.
    Detects and prevents duplicate ticket PDF imports using SHA-256 checksums.
    Updates the database with the stored path, ticket number, and checksum.
    Returns destination path.
    """
    src = Path(source_pdf_path)
    if not src.exists():
        raise FileNotFoundError(f"Source PDF file does not exist: {source_pdf_path}")

    # Verify PDF header
    with open(src, "rb") as f:
        header = f.read(5)
        if not header.startswith(b"%PDF"):
            raise ValueError("Invalid File Format: The selected file does not appear to be a valid PDF document.")

    # Calculate SHA-256 checksum
    checksum = compute_file_sha256(src)

    # Check for duplicate ticket in database
    with get_connection(db_path) as con:
        dup = con.execute(
            "SELECT id, family_code, family_name, ticket_pdf_path FROM families WHERE ticket_checksum = ?",
            (checksum,),
        ).fetchone()

        if dup:
            if dup["id"] != family_id:
                raise ValueError(
                    f"Duplicate Ticket Error: This exact ticket PDF has already been imported for family '{dup['family_name']}' ({dup['family_code']}). "
                    f"Duplicate import cancelled to preserve audit integrity."
                )
            elif not allow_reimport_same_family:
                raise ValueError(
                    f"Duplicate Ticket Error: This exact ticket PDF is already attached to this family ({family_code})."
                )

    # Create family-specific directory
    family_folder = TICKETS_DIR / sanitize_filename(family_code)
    family_folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_filename = f"{sanitize_filename(family_code)}_Ticket_{timestamp}.pdf"
    dest_path = family_folder / dest_filename

    shutil.copy2(src, dest_path)

    # Update database
    now_str = datetime.now().isoformat(timespec="seconds")
    update_data = {
        "ticket_pdf_path": str(dest_path),
        "ticket_checksum": checksum,
        "ticket_imported_at": now_str,
    }
    if ticket_number:
        update_data["ticket_number"] = ticket_number.strip()

    update_family(family_id, update_data, db_path=db_path)

    # Log into queue history
    log_queue_action(
        family_id=family_id,
        family_code=family_code,
        family_name=f"Family #{family_id}",
        action="TICKET_IMPORTED",
        notes=f"Imported ticket file: {dest_filename}. Ticket No: {ticket_number or 'N/A'}",
        db_path=db_path,
    )

    return dest_path

def open_ticket_pdf(pdf_path: str | Path) -> bool:
    """Open PDF with default system viewer on Windows."""
    p = Path(pdf_path)
    if not p.exists():
        return False
    try:
        os.startfile(str(p))
        return True
    except Exception:
        # Fallback to subprocess
        import subprocess
        try:
            subprocess.Popen(["start", "", str(p)], shell=True)
            return True
        except Exception:
            return False

def generate_booking_slip_pdf(
    family_dict: Dict[str, Any],
    pilgrims_list: List[Dict[str, Any]],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate an official-looking Srivani Booking Summary Slip using ReportLab.
    Saved to family's ticket folder or custom output path.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    family_code = family_dict.get("family_code", "UNKNOWN")
    if not output_path:
        family_folder = TICKETS_DIR / sanitize_filename(family_code)
        family_folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = family_folder / f"{sanitize_filename(family_code)}_SummarySlip_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1B365D'),
        alignment=1,  # Center
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#555555'),
        alignment=1,
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1B365D'),
        spaceBefore=10,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
    )
    bold_cell_style = ParagraphStyle(
        'BoldCellText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#222222'),
    )

    story = []

    # Header
    story.append(Paragraph("SRI VENKATESWARA AALAYA NIRMANAM TRUST (SRIVANI)", title_style))
    story.append(Paragraph("VIP Break Darshan Booking Summary & Pilgrim Record", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1B365D'), spaceBefore=2, spaceAfter=15))

    # Family & Donor Overview Table
    family_info = [
        [
            Paragraph("Family Code:", bold_cell_style), Paragraph(str(family_dict.get("family_code", "")), cell_style),
            Paragraph("Booking Status:", bold_cell_style), Paragraph(str(family_dict.get("status", "")), cell_style),
        ],
        [
            Paragraph("Family Name:", bold_cell_style), Paragraph(str(family_dict.get("family_name", "")), cell_style),
            Paragraph("Payment Status:", bold_cell_style), Paragraph(str(family_dict.get("payment_status", "")), cell_style),
        ],
        [
            Paragraph("Contact Person:", bold_cell_style), Paragraph(str(family_dict.get("contact_name", "")), cell_style),
            Paragraph("Donation Amount:", bold_cell_style), Paragraph(f"₹{float(family_dict.get('donation_amount') or 0):,.2f}", cell_style),
        ],
        [
            Paragraph("Phone:", bold_cell_style), Paragraph(str(family_dict.get("phone", "")), cell_style),
            Paragraph("Booking Type:", bold_cell_style), Paragraph(str(family_dict.get("booking_type", "")), cell_style),
        ],
        [
            Paragraph("Preferred Date:", bold_cell_style), Paragraph(str(family_dict.get("preferred_date", "Pending")), cell_style),
            Paragraph("Ticket / Ref No:", bold_cell_style), Paragraph(str(family_dict.get("ticket_number") or "N/A"), cell_style),
        ],
    ]

    t_family = Table(family_info, colWidths=[110, 155, 110, 155])
    t_family.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_family)
    story.append(Spacer(1, 15))

    # Pilgrims Details Section
    story.append(Paragraph(f"Registered Pilgrims ({len(pilgrims_list)} Devotee{'s' if len(pilgrims_list) != 1 else ''})", section_title))

    pilgrim_table_data = [
        [
            Paragraph("<b>#</b>", cell_style),
            Paragraph("<b>Full Name</b>", cell_style),
            Paragraph("<b>Age</b>", cell_style),
            Paragraph("<b>Gender</b>", cell_style),
            Paragraph("<b>ID Proof Type</b>", cell_style),
            Paragraph("<b>ID Last 4</b>", cell_style),
        ]
    ]

    for idx, p in enumerate(pilgrims_list, start=1):
        pilgrim_table_data.append([
            Paragraph(str(idx), cell_style),
            Paragraph(str(p.get("full_name", "")), bold_cell_style),
            Paragraph(str(p.get("age") or "-"), cell_style),
            Paragraph(str(p.get("gender") or "-"), cell_style),
            Paragraph(str(p.get("id_proof_type") or "-"), cell_style),
            Paragraph(str(p.get("id_proof_last4") or "-"), cell_style),
        ])

    t_pilgrims = Table(pilgrim_table_data, colWidths=[30, 190, 45, 75, 105, 85])
    t_pilgrims.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B365D')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F5F9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_pilgrims)

    # Footer note
    story.append(Spacer(1, 20))
    notice_text = (
        "<b>Important Instructions:</b><br/>"
        "• All devotees must carry the original ID proof used at the time of booking.<br/>"
        "• Traditional dress code is mandatory for Srivani VIP Break Darshan.<br/>"
        "• Official darshan reporting time and entry gate are determined strictly as per the TTD e-receipt.<br/>"
        "• Generated by Srivani Booking Manager • Single Admin Client Suite."
    )
    notice_style = ParagraphStyle(
        'Notice',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#64748B'),
    )
    story.append(Paragraph(notice_text, notice_style))

    doc.build(story)
    return output_path
