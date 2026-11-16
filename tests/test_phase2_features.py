"""
Unit tests specifically verifying Phase 2 requirements:
- Dashboard 6 summary metrics
- Queue history and audit logging
- Duplicate family prevention
- Excel & CSV pre-import analysis & duplicate detection
"""
from pathlib import Path
from database import (
    add_family_with_pilgrims,
    update_status_and_payment,
    set_priority,
    delete_family,
    get_queue_history,
    check_existing_family,
    get_stats,
)
from import_export import (
    analyze_import_file,
    commit_import_from_analysis,
    create_sample_excel_template,
)

def test_dashboard_summary_metrics(test_db):
    # Add pending family
    add_family_with_pilgrims(
        {"family_code": "FAM-ST1", "family_name": "Fam 1", "status": "Pending"},
        [{"full_name": "P1"}, {"full_name": "P2"}],
        db_path=test_db,
    )
    # Add in-progress family
    add_family_with_pilgrims(
        {"family_code": "FAM-ST2", "family_name": "Fam 2", "status": "In progress"},
        [{"full_name": "P3"}],
        db_path=test_db,
    )
    # Add booked family
    add_family_with_pilgrims(
        {"family_code": "FAM-ST3", "family_name": "Fam 3", "status": "Booked"},
        [{"full_name": "P4"}],
        db_path=test_db,
    )
    # Add cancelled family
    add_family_with_pilgrims(
        {"family_code": "FAM-ST4", "family_name": "Fam 4", "status": "Cancelled"},
        [{"full_name": "P5"}],
        db_path=test_db,
    )

    stats = get_stats(db_path=test_db)
    # Verify the 6 specific Phase 2 summary cards
    assert stats["total_families"] == 4
    assert stats["total_pilgrims"] == 5
    assert stats["pending_families"] == 1
    assert stats["in_progress"] == 1
    assert stats["booked"] == 1
    assert stats["cancelled"] == 1

def test_queue_history_audit_logging(test_db):
    fid = add_family_with_pilgrims(
        {"family_code": "FAM-HIST", "family_name": "Audit Family", "priority": "Normal", "status": "Pending"},
        [{"full_name": "Devotee 1"}],
        db_path=test_db,
    )

    # Status update
    update_status_and_payment(fid, "In progress", "Request sent", notes="Operator assigned", db_path=test_db)
    # Priority update
    set_priority(fid, "Urgent", db_path=test_db)
    # Mark booked
    update_status_and_payment(fid, "Booked", "Paid", notes="Darshan booked successfully", db_path=test_db)

    # Check history
    history = get_queue_history(family_id=fid, db_path=test_db)
    assert len(history) >= 4

    actions = [h["action"] for h in history]
    assert "STATUS_UPDATED" in actions
    assert "PRIORITY_CHANGED" in actions
    assert "FAMILY_CREATED" in actions

    # Check delete history
    delete_family(fid, db_path=test_db)
    del_history = get_queue_history(db_path=test_db)
    del_actions = [h["action"] for h in del_history]
    assert "FAMILY_DELETED" in del_actions

def test_duplicate_family_detection(test_db):
    add_family_with_pilgrims(
        {"family_code": "FAM-DUP-01", "family_name": "Reddy Family", "phone": "9848011223"},
        [{"full_name": "Ramesh Reddy"}],
        db_path=test_db,
    )

    # Check match by phone
    match1 = check_existing_family("9848011223", "Any Other Name", db_path=test_db)
    assert match1 is not None
    assert match1["family_code"] == "FAM-DUP-01"

    # Check match by code
    match2 = check_existing_family("9999999999", "Random", family_code="FAM-DUP-01", db_path=test_db)
    assert match2 is not None
    assert match2["family_name"] == "Reddy Family"

    # Non-duplicate should return None
    match3 = check_existing_family("9123456780", "Different Family", family_code="FAM-NEW", db_path=test_db)
    assert match3 is None

def test_analyze_import_file_preview_and_duplicates(temp_dir, test_db):
    # Pre-populate DB with 1 family
    add_family_with_pilgrims(
        {"family_code": "FAM-EXISTING", "family_name": "Existing Family", "phone": "9848099887"},
        [{"full_name": "Devotee One"}],
        db_path=test_db,
    )

    # Create CSV containing:
    # 1. Devotee Two in FAM-EXISTING (EXISTING_FAMILY)
    # 2. Devotee One in FAM-EXISTING (DUPLICATE_DEVOTEE against DB)
    # 3. New Family + Devotee Three (VALID_NEW)
    # 4. Same Devotee Three in same new family repeated (DUPLICATE_DEVOTEE in file)
    # 5. Row with invalid age (INVALID)
    csv_path = temp_dir / "preview_test.csv"
    csv_content = (
        "family_code,family_name,phone,full_name,age,gender\n"
        "FAM-EXISTING,Existing Family,9848099887,Devotee Two,35,Male\n"
        "FAM-EXISTING,Existing Family,9848099887,Devotee One,40,Male\n"
        "FAM-BRANDNEW,Brand New Family,9440123456,Devotee Three,25,Female\n"
        "FAM-BRANDNEW,Brand New Family,9440123456,Devotee Three,25,Female\n"
        "FAM-BRANDNEW,Brand New Family,9440123456,Devotee Four,999,Female\n"
    )
    csv_path.write_text(csv_content, encoding="utf-8")

    analysis = analyze_import_file(csv_path, db_path=test_db)
    summary = analysis["summary"]

    assert summary["total_rows"] == 5
    assert summary["existing_family"] == 1
    assert summary["duplicates"] == 2  # 1 against DB, 1 in file
    assert summary["valid_new"] == 1
    assert summary["invalid"] == 1

    # Now commit from analysis
    imported, skipped, fam_count = commit_import_from_analysis(analysis, skip_duplicates=True, db_path=test_db)
    assert imported == 2  # Devotee Two and Devotee Three
    assert fam_count == 2
