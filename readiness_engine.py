"""
SRIVANI BOOKING MANAGER - PHASE 9
Fast Booking Preparation Engine & Readiness Evaluation System

Strictly enforces compliance:
- Prepares and validates information in local application only.
- Does NOT automate TTD portal interactions.
- Validates 6 standardized readiness statuses and 5 payment tracking statuses.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from validators import (
    clean_text,
    normalize_date,
    normalize_gender,
    normalize_id_proof_type,
    normalize_phone,
    validate_age,
    validate_donation,
    validate_id_proof_last4,
)

# Standardized Phase 9 Booking Readiness & Lifecycle Statuses
STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_READY_FOR_MANUAL_BOOKING = "READY_FOR_MANUAL_BOOKING"
STATUS_BOOKING_IN_PROGRESS = "BOOKING_IN_PROGRESS"
STATUS_BOOKED = "BOOKED"
STATUS_CANCELLED = "CANCELLED"

ALL_BOOKING_STATUSES = [
    STATUS_NOT_STARTED,
    STATUS_INCOMPLETE,
    STATUS_READY_FOR_MANUAL_BOOKING,
    STATUS_BOOKING_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_CANCELLED,
]

# Standardized Phase 9 Payment Tracking Statuses (Tracking only - no credentials)
PAYMENT_NOT_PAID = "NOT_PAID"
PAYMENT_PENDING = "PAYMENT_PENDING"
PAYMENT_PAID = "PAID"
PAYMENT_FAILED = "FAILED"
PAYMENT_REFUNDED = "REFUNDED"

ALL_PAYMENT_STATUSES = [
    PAYMENT_NOT_PAID,
    PAYMENT_PENDING,
    PAYMENT_PAID,
    PAYMENT_FAILED,
    PAYMENT_REFUNDED,
]

# Map legacy status strings for 100% backward compatibility
LEGACY_STATUS_MAP = {
    "pending": STATUS_NOT_STARTED,
    "in progress": STATUS_BOOKING_IN_PROGRESS,
    "in_progress": STATUS_BOOKING_IN_PROGRESS,
    "booked": STATUS_BOOKED,
    "unavailable": STATUS_INCOMPLETE,
    "cancelled": STATUS_CANCELLED,
    "ready": STATUS_READY_FOR_MANUAL_BOOKING,
}

LEGACY_PAYMENT_MAP = {
    "not requested": PAYMENT_NOT_PAID,
    "request sent": PAYMENT_PENDING,
    "pending": PAYMENT_PENDING,
    "paid": PAYMENT_PAID,
    "failed": PAYMENT_FAILED,
    "refunded": PAYMENT_REFUNDED,
}


def normalize_booking_status(status_str: Optional[str]) -> str:
    """Normalize any status string to Phase 9 standardized status."""
    if not status_str:
        return STATUS_NOT_STARTED
    raw = str(status_str).strip()
    if raw in ALL_BOOKING_STATUSES:
        return raw
    return LEGACY_STATUS_MAP.get(raw.lower(), STATUS_NOT_STARTED)


def normalize_payment_tracking_status(status_str: Optional[str]) -> str:
    """Normalize any payment string to Phase 9 standardized tracking status."""
    if not status_str:
        return PAYMENT_NOT_PAID
    raw = str(status_str).strip()
    if raw in ALL_PAYMENT_STATUSES:
        return raw
    return LEGACY_PAYMENT_MAP.get(raw.lower(), PAYMENT_NOT_PAID)


def validate_family_fields(family: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate mandatory family-level profile fields."""
    errors = []
    name = clean_text(family.get("family_name") or family.get("head_name"))
    if not name or len(name) < 2:
        errors.append("Family / Primary Devotee name is required (at least 2 characters).")

    phone = clean_text(family.get("phone") or family.get("contact_number"))
    if not phone:
        errors.append("Primary contact phone number is required.")
    else:
        cleaned_phone, is_valid_phone = normalize_phone(phone)
        if not is_valid_phone:
            errors.append(f"Phone number '{phone}' is invalid (must be a valid 10-digit mobile number).")

    email = clean_text(family.get("email"))
    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors.append(f"Email address '{email}' is invalid.")

    pref_date = clean_text(family.get("preferred_date"))
    if pref_date:
        _, is_valid_date = normalize_date(pref_date)
        if not is_valid_date:
            errors.append(f"Preferred date '{pref_date}' is not a recognized date format.")

    return len(errors) == 0, errors


def validate_pilgrim_fields(pilgrim: Dict[str, Any], index: int = 1) -> Tuple[bool, List[str]]:
    """Validate individual pilgrim record fields."""
    errors = []
    p_name = clean_text(pilgrim.get("full_name") or pilgrim.get("name"))
    label = f"Pilgrim #{index} ({p_name or 'Unnamed'})"

    if not p_name or len(p_name) < 2:
        errors.append(f"{label}: Devotee full name is required.")

    age = pilgrim.get("age")
    val_age, is_valid_age = validate_age(age)
    if val_age is None or not is_valid_age or val_age <= 0:
        errors.append(f"{label}: Valid age between 1 and 120 is required.")

    gender = normalize_gender(pilgrim.get("gender"))
    if not gender or gender not in ("Male", "Female", "Other"):
        errors.append(f"{label}: Valid gender (Male, Female, Other) is required.")

    proof_type = normalize_id_proof_type(pilgrim.get("id_proof_type") or pilgrim.get("id_type"))
    if not proof_type:
        errors.append(f"{label}: ID proof type (e.g., Aadhaar, Passport, Voter ID) is required.")

    last4 = clean_text(pilgrim.get("id_proof_last4") or pilgrim.get("id_number"))
    val_last4, is_valid_last4 = validate_id_proof_last4(last4)
    if not val_last4 or not is_valid_last4 or len(val_last4) < 4:
        errors.append(f"{label}: Last 4 characters of ID proof are required for verification.")

    return len(errors) == 0, errors


def detect_pilgrim_duplicates(pilgrims: List[Dict[str, Any]]) -> List[str]:
    """Detect duplicate pilgrim records within the same family roster."""
    issues = []
    seen_ids = set()
    seen_names = set()

    for idx, p in enumerate(pilgrims, start=1):
        name = clean_text(p.get("full_name") or p.get("name")).lower()
        last4 = clean_text(p.get("id_proof_last4") or p.get("id_number"))
        proof_type = clean_text(p.get("id_proof_type") or p.get("id_type")).lower()

        if name:
            if name in seen_names:
                issues.append(f"Duplicate pilgrim name '{p.get('full_name')}' found in roster.")
            seen_names.add(name)

        if last4 and proof_type:
            id_key = f"{proof_type}:{last4}"
            if id_key in seen_ids:
                issues.append(f"Duplicate ID proof ({proof_type.upper()} ending in {last4}) detected on multiple pilgrims.")
            seen_ids.add(id_key)

    return issues


def calculate_booking_readiness(
    family: Dict[str, Any],
    pilgrims: List[Dict[str, Any]],
    documents: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Core Booking Readiness Engine.
    
    Evaluates:
    1. Family details completeness.
    2. Pilgrim roster count (1 <= count <= 6).
    3. Complete profile for every pilgrim.
    4. Required documents recorded or attached.
    5. Local donation amount preference configured (> 0).
    6. Zero critical validation errors or duplicate records.
    
    Returns structured evaluation with exact missing items and score percentage.
    """
    missing_items = []
    completed_items = []
    validation_errors = []

    current_status = normalize_booking_status(family.get("status"))

    # If already Booked or Cancelled, preserve terminal state
    if current_status in (STATUS_BOOKED, STATUS_CANCELLED):
        return {
            "status": current_status,
            "is_ready": (current_status == STATUS_BOOKED),
            "score": 100 if current_status == STATUS_BOOKED else 0,
            "missing_items": [],
            "completed_items": ["Booking finalized" if current_status == STATUS_BOOKED else "Booking cancelled"],
            "validation_errors": [],
            "checklist": {
                "family_details": True,
                "pilgrim_count": len(pilgrims) > 0,
                "pilgrim_profiles": True,
                "donation_preference": True,
                "document_checklist": True,
            },
        }

    # 1. Family Details Check
    fam_valid, fam_errors = validate_family_fields(family)
    if fam_valid:
        completed_items.append("Primary contact and family profile complete")
    else:
        missing_items.append("Complete required family profile fields")
        validation_errors.extend(fam_errors)

    # 2. Pilgrim Count Check
    pilgrim_count = len(pilgrims)
    if pilgrim_count == 0:
        missing_items.append("Add at least 1 pilgrim to the family roster")
    elif pilgrim_count > 6:
        missing_items.append(f"Pilgrim roster exceeds standard TTD booking transaction limit of 6 ({pilgrim_count} pilgrims present)")
    else:
        completed_items.append(f"Pilgrim roster verified ({pilgrim_count} pilgrim(s))")

    # 3. Individual Pilgrim Profiles Check
    all_pilgrims_valid = True
    if pilgrim_count > 0:
        for idx, p in enumerate(pilgrims, start=1):
            p_valid, p_errors = validate_pilgrim_fields(p, idx)
            if not p_valid:
                all_pilgrims_valid = False
                validation_errors.extend(p_errors)

        if all_pilgrims_valid:
            completed_items.append("All pilgrim profiles verified (Name, Age, Gender, ID Proof)")
        else:
            missing_items.append("Complete all required pilgrim profile details")

        # Duplicate check within family
        dup_issues = detect_pilgrim_duplicates(pilgrims)
        if dup_issues:
            validation_errors.extend(dup_issues)
            missing_items.append("Resolve duplicate pilgrim entries in roster")

    # 4. Donation Amount Preference Check (Local preparation only)
    donation_val, is_valid_donation = validate_donation(family.get("donation_amount"))
    if is_valid_donation and donation_val > 0:
        completed_items.append(f"Donation preference recorded locally (₹{donation_val:,.0f})")
    else:
        missing_items.append("Configure donation amount preference in local application")

    # 5. Document Checklist Check
    has_docs = False
    # Check if pilgrims have id_proofs or if supporting documents / tickets exist
    ticket_path = family.get("ticket_pdf_path")
    doc_count = len(documents) if documents else 0
    if (doc_count > 0) or (ticket_path and str(ticket_path).strip()) or (all_pilgrims_valid and pilgrim_count > 0):
        has_docs = True
        completed_items.append("Identity proofs and supporting documentation recorded")
    else:
        missing_items.append("Record identity document proofs for all pilgrims")

    # Calculate overall readiness percentage score
    total_checks = 5
    passed_checks = sum([
        fam_valid,
        (1 <= pilgrim_count <= 6),
        (pilgrim_count > 0 and all_pilgrims_valid),
        (is_valid_donation and donation_val > 0),
        has_docs,
    ])
    score = int((passed_checks / total_checks) * 100)

    # Determine final Readiness Status
    if passed_checks == total_checks and len(validation_errors) == 0:
        if current_status == STATUS_BOOKING_IN_PROGRESS:
            readiness_status = STATUS_BOOKING_IN_PROGRESS
        else:
            readiness_status = STATUS_READY_FOR_MANUAL_BOOKING
        is_ready = True
    else:
        if passed_checks == 0:
            readiness_status = STATUS_NOT_STARTED
        else:
            readiness_status = STATUS_INCOMPLETE
        is_ready = False

    return {
        "status": readiness_status,
        "is_ready": is_ready,
        "score": score,
        "missing_items": missing_items,
        "completed_items": completed_items,
        "validation_errors": validation_errors,
        "checklist": {
            "family_details": fam_valid,
            "pilgrim_count": (1 <= pilgrim_count <= 6),
            "pilgrim_profiles": (pilgrim_count > 0 and all_pilgrims_valid),
            "donation_preference": (is_valid_donation and donation_val > 0),
            "document_checklist": has_docs,
        },
    }
