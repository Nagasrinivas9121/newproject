"""
Unit tests for Search, Filters, and Queue Prioritization.
"""
from database import (
    add_family_with_pilgrims,
    get_all_families,
    update_status_and_payment,
    set_priority,
    shift_queue_order,
)

def test_search_and_filters(test_db):
    f1 = add_family_with_pilgrims({
        "family_code": "FAM-SRI-001",
        "family_name": "Narayana Family",
        "contact_name": "Srinivas Narayana",
        "phone": "9848012345",
        "booking_type": "Advance",
        "status": "Pending",
        "payment_status": "Paid",
        "priority": "Normal",
    }, [{"full_name": "Srinivas Narayana", "age": 40}], db_path=test_db)

    f2 = add_family_with_pilgrims({
        "family_code": "FAM-SRI-002",
        "family_name": "Govind Family",
        "contact_name": "Govind",
        "phone": "9440156789",
        "booking_type": "Current",
        "status": "Booked",
        "payment_status": "Paid",
        "priority": "Urgent",
    }, [{"full_name": "Govind", "age": 55}, {"full_name": "Padma", "age": 50}], db_path=test_db)

    # Search by family name
    res = get_all_families(search="Narayana", db_path=test_db)
    assert len(res) == 1
    assert res[0]["family_code"] == "FAM-SRI-001"

    # Search by pilgrim name
    res = get_all_families(search="Padma", db_path=test_db)
    assert len(res) == 1
    assert res[0]["family_code"] == "FAM-SRI-002"

    # Search by phone
    res = get_all_families(search="9440156789", db_path=test_db)
    assert len(res) == 1

    # Filter by status
    res = get_all_families(status="Pending", db_path=test_db)
    assert len(res) == 1
    assert res[0]["id"] == f1

    res = get_all_families(status="Booked", db_path=test_db)
    assert len(res) == 1
    assert res[0]["id"] == f2

    # Filter by booking type
    res = get_all_families(booking_type="Current", db_path=test_db)
    assert len(res) == 1
    assert res[0]["id"] == f2

def test_queue_prioritization(test_db):
    # Create 3 families
    f_normal = add_family_with_pilgrims({
        "family_code": "FAM-NORM", "family_name": "Normal Fam", "priority": "Normal", "status": "Pending"
    }, [{"full_name": "P1"}], db_path=test_db)

    f_urgent = add_family_with_pilgrims({
        "family_code": "FAM-URG", "family_name": "Urgent Fam", "priority": "Urgent", "status": "Pending"
    }, [{"full_name": "P2"}], db_path=test_db)

    f_high = add_family_with_pilgrims({
        "family_code": "FAM-HIGH", "family_name": "High Fam", "priority": "High", "status": "Pending"
    }, [{"full_name": "P3"}], db_path=test_db)

    # In queue sorting, Urgent must be first, then High, then Normal
    ordered = get_all_families(sort_by="queue", db_path=test_db)
    assert ordered[0]["family_code"] == "FAM-URG"
    assert ordered[1]["family_code"] == "FAM-HIGH"
    assert ordered[2]["family_code"] == "FAM-NORM"

    # Pending must come before Booked even within same priority
    update_status_and_payment(f_urgent, "Booked", "Paid", db_path=test_db)
    ordered_after_book = get_all_families(sort_by="queue", db_path=test_db)
    # Since FAM-URG is Booked, and FAM-HIGH is Pending, FAM-HIGH is served first!
    assert ordered_after_book[0]["family_code"] == "FAM-HIGH"
