"""
Unit tests for Ticket PDF storage, organization, and slip generation.
"""
from pathlib import Path
from ticket_manager import store_ticket_pdf, generate_booking_slip_pdf
from database import add_family_with_pilgrims, get_family

def test_store_ticket_pdf(temp_dir, test_db, monkeypatch):
    # Mock TICKETS_DIR in ticket_manager to point to temp_dir / "tickets"
    mock_tickets = temp_dir / "tickets"
    monkeypatch.setattr("ticket_manager.TICKETS_DIR", mock_tickets)

    # Create dummy source PDF
    src_pdf = temp_dir / "source_ticket.pdf"
    src_pdf.write_bytes(b"%PDF-1.4 dummy pdf content")

    family_id = add_family_with_pilgrims({"family_name": "Ticket Fam", "family_code": "FAM-TCK-99"}, [], db_path=test_db)
    
    stored_path = store_ticket_pdf(family_id, "FAM-TCK-99", src_pdf, ticket_number="SRI-887766", db_path=test_db)
    
    assert stored_path.exists()
    assert "FAM-TCK-99" in str(stored_path)

    fam = get_family(family_id, db_path=test_db)
    assert fam["ticket_pdf_path"] == str(stored_path)
    assert fam["ticket_number"] == "SRI-887766"

def test_generate_booking_slip_pdf(temp_dir):
    family_dict = {
        "family_code": "FAM-VIP-01",
        "family_name": "VIP Family",
        "contact_name": "Venkatesh",
        "phone": "9848011223",
        "donation_amount": 20000.0,
        "booking_type": "Advance",
        "preferred_date": "2026-12-30",
        "status": "Booked",
        "payment_status": "Paid",
        "ticket_number": "TTD-SRI-12345",
    }
    pilgrims_list = [
        {"full_name": "Venkatesh", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1111"},
        {"full_name": "Lakshmi", "age": 40, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "2222"},
    ]

    out_slip = temp_dir / "slip.pdf"
    res = generate_booking_slip_pdf(family_dict, pilgrims_list, output_path=out_slip)
    assert res.exists()
    assert res.stat().st_size > 1000  # ReportLab generated valid PDF
