"""
SRIVANI BOOKING MANAGER - Configuration and Constants
"""
import os
import sys
from pathlib import Path

# Application Directory
APP_DIR = Path(__file__).resolve().parent

# When frozen (packaged as Windows executable), keep user data outside the installation directory
# in the standard user AppData directory (%LOCALAPPDATA%\SrivaniBookingManager)
if getattr(sys, "frozen", False):
    local_app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if local_app_data:
        DATA_DIR = Path(local_app_data) / "SrivaniBookingManager"
    else:
        DATA_DIR = APP_DIR / "data"
else:
    DATA_DIR = APP_DIR / "data"

TICKETS_DIR = DATA_DIR / "tickets"
BACKUPS_DIR = DATA_DIR / "backups"
DB_PATH = DATA_DIR / "srivani_manager.db"

# Ensure essential directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
TICKETS_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

# Booking Statuses
STATUS_PENDING = "Pending"
STATUS_IN_PROGRESS = "In progress"
STATUS_BOOKED = "Booked"
STATUS_UNAVAILABLE = "Unavailable"
STATUS_CANCELLED = "Cancelled"
BOOKING_STATUSES = [
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_UNAVAILABLE,
    STATUS_CANCELLED,
]

# Payment Statuses
PAYMENT_NOT_REQUESTED = "Not requested"
PAYMENT_REQUEST_SENT = "Request sent"
PAYMENT_PAID = "Paid"
PAYMENT_FAILED = "Failed"
PAYMENT_REFUNDED = "Refunded"
PAYMENT_STATUSES = [
    PAYMENT_NOT_REQUESTED,
    PAYMENT_REQUEST_SENT,
    PAYMENT_PAID,
    PAYMENT_FAILED,
    PAYMENT_REFUNDED,
]

# Queue Priorities
PRIORITY_URGENT = "Urgent"
PRIORITY_HIGH = "High"
PRIORITY_NORMAL = "Normal"
PRIORITY_LOW = "Low"
PRIORITIES = [
    PRIORITY_URGENT,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
    PRIORITY_LOW,
]

PRIORITY_WEIGHTS = {
    PRIORITY_URGENT: 0,
    PRIORITY_HIGH: 1,
    PRIORITY_NORMAL: 2,
    PRIORITY_LOW: 3,
}

# Booking Types
BOOKING_TYPE_ADVANCE = "Advance"
BOOKING_TYPE_CURRENT = "Current"
BOOKING_TYPES = [
    BOOKING_TYPE_ADVANCE,
    BOOKING_TYPE_CURRENT,
]

# Standard ID Proof Types
ID_PROOF_AADHAAR = "Aadhaar"
ID_PROOF_VOTER = "Voter ID"
ID_PROOF_PASSPORT = "Passport"
ID_PROOF_DRIVING = "Driving License"
ID_PROOF_PAN = "PAN Card"
ID_PROOF_OTHER = "Other"
ID_PROOF_TYPES = [
    ID_PROOF_AADHAAR,
    ID_PROOF_VOTER,
    ID_PROOF_PASSPORT,
    ID_PROOF_DRIVING,
    ID_PROOF_PAN,
    ID_PROOF_OTHER,
]

# Gender options
GENDERS = ["Male", "Female", "Other"]

# Srivani financial guidelines
SRIVANI_DONATION_PER_PERSON = 10000.0  # ₹10,000 per person standard donation
SRIVANI_DARSHAN_FEE_PER_PERSON = 500.0  # ₹500 VIP break darshan ticket fee

# Official TTD Portal URL (User/Client controlled)
TTD_PORTAL_URL = "https://ttdevasthanams.ap.gov.in"
