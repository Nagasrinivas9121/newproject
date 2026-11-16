"""
SRIVANI BOOKING MANAGER - Excel (.xlsx) & CSV Import/Export Engine
"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config import (
    SRIVANI_DONATION_PER_PERSON,
    BOOKING_TYPE_ADVANCE,
    STATUS_PENDING,
    PAYMENT_NOT_REQUESTED,
    PRIORITY_NORMAL,
)
from database import get_connection, add_family_with_pilgrims
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

HEADER_SYNONYMS = {
    "family_name": ["family_name", "family", "family name", "group_name", "group", "family title"],
    "family_code": ["family_code", "family_id", "family id", "code", "group_id"],
    "contact_name": ["contact_name", "contact", "contact person", "donor_name", "donor", "primary_contact"],
    "phone": ["phone", "mobile", "contact_number", "phone_number", "mobile_number", "cell"],
    "email": ["email", "email_id", "e-mail", "email_address"],
    "full_name": ["full_name", "pilgrim_name", "pilgrim", "name", "devotee_name", "devotee", "member_name"],
    "age": ["age"],
    "gender": ["gender", "sex"],
    "id_proof_type": ["id_proof_type", "id_proof", "id_type", "proof_type", "id_card", "id_proof_name"],
    "id_proof_last4": ["id_proof_last4", "id_last4", "last4", "id_number", "aadhaar_last4", "id_last_4", "last_4_digits"],
    "donation_amount": ["donation_amount", "donation", "amount", "srivani_donation", "total_donation"],
    "booking_type": ["booking_type", "booking", "type", "quota", "darshan_type"],
    "preferred_date": ["preferred_date", "date", "darshan_date", "booking_date", "travel_date"],
    "priority": ["priority", "queue_priority"],
    "notes": ["notes", "remarks", "comment", "instructions"],
}

def map_column_header(raw_header: str) -> Optional[str]:
    """Map user/Excel column header to canonical field name."""
    if not raw_header:
        return None
    cleaned = str(raw_header).strip().lower().replace("_", " ").replace("-", " ")
    for canonical, synonyms in HEADER_SYNONYMS.items():
        for syn in synonyms:
            if cleaned == syn.replace("_", " "):
                return canonical
    # Fallback to direct match
    cleaned_under = str(raw_header).strip().lower().replace(" ", "_")
    if cleaned_under in HEADER_SYNONYMS:
        return cleaned_under
    return None

def read_raw_records_from_csv(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Read rows from a CSV file."""
    rows = []
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            raw_headers = next(reader)
        except StopIteration:
            return [], []
        fieldnames = [str(h).strip() for h in raw_headers]
        for line_num, raw_row in enumerate(reader, start=2):
            if not any(str(cell).strip() for cell in raw_row):
                continue
            row_dict = {}
            for col_idx, header in enumerate(fieldnames):
                val = raw_row[col_idx] if col_idx < len(raw_row) else ""
                row_dict[header] = val
            row_dict["_line_number"] = line_num
            rows.append(row_dict)
    return fieldnames, rows

def read_raw_records_from_excel(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Read rows from an Excel (.xlsx/.xls) workbook."""
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb.active
    rows = []
    raw_headers = []
    
    first_row = True
    for line_num, row_cells in enumerate(ws.iter_rows(values_only=True), start=1):
        if first_row:
            raw_headers = [str(c).strip() if c is not None else "" for c in row_cells]
            first_row = False
            continue
        
        # Check if entire row is empty
        if not any(c is not None and str(c).strip() != "" for c in row_cells):
            continue
            
        row_dict = {}
        for col_idx, header in enumerate(raw_headers):
            if not header:
                continue
            val = row_cells[col_idx] if col_idx < len(row_cells) else ""
            if isinstance(val, datetime):
                val = val.strftime("%Y-%m-%d")
            row_dict[header] = val
        row_dict["_line_number"] = line_num
        rows.append(row_dict)
    wb.close()
    return raw_headers, rows

def analyze_import_file(path: str | Path, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Analyze CSV or Excel file for preview before committing to database.
    Performs full validation, detects duplicates in file and against database.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = p.suffix.lower()
    if ext in [".xlsx", ".xlsm", ".xltx"]:
        raw_headers, raw_rows = read_raw_records_from_excel(p)
    elif ext == ".csv":
        raw_headers, raw_rows = read_raw_records_from_csv(p)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Please provide a .xlsx or .csv file.")

    if not raw_headers or not raw_rows:
        return {
            "file_name": p.name,
            "summary": {
                "total_rows": 0,
                "valid_new": 0,
                "existing_family": 0,
                "duplicates": 0,
                "invalid": 0,
            },
            "rows": [],
            "errors": ["The file is empty or contains no data rows."],
            "families_map": {},
        }

    # Map headers to canonical names
    header_map = {}
    for h in raw_headers:
        canonical = map_column_header(h)
        if canonical:
            header_map[h] = canonical

    mapped_canonical_values = set(header_map.values())
    if "family_name" not in mapped_canonical_values or "full_name" not in mapped_canonical_values:
        raise ValueError(
            "Missing required columns! File must include at least 'Family Name' and 'Pilgrim Name' (or 'Full Name')."
        )

    analyzed_rows = []
    seen_in_batch = set()  # (family_key, devotee_name_lower)
    families_map: Dict[str, Dict[str, Any]] = {}

    valid_new_count = 0
    existing_family_count = 0
    duplicate_count = 0
    invalid_count = 0

    with get_connection(db_path) as con:
        # Pre-fetch existing families and devotees for fast lookup
        existing_families_db = con.execute("SELECT id, family_code, family_name, phone FROM families").fetchall()
        db_family_by_code = {f["family_code"].lower(): f for f in existing_families_db if f["family_code"]}
        db_family_by_phone = {f["phone"]: f for f in existing_families_db if f["phone"]}

        for raw in raw_rows:
            line_num = raw.get("_line_number", "?")
            row = {}
            for orig_k, orig_v in raw.items():
                if orig_k in header_map:
                    row[header_map[orig_k]] = orig_v

            family_name = clean_text(row.get("family_name"))
            full_name = clean_text(row.get("full_name"))
            phone_raw = row.get("phone")
            age_raw = row.get("age")
            date_raw = row.get("preferred_date")
            don_raw = row.get("donation_amount")

            row_errors = []
            if not family_name:
                row_errors.append("Family Name is required")
            if not full_name:
                row_errors.append("Devotee Name is required")

            age_val, is_age_valid = validate_age(age_raw)
            if not is_age_valid:
                row_errors.append(f"Invalid age '{age_raw}' (0-120)")

            phone, is_phone_valid = normalize_phone(phone_raw)
            if not is_phone_valid:
                row_errors.append(f"Invalid phone '{phone_raw}'")

            pref_date, is_date_valid = normalize_date(date_raw)
            if not is_date_valid:
                row_errors.append(f"Invalid date '{date_raw}'")

            donation, is_don_valid = validate_donation(don_raw)
            if not is_don_valid:
                row_errors.append("Invalid donation amount")

            gender = normalize_gender(row.get("gender"))
            id_type = normalize_id_proof_type(row.get("id_proof_type"))
            last4, _ = validate_id_proof_last4(row.get("id_proof_last4"))
            booking_type = clean_text(row.get("booking_type")) or BOOKING_TYPE_ADVANCE
            contact_name = clean_text(row.get("contact_name")) or family_name
            email = clean_text(row.get("email"))
            priority = clean_text(row.get("priority")) or PRIORITY_NORMAL
            notes = clean_text(row.get("notes"))
            explicit_code = clean_text(row.get("family_code"))

            # Determine grouping key
            if explicit_code:
                group_key = f"CODE:{explicit_code.upper()}"
            else:
                group_key = f"NAME:{family_name.lower()}#PHONE:{phone}"

            status = "VALID_NEW"
            status_desc = "New family & devotee"

            if row_errors:
                status = "INVALID"
                status_desc = "; ".join(row_errors)
                invalid_count += 1
            else:
                # Check duplicate within this import file
                batch_devotee_key = (group_key, full_name.lower())
                if batch_devotee_key in seen_in_batch:
                    status = "DUPLICATE_DEVOTEE"
                    status_desc = f"Duplicate devotee '{full_name}' repeated in file"
                    duplicate_count += 1
                else:
                    seen_in_batch.add(batch_devotee_key)

                    # Check against Database
                    matched_db_fam = None
                    if explicit_code and explicit_code.lower() in db_family_by_code:
                        matched_db_fam = db_family_by_code[explicit_code.lower()]
                    elif phone and phone in db_family_by_phone:
                        matched_db_fam = db_family_by_phone[phone]

                    if matched_db_fam:
                        # Family exists in DB, check if devotee exists in this family
                        fam_id = matched_db_fam["id"]
                        p_exists = con.execute(
                            "SELECT id FROM pilgrims WHERE family_id = ? AND lower(full_name) = lower(?)",
                            (fam_id, full_name),
                        ).fetchone()
                        if p_exists:
                            status = "DUPLICATE_DEVOTEE"
                            status_desc = f"Devotee already exists in DB ({matched_db_fam['family_code']})"
                            duplicate_count += 1
                        else:
                            status = "EXISTING_FAMILY"
                            status_desc = f"Will add to existing family ({matched_db_fam['family_code']})"
                            existing_family_count += 1
                    else:
                        status = "VALID_NEW"
                        valid_new_count += 1

            analyzed_row = {
                "line_number": line_num,
                "family_name": family_name,
                "family_code": explicit_code,
                "contact_name": contact_name,
                "phone": phone,
                "email": email,
                "full_name": full_name,
                "age": age_val,
                "gender": gender,
                "id_proof_type": id_type,
                "id_proof_last4": last4,
                "donation_amount": donation,
                "booking_type": booking_type,
                "preferred_date": pref_date,
                "priority": priority,
                "notes": notes,
                "status": status,
                "status_desc": status_desc,
                "group_key": group_key,
                "is_valid": len(row_errors) == 0,
            }
            analyzed_rows.append(analyzed_row)

            # Build family map for valid rows
            if status in ("VALID_NEW", "EXISTING_FAMILY"):
                if group_key not in families_map:
                    families_map[group_key] = {
                        "family_code": explicit_code,
                        "family_name": family_name,
                        "contact_name": contact_name,
                        "phone": phone,
                        "email": email,
                        "donation_amount": donation,
                        "booking_type": booking_type,
                        "preferred_date": pref_date,
                        "priority": priority,
                        "notes": notes,
                        "pilgrims": [],
                    }
                families_map[group_key]["pilgrims"].append({
                    "full_name": full_name,
                    "age": age_val,
                    "gender": gender,
                    "id_proof_type": id_type,
                    "id_proof_last4": last4,
                })

    return {
        "file_name": p.name,
        "summary": {
            "total_rows": len(raw_rows),
            "valid_new": valid_new_count,
            "existing_family": existing_family_count,
            "duplicates": duplicate_count,
            "invalid": invalid_count,
        },
        "rows": analyzed_rows,
        "errors": [r["status_desc"] for r in analyzed_rows if r["status"] == "INVALID"],
        "families_map": families_map,
    }

def commit_import_from_analysis(
    analysis: Dict[str, Any],
    skip_duplicates: bool = True,
    db_path: Optional[Path] = None,
) -> Tuple[int, List[str], int]:
    """
    Commit pre-analyzed import data to the SQLite database.
    """
    families_map = analysis.get("families_map", {})
    if not families_map:
        return 0, ["No valid records to import."], 0

    imported_pilgrims = 0
    skipped_messages = []
    families_created_or_updated = 0

    with get_connection(db_path) as con:
        for group_key, f_data in families_map.items():
            code = f_data["family_code"]
            existing = None
            if code:
                existing = con.execute("SELECT id, family_code FROM families WHERE lower(family_code) = lower(?)", (code,)).fetchone()
            if not existing and f_data["phone"]:
                existing = con.execute("SELECT id, family_code FROM families WHERE phone = ?", (f_data["phone"],)).fetchone()

            if existing:
                family_id = existing["id"]
            else:
                assigned_code = code or f"FAM-{datetime.now():%y%m%d}-{len(families_map)+1:03d}"
                cur = con.execute("""
                    INSERT INTO families (
                        family_code, family_name, contact_name, phone, email,
                        donation_amount, booking_type, preferred_date, status, payment_status,
                        priority, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    assigned_code,
                    f_data["family_name"],
                    f_data["contact_name"],
                    f_data["phone"],
                    f_data["email"],
                    f_data["donation_amount"],
                    f_data["booking_type"],
                    f_data["preferred_date"],
                    STATUS_PENDING,
                    PAYMENT_NOT_REQUESTED,
                    f_data["priority"],
                    f_data["notes"],
                    datetime.now().isoformat(timespec="seconds"),
                ))
                family_id = cur.lastrowid
                families_created_or_updated += 1

            # Insert pilgrims
            for p in f_data["pilgrims"]:
                p_exists = con.execute(
                    "SELECT id FROM pilgrims WHERE family_id = ? AND lower(full_name) = lower(?)",
                    (family_id, p["full_name"]),
                ).fetchone()
                if p_exists:
                    if skip_duplicates:
                        skipped_messages.append(f"Skipped duplicate devotee '{p['full_name']}' in family '{f_data['family_name']}'")
                        continue
                con.execute("""
                    INSERT INTO pilgrims (family_id, full_name, age, gender, id_proof_type, id_proof_last4)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    family_id,
                    p["full_name"],
                    p["age"],
                    p["gender"],
                    p["id_proof_type"],
                    p["id_proof_last4"],
                ))
                imported_pilgrims += 1

        con.commit()

    return imported_pilgrims, skipped_messages, len(families_map)
    """Read rows from an Excel (.xlsx/.xls) workbook."""
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb.active
    rows = []
    raw_headers = []
    
    first_row = True
    for line_num, row_cells in enumerate(ws.iter_rows(values_only=True), start=1):
        if first_row:
            raw_headers = [str(c).strip() if c is not None else "" for c in row_cells]
            first_row = False
            continue
        
        # Check if entire row is empty
        if not any(c is not None and str(c).strip() != "" for c in row_cells):
            continue
            
        row_dict = {}
        for col_idx, header in enumerate(raw_headers):
            if not header:
                continue
            val = row_cells[col_idx] if col_idx < len(row_cells) else ""
            # Convert datetime objects to string if openpyxl parsed them
            if isinstance(val, datetime):
                val = val.strftime("%Y-%m-%d")
            row_dict[header] = val
        row_dict["_line_number"] = line_num
        rows.append(row_dict)
    wb.close()
    return raw_headers, rows

def import_records(path: str | Path, db_path: Optional[Path] = None) -> Tuple[int, List[str], int]:
    """
    Import families and pilgrims from CSV or Excel (.xlsx).
    Returns (imported_pilgrim_count, skipped_lines_list, families_count).
    """
    analysis = analyze_import_file(path, db_path=db_path)
    skipped_messages = [r["status_desc"] for r in analysis["rows"] if r["status"] in ("INVALID", "DUPLICATE_DEVOTEE")]
    imported_pilgrims, commit_skipped, families_count = commit_import_from_analysis(analysis, skip_duplicates=True, db_path=db_path)
    all_skipped = skipped_messages + commit_skipped
    return imported_pilgrims, all_skipped, families_count

def export_to_csv(dest_path: str | Path, db_path: Optional[Path] = None) -> int:
    """Export all families and pilgrims to CSV."""
    with get_connection(db_path) as con:
        rows = con.execute("""
            SELECT
                f.family_code, f.family_name, f.contact_name, f.phone, f.email,
                f.donation_amount, f.booking_type, f.preferred_date, f.status,
                f.payment_status, f.priority, f.ticket_number, f.notes,
                p.full_name, p.age, p.gender, p.id_proof_type, p.id_proof_last4
            FROM families f
            LEFT JOIN pilgrims p ON p.family_id = f.id
            ORDER BY f.id ASC, p.id ASC
        """).fetchall()

    headers = [
        "family_code", "family_name", "contact_name", "phone", "email",
        "donation_amount", "booking_type", "preferred_date", "status",
        "payment_status", "priority", "ticket_number", "notes",
        "full_name", "age", "gender", "id_proof_type", "id_proof_last4"
    ]

    with open(dest_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(dict(r))

    return len(rows)

def export_to_excel(dest_path: str | Path, db_path: Optional[Path] = None) -> int:
    """Export all families and pilgrims to styled Excel workbook."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Srivani Families & Pilgrims"

    headers = [
        "Family ID", "Family Name", "Contact Person", "Phone", "Email",
        "Donation (₹)", "Booking Type", "Preferred Date", "Booking Status",
        "Payment Status", "Priority", "Ticket No.", "Notes",
        "Pilgrim Name", "Age", "Gender", "ID Proof Type", "ID Proof Last 4"
    ]

    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    with get_connection(db_path) as con:
        rows = con.execute("""
            SELECT
                f.family_code, f.family_name, f.contact_name, f.phone, f.email,
                f.donation_amount, f.booking_type, f.preferred_date, f.status,
                f.payment_status, f.priority, f.ticket_number, f.notes,
                p.full_name, p.age, p.gender, p.id_proof_type, p.id_proof_last4
            FROM families f
            LEFT JOIN pilgrims p ON p.family_id = f.id
            ORDER BY f.id ASC, p.id ASC
        """).fetchall()

    row_font = Font(name="Segoe UI", size=10)
    thin_border = Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD'),
    )

    for row_idx, r in enumerate(rows, start=2):
        row_values = [
            r["family_code"], r["family_name"], r["contact_name"], r["phone"], r["email"],
            r["donation_amount"], r["booking_type"], r["preferred_date"], r["status"],
            r["payment_status"], r["priority"], r["ticket_number"], r["notes"],
            r["full_name"], r["age"], r["gender"], r["id_proof_type"], r["id_proof_last4"]
        ]
        ws.append(row_values)
        for col_idx in range(1, len(row_values) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = row_font
            cell.border = thin_border

    # Auto adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(str(dest_path))
    wb.close()
    return len(rows)

import tkinter as tk
from tkinter import ttk, messagebox

class ImportPreviewDialog(tk.Toplevel):
    """
    Visual preview modal for Excel and CSV imports.
    Displays summary counts, rows with validation & duplicate status,
    and enables the admin to confirm or cancel the import.
    """

    def __init__(self, parent, file_path: str | Path, on_success_callback: Callable[[], None], db_path: Optional[Path] = None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.on_success = on_success_callback
        self.db_path = db_path

        self.title(f"Import Preview — {self.file_path.name}")
        self.geometry("960x640")
        self.minsize(840, 540)
        self.transient(parent)
        self.grab_set()

        self.analysis: Optional[Dict[str, Any]] = None
        self._build_ui()
        self._load_and_analyze()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Header
        hdr = ttk.Frame(container)
        hdr.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr, text="Import File Preview & Duplicate Analysis", font=("Segoe UI", 13, "bold"), foreground="#1B365D").pack(anchor="w")
        self.lbl_file_info = ttk.Label(hdr, text=f"File: {self.file_path.name}", font=("Segoe UI", 9), foreground="#64748B")
        self.lbl_file_info.pack(anchor="w")

        # Summary Badges Frame
        self.badges_frame = ttk.Frame(container)
        self.badges_frame.pack(fill="x", pady=(0, 12))

        # We will populate badges dynamically
        self.badge_labels = {}
        for key, title, color in [
            ("total", "Total Rows", "#1B365D"),
            ("valid_new", "Valid New Devotees", "#059669"),
            ("existing_family", "Existing Families", "#0284C7"),
            ("duplicates", "Duplicates", "#D97706"),
            ("invalid", "Invalid / Errors", "#DC2626"),
        ]:
            card = tk.Frame(self.badges_frame, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1, padx=10, pady=5)
            card.pack(side="left", expand=True, fill="x", padx=4)
            ttk.Label(card, text=title, font=("Segoe UI", 8, "bold"), foreground="#64748B", background="#FFFFFF").pack(anchor="w")
            lbl_val = ttk.Label(card, text="0", font=("Segoe UI", 12, "bold"), foreground=color, background="#FFFFFF")
            lbl_val.pack(anchor="w")
            self.badge_labels[key] = lbl_val

        # Preview Table
        table_frame = ttk.Frame(container)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("line", "status", "family", "devotee", "phone", "age_gender", "date", "notes")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        headings = {
            "line": "Row #",
            "status": "Import Status",
            "family": "Family Name",
            "devotee": "Devotee Name",
            "phone": "Phone",
            "age_gender": "Age / Gender",
            "date": "Preferred Date",
            "notes": "Validation & Details",
        }
        widths = {
            "line": 50,
            "status": 120,
            "family": 140,
            "devotee": 140,
            "phone": 100,
            "age_gender": 95,
            "date": 95,
            "notes": 200,
        }

        for c in cols:
            self.tree.heading(c, text=headings[c])
            align = "center" if c in ("line", "status", "age_gender", "date") else "w"
            self.tree.column(c, width=widths[c], anchor=align)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Tag colors
        self.tree.tag_configure("tag_new", background="#ECFDF5", foreground="#065F46")
        self.tree.tag_configure("tag_existing", background="#F0F9FF", foreground="#0369A1")
        self.tree.tag_configure("tag_dup", background="#FFFBEB", foreground="#92400E")
        self.tree.tag_configure("tag_invalid", background="#FEF2F2", foreground="#991B1B")

        # Bottom Bar: Options and Action buttons
        bottom_bar = ttk.Frame(container)
        bottom_bar.pack(fill="x", pady=(4, 0))

        self.var_skip_duplicates = tk.BooleanVar(value=True)
        chk_dup = ttk.Checkbutton(bottom_bar, text="Automatically skip duplicate devotees", variable=self.var_skip_duplicates)
        chk_dup.pack(side="left")

        self.btn_cancel = ttk.Button(bottom_bar, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_confirm = ttk.Button(bottom_bar, text="Confirm & Import Records", command=self._confirm_import)
        self.btn_confirm.pack(side="right")

    def _load_and_analyze(self):
        try:
            self.analysis = analyze_import_file(self.file_path, db_path=self.db_path)
        except Exception as e:
            messagebox.showerror("Analysis Failed", f"Could not analyze file:\n{e}", parent=self)
            self.destroy()
            return

        summary = self.analysis["summary"]
        self.badge_labels["total"].config(text=str(summary["total_rows"]))
        self.badge_labels["valid_new"].config(text=str(summary["valid_new"]))
        self.badge_labels["existing_family"].config(text=str(summary["existing_family"]))
        self.badge_labels["duplicates"].config(text=str(summary["duplicates"]))
        self.badge_labels["invalid"].config(text=str(summary["invalid"]))

        # Populate rows
        for r in self.analysis["rows"]:
            st = r["status"]
            tag = "tag_new"
            st_text = "🟢 New Devotee"
            if st == "EXISTING_FAMILY":
                tag = "tag_existing"
                st_text = "🔵 Family Exists"
            elif st == "DUPLICATE_DEVOTEE":
                tag = "tag_dup"
                st_text = "🟡 Duplicate"
            elif st == "INVALID":
                tag = "tag_invalid"
                st_text = "🔴 Error / Invalid"

            age_gender = f"{r['age'] or '-'} / {r['gender'] or '-'}"

            self.tree.insert(
                "",
                "end",
                values=(
                    r["line_number"],
                    st_text,
                    r["family_name"],
                    r["full_name"],
                    r["phone"] or "—",
                    age_gender,
                    r["preferred_date"] or "—",
                    r["status_desc"],
                ),
                tags=(tag,),
            )

        # Enable/Disable confirm button
        valid_importable = summary["valid_new"] + summary["existing_family"]
        if valid_importable == 0:
            self.btn_confirm.config(state="disabled", text="No Valid Records to Import")
        else:
            self.btn_confirm.config(state="normal", text=f"Confirm & Import ({valid_importable} Devotees)")

    def _confirm_import(self):
        if not self.analysis:
            return
        skip_dup = self.var_skip_duplicates.get()
        try:
            imported, skipped, fam_count = commit_import_from_analysis(self.analysis, skip_duplicates=skip_dup, db_path=self.db_path)
            self.on_success()
            self.destroy()
            msg = f"Import Successful!\n\n• Successfully Imported Devotees: {imported}\n• Families Created or Updated: {fam_count}"
            if skipped:
                msg += f"\n\nSkipped Devotees ({len(skipped)}):\n" + "\n".join(skipped[:10])
            messagebox.showinfo("Import Complete", msg)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to commit import records:\n{e}", parent=self)

def create_sample_excel_template(dest_path: str | Path):
    """Generate a ready-to-use sample Excel template with sample families."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Srivani Import Template"

    headers = [
        "family_code", "family_name", "contact_name", "phone", "email",
        "donation_amount", "booking_type", "preferred_date",
        "full_name", "age", "gender", "id_proof_type", "id_proof_last4"
    ]

    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0D5C75", end_color="0D5C75", fill_type="solid")

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill

    sample_data = [
        # Family 1 (2 pilgrims)
        ("FAM-001", "Reddy Family", "Ramesh Reddy", "9848022338", "ramesh.reddy@example.com", 20000, "Advance", "2026-12-25", "Ramesh Reddy", 46, "Male", "Aadhaar", "1234"),
        ("FAM-001", "Reddy Family", "Ramesh Reddy", "9848022338", "ramesh.reddy@example.com", 20000, "Advance", "2026-12-25", "Sita Devi Reddy", 42, "Female", "Aadhaar", "5678"),
        # Family 2 (1 pilgrim)
        ("FAM-002", "Sharma Family", "Venkatesh Sharma", "9440112233", "v.sharma@example.com", 10000, "Current", "2026-11-20", "Venkatesh Sharma", 52, "Male", "Passport", "9012"),
        # Family 3 (3 pilgrims)
        ("FAM-003", "Verma Family", "Rajesh Verma", "9876543210", "r.verma@example.com", 30000, "Advance", "2026-12-30", "Rajesh Verma", 48, "Male", "Aadhaar", "4321"),
        ("FAM-003", "Verma Family", "Rajesh Verma", "9876543210", "r.verma@example.com", 30000, "Advance", "2026-12-30", "Sunita Verma", 45, "Female", "Aadhaar", "8765"),
        ("FAM-003", "Verma Family", "Rajesh Verma", "9876543210", "r.verma@example.com", 30000, "Advance", "2026-12-30", "Aarav Verma", 18, "Male", "Aadhaar", "6543"),
    ]

    for row in sample_data:
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

    wb.save(str(dest_path))
    wb.close()
