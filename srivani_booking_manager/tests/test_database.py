"""
Unit tests for database operations, migrations, and cascade deletes.
"""
from database import (
    init_db,
    get_connection,
    add_family_with_pilgrims,
    get_family,
    get_family_pilgrims,
    update_family,
    delete_family,
    add_pilgrim,
    update_pilgrim,
    delete_pilgrim,
    update_status_and_payment,
    set_priority,
    get_all_families,
    get_stats,
)

def test_init_db_and_migrations(test_db):
    # Verify tables and migrated columns exist
    with get_connection(test_db) as con:
        cols = [r["name"] for r in con.execute("PRAGMA table_info(families)").fetchall()]
        assert "priority" in cols
        assert "ticket_pdf_path" in cols
        assert "ticket_number" in cols
        assert "email" in cols
        assert "address" in cols

def test_add_family_with_multiple_pilgrims(test_db):
    family_data = {
        "family_code": "FAM-TEST-001",
        "family_name": "Test Family",
        "contact_name": "John Doe",
        "phone": "9876543210",
        "email": "john@example.com",
        "donation_amount": 20000.0,
        "booking_type": "Advance",
        "preferred_date": "2026-12-25",
        "priority": "High",
    }
    pilgrims_data = [
        {"full_name": "John Doe", "age": 45, "gender": "Male", "id_proof_type": "Aadhaar", "id_proof_last4": "1234"},
        {"full_name": "Jane Doe", "age": 42, "gender": "Female", "id_proof_type": "Aadhaar", "id_proof_last4": "5678"},
    ]

    family_id = add_family_with_pilgrims(family_data, pilgrims_data, db_path=test_db)
    assert family_id > 0

    fam = get_family(family_id, db_path=test_db)
    assert fam["family_name"] == "Test Family"
    assert fam["priority"] == "High"
    assert fam["donation_amount"] == 20000.0

    pilgrims = get_family_pilgrims(family_id, db_path=test_db)
    assert len(pilgrims) == 2
    assert pilgrims[0]["full_name"] == "John Doe"
    assert pilgrims[1]["full_name"] == "Jane Doe"

def test_cascade_delete(test_db):
    family_data = {"family_name": "Delete Me", "family_code": "FAM-DEL"}
    pilgrims_data = [{"full_name": "Pilgrim 1", "age": 30}]
    family_id = add_family_with_pilgrims(family_data, pilgrims_data, db_path=test_db)

    # Check pilgrim exists
    assert len(get_family_pilgrims(family_id, db_path=test_db)) == 1

    # Delete family
    delete_family(family_id, db_path=test_db)

    # Both family and pilgrim should be gone
    assert get_family(family_id, db_path=test_db) is None
    with get_connection(test_db) as con:
        remaining_p = con.execute("SELECT COUNT(*) FROM pilgrims WHERE family_id = ?", (family_id,)).fetchone()[0]
        assert remaining_p == 0

def test_pilgrim_crud(test_db):
    family_id = add_family_with_pilgrims({"family_name": "Pilgrim CRUD Fam"}, [], db_path=test_db)
    
    # Add pilgrim
    p_id = add_pilgrim(family_id, {"full_name": "Alex", "age": 25, "gender": "Male"}, db_path=test_db)
    pilgrims = get_family_pilgrims(family_id, db_path=test_db)
    assert len(pilgrims) == 1
    assert pilgrims[0]["full_name"] == "Alex"

    # Update pilgrim
    update_pilgrim(p_id, {"full_name": "Alexander", "age": 26, "gender": "Male", "id_proof_type": "Passport", "id_proof_last4": "9999"}, db_path=test_db)
    pilgrims = get_family_pilgrims(family_id, db_path=test_db)
    assert pilgrims[0]["full_name"] == "Alexander"
    assert pilgrims[0]["age"] == 26
    assert pilgrims[0]["id_proof_last4"] == "9999"

    # Delete pilgrim
    delete_pilgrim(p_id, db_path=test_db)
    assert len(get_family_pilgrims(family_id, db_path=test_db)) == 0

def test_update_status_and_payment(test_db):
    family_id = add_family_with_pilgrims({"family_name": "Status Fam"}, [], db_path=test_db)
    update_status_and_payment(family_id, "Booked", "Paid", notes="Completed successfully", db_path=test_db)

    fam = get_family(family_id, db_path=test_db)
    assert fam["status"] == "Booked"
    assert fam["payment_status"] == "Paid"
    assert fam["notes"] == "Completed successfully"
    assert fam["booked_at"] is not None

def test_stats(test_db):
    add_family_with_pilgrims({"family_name": "F1", "donation_amount": 10000}, [{"full_name": "P1"}], db_path=test_db)
    f2_id = add_family_with_pilgrims({"family_name": "F2", "donation_amount": 20000}, [{"full_name": "P2"}, {"full_name": "P3"}], db_path=test_db)
    update_status_and_payment(f2_id, "Booked", "Paid", db_path=test_db)

    stats = get_stats(db_path=test_db)
    assert stats["total_families"] == 2
    assert stats["total_pilgrims"] == 3
    assert stats["pending"] == 1
    assert stats["booked"] == 1
    assert stats["paid_families"] == 1
    assert stats["total_donation"] == 30000.0
