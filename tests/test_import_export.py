"""
Unit tests for CSV and Excel (.xlsx) importing and exporting.
"""
from pathlib import Path
from import_export import (
    import_records,
    export_to_csv,
    export_to_excel,
    create_sample_excel_template,
)
from database import get_all_families, get_family_pilgrims

def test_csv_import_multi_pilgrim(temp_dir, test_db):
    csv_file = temp_dir / "test_families.csv"
    csv_content = (
        "family_code,family_name,contact_name,phone,donation_amount,booking_type,preferred_date,full_name,age,gender,id_proof_type,id_proof_last4\n"
        "FAM-101,Reddy Group,Ramesh Reddy,9848022338,20000,Advance,2026-12-25,Ramesh Reddy,46,Male,Aadhaar,1234\n"
        "FAM-101,Reddy Group,Ramesh Reddy,9848022338,20000,Advance,2026-12-25,Sita Reddy,42,Female,Aadhaar,5678\n"
        "FAM-102,Sharma,Anil,9440112233,10000,Current,,Anil Sharma,38,Male,Passport,9012\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    imported, skipped, families_count = import_records(csv_file, db_path=test_db)
    assert imported == 3
    assert len(skipped) == 0
    assert families_count == 2

    families = get_all_families(db_path=test_db)
    assert len(families) == 2

    # Verify grouping
    f1 = [f for f in families if f["family_code"] == "FAM-101"][0]
    p1 = get_family_pilgrims(f1["id"], db_path=test_db)
    assert len(p1) == 2
    assert p1[0]["full_name"] == "Ramesh Reddy"
    assert p1[1]["full_name"] == "Sita Reddy"

def test_excel_import(temp_dir, test_db):
    excel_file = temp_dir / "sample_template.xlsx"
    create_sample_excel_template(excel_file)
    assert excel_file.exists()

    imported, skipped, families_count = import_records(excel_file, db_path=test_db)
    assert imported >= 6
    assert families_count == 3

    families = get_all_families(db_path=test_db)
    assert len(families) == 3

def test_export_csv_and_excel(temp_dir, test_db):
    # First create template & import into DB
    excel_file = temp_dir / "source.xlsx"
    create_sample_excel_template(excel_file)
    import_records(excel_file, db_path=test_db)

    # Export to CSV
    out_csv = temp_dir / "exported.csv"
    count_csv = export_to_csv(out_csv, db_path=test_db)
    assert count_csv >= 6
    assert out_csv.exists()

    # Export to Excel
    out_xlsx = temp_dir / "exported.xlsx"
    count_xlsx = export_to_excel(out_xlsx, db_path=test_db)
    assert count_xlsx >= 6
    assert out_xlsx.exists()
