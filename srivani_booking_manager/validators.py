"""
SRIVANI BOOKING MANAGER - Input Validators and Sanitizers
"""
import re
from datetime import datetime
from typing import Optional, Tuple
from config import GENDERS, ID_PROOF_TYPES

def clean_text(value: Optional[str]) -> str:
    """Strip whitespace and return clean string."""
    if value is None:
        return ""
    return str(value).strip()

def normalize_phone(phone: Optional[str]) -> Tuple[str, bool]:
    """
    Sanitize and check phone number.
    Returns (cleaned_phone, is_valid).
    Permits standard 10-digit Indian numbers, optional +91, and placeholder demo numbers.
    """
    raw = clean_text(phone)
    if not raw:
        return "", True
    
    # Strip spaces, hyphens, parentheses
    cleaned = re.sub(r"[\s\-\(\)]", "", raw)
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]

    # Check if 10 digits
    if re.fullmatch(r"[6-9]\d{9}", cleaned):
        return cleaned, True
    
    # Check if placeholder (like 9XXXXXXXXX)
    if re.fullmatch(r"[6-9][X0-9]{9}", cleaned, re.IGNORECASE):
        return cleaned.upper(), True
        
    return raw, False

def normalize_date(date_str: Optional[str]) -> Tuple[str, bool]:
    """
    Parse and normalize date string to YYYY-MM-DD.
    Supports formats: YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYY/MM/DD, and datetime objects.
    Returns (normalized_date_str, is_valid).
    """
    if date_str is None:
        return "", True
    raw = str(date_str).strip()
    if not raw:
        return "", True

    # If it's already an ISO timestamp like 2026-12-20T00:00:00
    if "T" in raw:
        raw = raw.split("T")[0]
    elif " " in raw:
        raw = raw.split(" ")[0]

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%Y.%m.%d",
        "%b %d, %Y",
        "%d %b %Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d"), True
        except ValueError:
            continue

    return raw, False

def validate_age(age_val) -> Tuple[Optional[int], bool]:
    """
    Validate age is an integer between 0 and 120.
    Returns (parsed_age, is_valid).
    """
    if age_val is None:
        return None, True
    raw = str(age_val).strip()
    if not raw:
        return None, True
    try:
        # Handle float values that might come from excel, e.g., 45.0
        val = int(float(raw))
        if 0 <= val <= 120:
            return val, True
        return None, False
    except (ValueError, TypeError):
        return None, False

def normalize_gender(gender_str: Optional[str]) -> str:
    """Normalize gender to standard Male/Female/Other."""
    raw = clean_text(gender_str).lower()
    if not raw:
        return ""
    if raw.startswith("m"):
        return "Male"
    elif raw.startswith("f"):
        return "Female"
    elif raw.startswith("t") or raw.startswith("o"):
        return "Other"
    return clean_text(gender_str)

def normalize_id_proof_type(proof_type: Optional[str]) -> str:
    """Normalize ID proof type against standard options."""
    raw = clean_text(proof_type).lower()
    if not raw:
        return "Aadhaar"
    if "aadhaar" in raw or "aadhar" in raw or "adhar" in raw:
        return "Aadhaar"
    if "passport" in raw:
        return "Passport"
    if "voter" in raw or "epic" in raw:
        return "Voter ID"
    if "dl" in raw or "driving" in raw or "licence" in raw or "license" in raw:
        return "Driving License"
    if "pan" in raw:
        return "PAN Card"
    for opt in ID_PROOF_TYPES:
        if opt.lower() in raw or raw in opt.lower():
            return opt
    return clean_text(proof_type)

def validate_id_proof_last4(last4: Optional[str]) -> Tuple[str, bool]:
    """
    Validate that ID proof last 4 is at most 4 alphanumeric digits.
    Must NOT be a full Aadhaar (12 digits) or sensitive credential.
    """
    raw = clean_text(last4)
    if not raw:
        return "", True
    
    # If user accidentally entered full 12 digits, extract last 4 to protect privacy
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 12:
        return digits[-4:], True

    cleaned = raw[-4:] if len(raw) > 4 else raw
    if re.fullmatch(r"[A-Za-z0-9]{1,4}", cleaned):
        return cleaned, True

    return cleaned, False

def validate_donation(amount) -> Tuple[float, bool]:
    """Validate donation amount is non-negative float."""
    if amount is None or str(amount).strip() == "":
        return 10000.0, True
    try:
        val = float(amount)
        if val >= 0:
            return val, True
        return 0.0, False
    except (ValueError, TypeError):
        return 0.0, False
