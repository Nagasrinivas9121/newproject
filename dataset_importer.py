"""
SRIVANI BOOKING MANAGER - Phase 10
Universal Dataset Import & Column Mapping Engine

Supports:
- CSV (.csv) with auto delimiter & encoding detection
- Excel (.xlsx, .xlsm, .xltx) via openpyxl
- Excel legacy (.xls) when supported
- Comprehensive column mapping with smart aliases
- Strict row-by-row validation & downloadable error reports
- 3-Way Duplicate Handling (SKIP, UPDATE, CANCEL)
- Atomic database transactions with rollback on critical failure
- Unique import batch IDs and immutable import history
"""

import csv
import io
import json
import re
import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import openpyxl

from config import (
    DB_PATH,
    SRIVANI_DONATION_PER_PERSON,
    BOOKING_TYPE_ADVANCE,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_UNAVAILABLE,
    STATUS_CANCELLED,
    PAYMENT_NOT_REQUESTED,
    PAYMENT_REQUEST_SENT,
    PAYMENT_PAID,
    PAYMENT_FAILED,
    PAYMENT_REFUNDED,
    PRIORITY_NORMAL,
    PRIORITY_URGENT,
    PRIORITY_HIGH,
    PRIORITY_LOW,
)
from database import get_connection, record_import_batch, generate_family_code
from backup_manager import create_database_backup
from validators import (
    clean_text,
    normalize_phone,
    normalize_date,
    validate_age,
    normalize_gender,
    normalize_id_proof_type,
    validate_id_proof_last4,
    validate_donation,
)
from readiness_engine import (
    normalize_booking_status,
    normalize_payment_tracking_status,
    calculate_booking_readiness,
)
from logger import get_logger

logger = get_logger("dataset_importer")

# Duplicate handling policies
DUP_POLICY_SKIP = "SKIP"
DUP_POLICY_UPDATE = "UPDATE"
DUP_POLICY_CANCEL = "CANCEL"
ALL_DUP_POLICIES = [DUP_POLICY_SKIP, DUP_POLICY_UPDATE, DUP_POLICY_CANCEL]

# Canonical application fields available for mapping
TARGET_FAMILY_FIELDS = [
    ("family_name", "Family Name (Required)", True),
    ("family_code", "Family ID / Code", False),
    ("contact_name", "Primary Contact Person", False),
    ("phone", "Mobile / Phone Number (Required)", True),
    ("email", "Email Address", False),
    ("address", "Residential Address / City", False),
    ("donation_amount", "Donation Amount (INR)", False),
    ("booking_status", "Booking Status", False),
    ("payment_status", "Payment Status", False),
    ("preferred_date", "Preferred Darshan Date", False),
    ("booking_type", "Booking Type (Advance/Current)", False),
    ("priority", "Queue Priority", False),
    ("notes", "Special Notes / Remarks", False),
]

TARGET_PILGRIM_FIELDS = [
    ("full_name", "Pilgrim Full Name (Required)", True),
    ("age", "Pilgrim Age", False),
    ("gender", "Pilgrim Gender (M/F)", False),
    ("id_proof_type", "ID Proof Type", False),
    ("id_proof_last4", "ID Proof Number / Last 4", False),
    ("document_status", "Document Verification Status", False),
]

ALL_TARGET_FIELDS = TARGET_FAMILY_FIELDS + TARGET_PILGRIM_FIELDS
TARGET_FIELD_NAMES = [f[0] for f in ALL_TARGET_FIELDS]

# Comprehensive alias mapping dictionary
COLUMN_ALIASES: Dict[str, List[str]] = {
    "family_name": [
        "family_name", "family", "family name", "group_name", "group", "family title",
        "primary devotee", "head of family", "head name", "donor group", "household",
        "household name", "household title",
    ],
    "family_code": [
        "family_code", "family_id", "family id", "code", "group_id", "booking id",
        "reg no", "registration number", "reference id", "family code",
    ],
    "contact_name": [
        "contact_name", "contact", "contact person", "donor_name", "donor",
        "primary_contact", "applicant name",
    ],
    "phone": [
        "phone", "mobile", "contact_number", "phone_number", "mobile_number", "cell",
        "mobile no", "phone no", "contact no", "telephone", "whatsapp",
        "contact mobile", "primary phone", "primary mobile",
    ],
    "email": [
        "email", "email_id", "e-mail", "email_address", "mail", "contact email",
    ],
    "address": [
        "address", "city", "residence", "location", "place", "state", "town",
        "home address", "postal address",
    ],
    "full_name": [
        "full_name", "pilgrim_name", "pilgrim", "name", "devotee_name", "devotee",
        "member_name", "person name", "yatri name", "yatri full name", "yatri",
        "devotee full name", "lead pilgrim",
    ],
    "age": [
        "age", "pilgrim age", "devotee age", "years", "dob age", "age (years)",
    ],
    "gender": [
        "gender", "sex", "m/f", "male/female",
    ],
    "id_proof_type": [
        "id_proof_type", "id_proof", "id_type", "proof_type", "id_card", "identity_type",
        "id document", "proof of id", "gov id", "id proof name",
    ],
    "id_proof_last4": [
        "id_proof_last4", "id_last4", "last4", "id_number", "aadhaar_last4", "id_last_4",
        "last_4_digits", "aadhaar", "aadhaar number", "id ref", "id reference",
    ],
    "donation_amount": [
        "donation_amount", "donation", "amount", "srivani_donation", "total_donation",
        "donation in inr", "contribution", "fee", "payment amount",
    ],
    "booking_status": [
        "booking_status", "status", "darshan status", "ticket status", "application status",
    ],
    "payment_status": [
        "payment_status", "payment", "payment state", "fee status", "pay status",
    ],
    "preferred_date": [
        "preferred_date", "date", "darshan_date", "booking_date", "travel_date",
        "visit date", "sewa date", "target date",
    ],
    "booking_type": [
        "booking_type", "booking", "type", "quota", "darshan_type", "booking category",
    ],
    "priority": [
        "priority", "queue_priority", "urgency", "queue rank",
    ],
    "notes": [
        "notes", "remarks", "comment", "instructions", "special requests",
    ],
}


def read_dataset_file(file_path: str | Path) -> Tuple[List[str], List[Dict[str, Any]], int, str]:
    """
    Read raw data records from a CSV or Excel spreadsheet.
    
    Returns:
    - headers: List of raw column headers from file
    - raw_rows: List of row dictionaries with '_row_num' metadata
    - file_size: Size of file in bytes
    - format_desc: Format name ('CSV' or 'Excel')
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = p.stat().st_size
    ext = p.suffix.lower()

    if ext == ".csv":
        # Multi-encoding & delimiter detection
        raw_bytes = p.read_bytes()
        encoding = "utf-8"
        for enc in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
            try:
                text_sample = raw_bytes[:4096].decode(enc)
                encoding = enc
                break
            except UnicodeDecodeError:
                continue

        text_content = raw_bytes.decode(encoding, errors="replace")
        sample = text_content[:2048]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            delimiter = dialect.delimiter
        except Exception:
            delimiter = ","

        reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
        try:
            first_row = next(reader)
        except StopIteration:
            return [], [], file_size, "CSV"

        headers = [str(h).strip() for h in first_row if str(h).strip()]
        raw_rows = []
        for line_num, r in enumerate(reader, start=2):
            if not any(str(cell).strip() for cell in r):
                continue
            row_dict = {"_row_num": line_num}
            for col_idx, h in enumerate(headers):
                row_dict[h] = r[col_idx] if col_idx < len(r) else ""
            raw_rows.append(row_dict)

        return headers, raw_rows, file_size, "CSV"

    elif ext in [".xlsx", ".xlsm", ".xltx"]:
        wb = openpyxl.load_workbook(str(p), data_only=True)
        ws = wb.active
        raw_rows = []
        headers = []

        first = True
        for line_num, row_cells in enumerate(ws.iter_rows(values_only=True), start=1):
            if first:
                headers = [str(c).strip() for c in row_cells if c is not None and str(c).strip()]
                first = False
                continue

            if not any(c is not None and str(c).strip() != "" for c in row_cells):
                continue

            row_dict = {"_row_num": line_num}
            for col_idx, h in enumerate(headers):
                val = row_cells[col_idx] if col_idx < len(row_cells) else ""
                if isinstance(val, (datetime.datetime, datetime.date)):
                    val = val.strftime("%Y-%m-%d")
                row_dict[h] = val if val is not None else ""
            raw_rows.append(row_dict)

        wb.close()
        return headers, raw_rows, file_size, "Excel (.xlsx)"

    elif ext == ".xls":
        try:
            import xlrd  # type: ignore
            book = xlrd.open_workbook(str(p))
            sheet = book.sheet_by_index(0)
            headers = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
            raw_rows = []
            for r in range(1, sheet.nrows):
                row_cells = [sheet.cell_value(r, c) for c in range(sheet.ncols)]
                if not any(str(c).strip() for c in row_cells):
                    continue
                row_dict = {"_row_num": r + 1}
                for c_idx, h in enumerate(headers):
                    row_dict[h] = row_cells[c_idx] if c_idx < len(row_cells) else ""
                raw_rows.append(row_dict)
            return headers, raw_rows, file_size, "Excel Legacy (.xls)"
        except ImportError:
            raise ValueError(
                "Legacy Excel (.xls) reader is not installed. "
                "Please save the file as modern Excel (.xlsx) or CSV (.csv) before importing."
            )

    else:
        raise ValueError(f"Unsupported file extension '{ext}'. Supported formats: .csv, .xlsx, .xls")


def detect_column_mapping(headers: List[str]) -> Dict[str, Optional[str]]:
    """
    Intelligently auto-map raw spreadsheet headers to canonical application fields.
    Does not guess ambiguous columns without confidence.
    """
    mapping: Dict[str, Optional[str]] = {}
    used_targets = set()

    for h in headers:
        if not h:
            continue
        normalized_h = str(h).strip().lower().replace("_", " ").replace("-", " ")

        best_target = None
        # Exact alias match
        for target, aliases in COLUMN_ALIASES.items():
            if target in used_targets:
                continue
            for alias in aliases:
                norm_alias = alias.replace("_", " ")
                if normalized_h == norm_alias:
                    best_target = target
                    break
            if best_target:
                break

        # Fallback substring match if high confidence
        if not best_target:
            for target, aliases in COLUMN_ALIASES.items():
                if target in used_targets:
                    continue
                for alias in aliases:
                    norm_alias = alias.replace("_", " ")
                    if norm_alias == normalized_h:
                        best_target = target
                        break
                if best_target:
                    break

        if best_target:
            mapping[h] = best_target
            used_targets.add(best_target)
        else:
            mapping[h] = None

    return mapping


def validate_and_analyze_dataset(
    headers: List[str],
    raw_rows: List[Dict[str, Any]],
    column_mapping: Dict[str, Optional[str]],
    dup_policy: str = DUP_POLICY_SKIP,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Validate the dataset and analyze new, duplicate, update, and invalid records.
    Pre-checks everything against the active SQLite database.
    """
    mapped_targets = {v for v in column_mapping.values() if v}

    # Core required fields check
    has_family_name = "family_name" in mapped_targets
    has_pilgrim_name = "full_name" in mapped_targets

    if not has_family_name and not has_pilgrim_name:
        raise ValueError("Mapping must include at least 'Family Name' or 'Pilgrim Full Name'.")

    # Fetch existing DB families and pilgrims for duplicate and update checks
    with get_connection(db_path) as con:
        db_fams = [dict(r) for r in con.execute("SELECT id, family_code, family_name, phone FROM families").fetchall()]
        db_pils = [dict(r) for r in con.execute("SELECT id, family_id, full_name FROM pilgrims").fetchall()]

    db_by_code = {str(f.get("family_code") or "").strip().lower(): f for f in db_fams if f.get("family_code")}
    db_by_phone = {str(f.get("phone") or "").strip(): f for f in db_fams if f.get("phone")}

    # Build DB pilgrim lookup: (family_id, pilgrim_name_lower) -> pilgrim_id
    db_pilgrim_map = {
        (p["family_id"], str(p.get("full_name") or "").strip().lower()): p["id"]
        for p in db_pils
    }

    valid_rows = []
    invalid_rows = []
    validation_errors = []

    seen_in_batch_families = set()
    seen_in_batch_pilgrims = set()

    new_families_count = 0
    updated_families_count = 0
    skipped_records_count = 0
    new_pilgrims_count = 0
    updated_pilgrims_count = 0
    duplicate_records_count = 0

    families_bundle: Dict[str, Dict[str, Any]] = {}

    for raw in raw_rows:
        row_num = raw.get("_row_num", 0)
        row_data: Dict[str, Any] = {}
        for h, target in column_mapping.items():
            if target:
                row_data[target] = raw.get(h, "")

        row_errors: List[Dict[str, Any]] = []

        # 1. Family Name resolution & Family Reference Check
        code = clean_text(row_data.get("family_code"))
        raw_fam_name = clean_text(row_data.get("family_name"))
        raw_pilgrim_name = clean_text(row_data.get("full_name"))
        phone_raw = row_data.get("phone")

        if code:
            if code.lower() in db_by_code:
                ref_fam = db_by_code[code.lower()]
                if not raw_fam_name:
                    raw_fam_name = ref_fam["family_name"]
                if not phone_raw and ref_fam.get("phone"):
                    phone_raw = ref_fam.get("phone")
            elif not raw_fam_name:
                row_errors.append({
                    "row": row_num,
                    "column": "family_code",
                    "value": code,
                    "error": f"Missing family reference: Family code '{code}' does not exist in database.",
                })

        if not raw_fam_name and raw_pilgrim_name:
            raw_fam_name = f"{raw_pilgrim_name} Family"

        if not raw_fam_name and not (code and code.lower() not in db_by_code):
            row_errors.append({"row": row_num, "column": "family_name", "value": "", "error": "Family Name is required."})

        # 2. Pilgrim Name resolution
        if not raw_pilgrim_name and not has_pilgrim_name:
            raw_pilgrim_name = clean_text(row_data.get("contact_name")) or raw_fam_name

        if not raw_pilgrim_name:
            row_errors.append({"row": row_num, "column": "full_name", "value": "", "error": "Pilgrim Full Name is required."})

        # 3. Phone validation
        phone_raw = row_data.get("phone")
        phone = ""
        if phone_raw:
            phone_clean, is_valid_phone = normalize_phone(phone_raw)
            if not is_valid_phone and str(phone_raw).strip() != "":
                row_errors.append({"row": row_num, "column": "phone", "value": str(phone_raw), "error": "Invalid 10-digit mobile number format."})
            phone = phone_clean

        # 4. Email validation
        email = clean_text(row_data.get("email"))
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            row_errors.append({"row": row_num, "column": "email", "value": email, "error": f"Invalid email format: '{email}'."})

        # 5. Age validation
        age_raw = row_data.get("age")
        age_val, is_age_valid = validate_age(age_raw)
        if not is_age_valid and str(age_raw).strip() != "":
            row_errors.append({"row": row_num, "column": "age", "value": str(age_raw), "error": f"Age must be an integer between 0 and 120."})

        # 6. Date validation
        date_raw = row_data.get("preferred_date")
        pref_date, is_date_valid = normalize_date(date_raw)
        if not is_date_valid and str(date_raw).strip() != "":
            row_errors.append({"row": row_num, "column": "preferred_date", "value": str(date_raw), "error": f"Unrecognized date format '{date_raw}' (use YYYY-MM-DD)."})

        # 7. Donation validation
        don_raw = row_data.get("donation_amount")
        donation, is_don_valid = validate_donation(don_raw)
        if not is_don_valid and str(don_raw).strip() != "":
            row_errors.append({"row": row_num, "column": "donation_amount", "value": str(don_raw), "error": "Donation amount must be a positive number."})

        # Other fields normalization
        gender = normalize_gender(row_data.get("gender"))
        id_type = normalize_id_proof_type(row_data.get("id_proof_type"))
        last4, _ = validate_id_proof_last4(row_data.get("id_proof_last4"))
        b_status = normalize_booking_status(row_data.get("booking_status"))
        
        # Resolve Queue Status (Pending, In progress, Booked, Unavailable, Cancelled)
        raw_b_status = clean_text(row_data.get("booking_status"))
        queue_status = STATUS_PENDING
        if raw_b_status:
            for s_opt in (STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_BOOKED, STATUS_UNAVAILABLE, STATUS_CANCELLED):
                if raw_b_status.lower() == s_opt.lower():
                    queue_status = s_opt
                    break

        p_status = normalize_payment_tracking_status(row_data.get("payment_status"))
        b_type = clean_text(row_data.get("booking_type")) or BOOKING_TYPE_ADVANCE
        prio = clean_text(row_data.get("priority")) or PRIORITY_NORMAL
        notes = clean_text(row_data.get("notes"))
        code = clean_text(row_data.get("family_code"))

        # Grouping key for family grouping in dataset
        if code:
            fam_group_key = f"CODE:{code.upper()}"
        elif phone:
            fam_group_key = f"PHONE:{phone}"
        else:
            fam_group_key = f"NAME:{raw_fam_name.lower()}"

        if row_errors:
            invalid_rows.append({"row_num": row_num, "errors": row_errors, "raw": row_data})
            validation_errors.extend(row_errors)
            continue

        # Check for duplicate pilgrim in file batch
        pilgrim_batch_key = (fam_group_key, raw_pilgrim_name.lower())
        if pilgrim_batch_key in seen_in_batch_pilgrims:
            dup_err = {"row": row_num, "column": "full_name", "value": raw_pilgrim_name, "error": f"Duplicate pilgrim '{raw_pilgrim_name}' repeated in dataset for same family."}
            row_errors.append(dup_err)
            validation_errors.append(dup_err)
            invalid_rows.append({"row_num": row_num, "errors": [dup_err], "raw": row_data})
            duplicate_records_count += 1
            continue

        seen_in_batch_pilgrims.add(pilgrim_batch_key)

        # Check DB duplicates
        matched_db_family = None
        if code and code.lower() in db_by_code:
            matched_db_family = db_by_code[code.lower()]
        elif phone and phone in db_by_phone:
            matched_db_family = db_by_phone[phone]

        fam_is_duplicate = matched_db_family is not None
        pilgrim_is_duplicate = False
        if matched_db_family:
            p_key = (matched_db_family["id"], raw_pilgrim_name.lower())
            if p_key in db_pilgrim_map:
                pilgrim_is_duplicate = True
                duplicate_records_count += 1

        # Evaluate duplicate policy
        action = "INSERT"
        if pilgrim_is_duplicate:
            if dup_policy == DUP_POLICY_CANCEL:
                raise ValueError(
                    f"Duplicate record detected on row {row_num}: "
                    f"Family '{raw_fam_name}' / Pilgrim '{raw_pilgrim_name}' already exists in database. "
                    f"Import aborted per policy DUP_POLICY_CANCEL."
                )
            elif dup_policy == DUP_POLICY_UPDATE:
                action = "UPDATE"
                updated_pilgrims_count += 1
            elif dup_policy == DUP_POLICY_SKIP:
                action = "SKIP"
                skipped_records_count += 1
        elif fam_is_duplicate:
            if dup_policy == DUP_POLICY_CANCEL and not has_pilgrim_name:
                raise ValueError(
                    f"Duplicate family detected on row {row_num}: "
                    f"Family '{raw_fam_name}' already exists in database. "
                    f"Import aborted per policy DUP_POLICY_CANCEL."
                )
            elif dup_policy == DUP_POLICY_UPDATE:
                action = "INSERT"
                if fam_group_key not in seen_in_batch_families:
                    updated_families_count += 1
            else:
                action = "INSERT"

        if action == "INSERT":
            if fam_group_key not in seen_in_batch_families and not fam_is_duplicate:
                new_families_count += 1
            new_pilgrims_count += 1

        seen_in_batch_families.add(fam_group_key)

        analyzed_item = {
            "row_num": row_num,
            "action": action,
            "fam_group_key": fam_group_key,
            "matched_db_family_id": matched_db_family["id"] if matched_db_family else None,
            "matched_db_pilgrim_id": db_pilgrim_map.get((matched_db_family["id"], raw_pilgrim_name.lower())) if matched_db_family else None,
            "family_code": code,
            "family_name": raw_fam_name,
            "contact_name": clean_text(row_data.get("contact_name")) or raw_fam_name,
            "phone": phone,
            "email": email,
            "address": clean_text(row_data.get("address")),
            "donation_amount": donation,
            "booking_status": b_status,
            "payment_status": p_status,
            "preferred_date": pref_date,
            "booking_type": b_type,
            "priority": prio,
            "notes": notes,
            "pilgrim": {
                "full_name": raw_pilgrim_name,
                "age": age_val,
                "gender": gender,
                "id_proof_type": id_type,
                "id_proof_last4": last4,
                "document_status": clean_text(row_data.get("document_status")) or "Pending Verification",
            },
        }
        valid_rows.append(analyzed_item)

        # Aggregate by family
        if action in ("INSERT", "UPDATE"):
            if fam_group_key not in families_bundle:
                fam_action = "UPDATE" if (fam_is_duplicate and dup_policy == DUP_POLICY_UPDATE) else "INSERT"
                families_bundle[fam_group_key] = {
                    "action": fam_action,
                    "db_family_id": matched_db_family["id"] if matched_db_family else None,
                    "family_code": code,
                    "family_name": raw_fam_name,
                    "contact_name": clean_text(row_data.get("contact_name")) or raw_fam_name,
                    "phone": phone,
                    "email": email,
                    "address": clean_text(row_data.get("address")),
                    "donation_amount": donation,
                    "booking_status": b_status,
                    "queue_status": queue_status,
                    "payment_status": p_status,
                    "preferred_date": pref_date,
                    "booking_type": b_type,
                    "priority": prio,
                    "notes": notes,
                    "pilgrims": [],
                }
            families_bundle[fam_group_key]["pilgrims"].append(analyzed_item)

    return {
        "total_rows": len(raw_rows),
        "valid_rows_count": len(valid_rows),
        "invalid_rows_count": len(invalid_rows),
        "new_families_count": new_families_count,
        "new_pilgrims_count": new_pilgrims_count,
        "updated_families_count": updated_families_count,
        "updated_pilgrims_count": updated_pilgrims_count,
        "skipped_records_count": skipped_records_count,
        "duplicate_records_count": duplicate_records_count,
        "validation_errors": validation_errors,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "families_bundle": families_bundle,
    }


def execute_dataset_import(
    analysis: Dict[str, Any],
    file_name: str,
    file_size: int,
    file_format: str,
    column_mapping: Dict[str, Optional[str]],
    admin_user: str = "admin",
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Commit pre-validated dataset to the SQLite database within an atomic transaction.
    Rolls back automatically on critical database failures.
    Records batch to import_batches table and returns summary.
    """
    batch_id = f"BATCH-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    families_bundle = analysis.get("families_bundle", {})
    successful_count = 0
    updated_count = 0
    skipped_count = analysis.get("skipped_records_count", 0)
    failed_count = analysis.get("invalid_rows_count", 0)

    # Create pre-import database backup before any database changes
    try:
        create_database_backup(db_path=db_path)
    except Exception as e:
        logger.warning(f"Pre-import database backup warning: {e}")

    try:
        with get_connection(db_path) as con:
            for group_key, fam_info in families_bundle.items():
                action = fam_info.get("action", "INSERT")
                db_fid = fam_info.get("db_family_id")

                if action == "UPDATE" and db_fid:
                    # Update existing family
                    con.execute("""
                        UPDATE families SET
                            family_name = COALESCE(NULLIF(?, ''), family_name),
                            contact_name = COALESCE(NULLIF(?, ''), contact_name),
                            email = COALESCE(NULLIF(?, ''), email),
                            address = COALESCE(NULLIF(?, ''), address),
                            preferred_date = COALESCE(NULLIF(?, ''), preferred_date),
                            notes = COALESCE(NULLIF(?, ''), notes)
                        WHERE id = ?
                    """, (
                        fam_info["family_name"],
                        fam_info["contact_name"],
                        fam_info["email"],
                        fam_info["address"],
                        fam_info["preferred_date"],
                        fam_info["notes"],
                        db_fid,
                    ))
                    family_id = db_fid
                    updated_count += 1
                elif db_fid:
                    # Reuse existing family ID when matching existing family is found in DB
                    family_id = db_fid
                else:
                    # Insert new family
                    code = fam_info.get("family_code") or generate_family_code()
                    donation = fam_info.get("donation_amount")
                    if not donation or donation <= 0:
                        donation = len(fam_info.get("pilgrims", [])) * SRIVANI_DONATION_PER_PERSON

                    cur = con.execute("""
                        INSERT INTO families (
                            family_code, family_name, contact_name, phone, email, address,
                            donation_amount, booking_type, preferred_date, status, payment_status,
                            priority, notes, created_at, readiness_status, readiness_score
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NOT_STARTED', 0)
                    """, (
                        code,
                        fam_info["family_name"],
                        fam_info["contact_name"],
                        fam_info["phone"],
                        fam_info["email"],
                        fam_info["address"],
                        donation,
                        fam_info["booking_type"],
                        fam_info["preferred_date"],
                        fam_info.get("queue_status", STATUS_PENDING),
                        fam_info["payment_status"],
                        fam_info["priority"],
                        fam_info["notes"],
                        now_str,
                    ))
                    family_id = cur.lastrowid
                    successful_count += 1

                # Process pilgrims for this family
                for p_item in fam_info.get("pilgrims", []):
                    p_data = p_item["pilgrim"]
                    p_action = p_item.get("action", "INSERT")
                    db_pid = p_item.get("matched_db_pilgrim_id")

                    if p_action == "UPDATE" and db_pid:
                        con.execute("""
                            UPDATE pilgrims SET
                                age = COALESCE(?, age),
                                gender = COALESCE(NULLIF(?, ''), gender),
                                id_proof_type = COALESCE(NULLIF(?, ''), id_proof_type),
                                id_proof_last4 = COALESCE(NULLIF(?, ''), id_proof_last4)
                            WHERE id = ?
                        """, (
                            p_data["age"],
                            p_data["gender"],
                            p_data["id_proof_type"],
                            p_data["id_proof_last4"],
                            db_pid,
                        ))
                        updated_count += 1
                    else:
                        con.execute("""
                            INSERT INTO pilgrims (
                                family_id, full_name, age, gender, id_proof_type, id_proof_last4
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            family_id,
                            p_data["full_name"],
                            p_data["age"],
                            p_data["gender"],
                            p_data["id_proof_type"],
                            p_data["id_proof_last4"],
                        ))
                        successful_count += 1

                # Re-calculate readiness score for family
                pils_db = [dict(r) for r in con.execute("SELECT * FROM pilgrims WHERE family_id = ?", (family_id,)).fetchall()]
                docs_db = [dict(r) for r in con.execute("SELECT * FROM family_documents WHERE family_id = ?", (family_id,)).fetchall()]
                fam_row = dict(con.execute("SELECT * FROM families WHERE id = ?", (family_id,)).fetchone())

                readiness = calculate_booking_readiness(fam_row, pils_db, docs_db)
                con.execute("""
                    UPDATE families SET
                        readiness_status = ?, readiness_score = ?, readiness_missing = ?
                    WHERE id = ?
                """, (readiness["status"], readiness["score"], json.dumps(readiness["missing_items"]), family_id))

            con.commit()

        # Record batch log
        error_summary_str = f"Valid: {analysis.get('valid_rows_count', 0)}, Invalid: {failed_count}"
        record_import_batch(
            batch_id=batch_id,
            file_name=file_name,
            file_size=file_size,
            file_format=file_format,
            admin_user=admin_user,
            total_rows=analysis.get("total_rows", 0),
            successful_records=successful_count,
            updated_records=updated_count,
            skipped_records=skipped_count,
            failed_records=failed_count,
            status="COMPLETED",
            error_summary=error_summary_str,
            mapping_config=column_mapping,
            db_path=db_path,
        )

        return {
            "status": "COMPLETED",
            "batch_id": batch_id,
            "file_name": file_name,
            "total_rows": analysis.get("total_rows", 0),
            "successful_records": successful_count,
            "updated_records": updated_count,
            "skipped_records": skipped_count,
            "failed_records": failed_count,
            "new_families": analysis.get("new_families_count", 0),
            "new_pilgrims": analysis.get("new_pilgrims_count", 0),
            "message": (
                f"Successfully completed batch '{batch_id}'. "
                f"Processed {successful_count} record(s), updated {updated_count}, "
                f"skipped {skipped_count}, rejected {failed_count} invalid row(s)."
            ),
        }

    except Exception as e:
        logger.error(f"Critical error during transactional import execution: {e}")
        # Record failed batch
        record_import_batch(
            batch_id=batch_id,
            file_name=file_name,
            file_size=file_size,
            file_format=file_format,
            admin_user=admin_user,
            total_rows=analysis.get("total_rows", 0),
            successful_records=0,
            updated_records=0,
            skipped_records=0,
            failed_records=analysis.get("total_rows", 0),
            status="FAILED",
            error_summary=str(e),
            mapping_config=column_mapping,
            db_path=db_path,
        )
        raise e


def export_validation_report_csv(validation_errors: List[Dict[str, Any]], out_path: str | Path) -> str:
    """Generate and write a structured validation error report to CSV."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Row Number", "Column Field", "Problematic Value", "Validation Error Description"])
        for err in validation_errors:
            writer.writerow([
                err.get("row", ""),
                err.get("column", ""),
                err.get("value", ""),
                err.get("error", ""),
            ])
    return str(p)
