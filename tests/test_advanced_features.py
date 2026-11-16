"""
Unit tests for edge cases, backwards compatibility, and advanced features.
"""
import pytest
from pathlib import Path
import app
from database import (
    add_family_with_pilgrims,
    get_all_families,
    shift_queue_order,
    get_family,
)
from import_export import import_records, export_to_csv, export_to_excel
from ticket_manager import sanitize_filename

def test_legacy_compatibility(temp_dir, monkeypatch):
    # Test app.connect() and app.import_csv()
    test_db = temp_dir / "compat.db"
    monkeypatch.setattr("config.DB_PATH", test_db)
    monkeypatch.setattr("database.DB_PATH", test_db)
    app.init_db()

    con_context = app.connect()
    with con_context as con:
        cur = con.execute("SELECT COUNT(*) FROM families")
        assert cur.fetchone()[0] == 0

    csv_file = temp_dir / "compat.csv"
    csv_file.write_text(
        "family_name,full_name,age,phone\nReddy,Ramesh,45,9848011223\n",
        encoding="utf-8"
    )
    imported, skipped = app.import_csv(csv_file)
    assert imported == 1
    assert len(skipped) == 0

def test_import_missing_required_headers(temp_dir, test_db):
    bad_csv = temp_dir / "bad.csv"
    bad_csv.write_text("age,phone,gender\n45,9848011223,Male\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required columns"):
        import_records(bad_csv, db_path=test_db)

def test_import_empty_file(temp_dir, test_db):
    empty_csv = temp_dir / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")
    imported, skipped, fam_count = import_records(empty_csv, db_path=test_db)
    assert imported == 0
    assert len(skipped) == 1
    assert fam_count == 0

def test_sanitize_filename():
    assert sanitize_filename("FAM/001:Special*Test?") == "FAM001SpecialTest"
    assert sanitize_filename("FAM-2026_01.02") == "FAM-2026_01.02"

def test_shift_queue_order(test_db):
    f1 = add_family_with_pilgrims({"family_code": "FAM-Q1", "family_name": "Fam 1"}, [{"full_name": "P1"}], db_path=test_db)
    f2 = add_family_with_pilgrims({"family_code": "FAM-Q2", "family_name": "Fam 2"}, [{"full_name": "P2"}], db_path=test_db)
    f3 = add_family_with_pilgrims({"family_code": "FAM-Q3", "family_name": "Fam 3"}, [{"full_name": "P3"}], db_path=test_db)

    # Initial order: FAM-Q1, FAM-Q2, FAM-Q3
    initial = [f["family_code"] for f in get_all_families(sort_by="queue", db_path=test_db)]
    assert initial == ["FAM-Q1", "FAM-Q2", "FAM-Q3"]

    # Shift f2 up
    shift_queue_order(f2, "up", db_path=test_db)
    after_up = [f["family_code"] for f in get_all_families(sort_by="queue", db_path=test_db)]
    assert after_up == ["FAM-Q2", "FAM-Q1", "FAM-Q3"]

    # Shift f2 down
    shift_queue_order(f2, "down", db_path=test_db)
    after_down = [f["family_code"] for f in get_all_families(sort_by="queue", db_path=test_db)]
    assert after_down == ["FAM-Q1", "FAM-Q2", "FAM-Q3"]

def test_export_empty_db(temp_dir, test_db):
    empty_csv = temp_dir / "empty_out.csv"
    empty_xlsx = temp_dir / "empty_out.xlsx"
    c1 = export_to_csv(empty_csv, db_path=test_db)
    assert c1 == 0
    assert empty_csv.exists()

    c2 = export_to_excel(empty_xlsx, db_path=test_db)
    assert c2 == 0
    assert empty_xlsx.exists()
