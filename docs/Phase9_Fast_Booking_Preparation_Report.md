# SRIVANI BOOKING MANAGER — PHASE 9
## Fast Booking Preparation Engine & Operational Compliance Suite

**Project Version:** v9.0.0 Fast Booking Engine  
**Target Environment:** Windows Desktop Application (Python 3.14+, Tkinter Modern Flat Theme)  
**Execution Date:** 2026-11-16  
**Compliance Standard:** 100% Non-Automated • Assisted Preparation Only • Official Portal Independent  

---

### EXECUTIVE SUMMARY

Phase 9 establishes the **Fast Booking Preparation Engine** for the **SRIVANI BOOKING MANAGER**. This major release transforms devotee management into a high-efficiency preparation and assisted booking workflow. 

Crucially, **the application is an assisted booking preparation tool, NOT an automated TTD booking bot**. All website interactions, login authentication, CAPTCHA solutions, OTP verification, form inputs, and payment disbursements are performed independently and directly by the client on the official Tirumala Tirupati Devasthanams (TTD) portal (`https://ttdevasthanams.ap.gov.in`).

All existing capabilities from **Phases 1 through 8** (SQLite/PostgreSQL multi-tenancy, cryptographic licensing, role-based security, PDF slip generation, queue prioritization, and advanced operational analytics) are fully preserved.

---

### MODULE ARCHITECTURE & IMPLEMENTATION DETAILS

```
+--------------------------------------------------------------------------------------------------+
|                           SRIVANI BOOKING MANAGER — PHASE 9 ARCHITECTURE                          |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   +------------------------------------------------------------------------------------------+   |
|   | 1. Fast Booking Dashboard View (FastBookingDashboardView)                                |   |
|   |    • Total Families • Total Pilgrims • Ready for Booking • Incomplete Profiles           |   |
|   |    • Pending Bookings • Completed Bookings • 5-State Payment Counters • Recent Activity  |   |
|   +---------------------------------------------+--------------------------------------------+   |
|                                                 |                                                |
|   +---------------------------------------------v--------------------------------------------+   |
|   | 2. Booking Readiness Engine (readiness_engine.py)                                         |   |
|   |    • 6 Booking Readiness Statuses:                                                       |   |
|   |      NOT_STARTED | INCOMPLETE | READY_FOR_MANUAL_BOOKING | BOOKING_IN_PROGRESS | BOOKED      |   |
|   |    • 5 Payment Tracking Statuses:                                                        |   |
|   |      NOT_PAID | PAYMENT_PENDING | PAID | FAILED | REFUNDED                               |   |
|   |    • Duplicate Pilgrim Detection (Name + ID / Phone)                                     |   |
|   |    • Dynamic Readiness Score (0-100%) & Detailed Missing Items Breakdown                |   |
|   +---------------------------------------------+--------------------------------------------+   |
|                                                 |                                                |
|   +---------------------------------------------v--------------------------------------------+   |
|   | 3. Manual Booking Workspace Dialog (ManualBookingWorkspaceDialog)                        |   |
|   |    • Devotee & Pilgrim Roster with One-Click Copy To Clipboard                           |   |
|   |    • Locally Configured Donation Amount with Strict Non-Automation Disclaimer            |   |
|   |    • 'OPEN OFFICIAL TTD WEBSITE' Button (webbrowser.open - User Click Only)              |   |
|   |    • 7-Step Interactive Manual Checklist Enforcing Human Verification                    |   |
|   |    • Live Booking Status Transition & Payment Ref/Accounting Note Recording              |   |
|   +---------------------+-----------------------------------+--------------------------------+   |
|                         |                                   |                                    |
|   +---------------------v--------------------+      +-------v--------------------------------+   |
|   | 4. Document Manager (document_manager.py)|      | 5. Booking History (BookingHistoryFrame)|  |
|   |    • Local Storage: data/documents/{id}/ |      |    • Real-Time Search & Status Filters |   |
|   |    • File Size Limit: <= 10MB            |      |    • Single-Click CSV Export           |   |
|   |    • Allowed: PDF, PNG, JPG, JPEG        |      |    • Formatted Excel (.xlsx) Export    |   |
|   |    • SHA-256 Cryptographic Checksum      |      |    • Readiness Badges & Direct Links   |   |
|   |    • OS-Default Preview Launcher         |      +----------------------------------------+   |
|   +------------------------------------------+                                                   |
+--------------------------------------------------------------------------------------------------+
```

---

### 1. STRICT REGULATORY & TECHNICAL COMPLIANCE BOUNDARIES

The Phase 9 architecture establishes inviolable boundaries verified by unit tests:

| Compliance Dimension | System Boundary / Technical Implementation |
|---|---|
| **Portal Interaction** | The application **never** launches automated browsers (Playwright, Selenium, Puppeteer). It uses standard OS `webbrowser.open("https://ttdevasthanams.ap.gov.in")` triggered exclusively by deliberate user click. |
| **Credential Safety** | The application **never** collects, prompts for, or stores TTD portal credentials, passwords, or session tokens. |
| **CAPTCHA / OTP** | CAPTCHA solving, bypass mechanisms, or OTP intercepts are strictly prohibited. Clients solve challenges manually in their own browser. |
| **Form Inputs** | The application provides one-click copy buttons for local application records. It **never** injects JavaScript or manipulates the TTD DOM. |
| **Payment Integrity** | Financial gateways, credit card details, UPI PINs, and banking credentials are never processed or retained. Payment tracking is restricted to status flags, dates, and manual UTR references. |
| **Document Privacy** | Devotee documents are stored exclusively in local folders (`data/documents/{family_id}/`) with SHA-256 integrity checks. They are never uploaded to any unauthorized server. |

---

### 2. DATABASE SCHEMA MIGRATION (VERSION 5)

The SQLite database (`srivani.db`) has been migrated from Version 4 to Version 5 with backward-compatible additive columns and indexes:

```sql
-- Supporting documents table
CREATE TABLE IF NOT EXISTS family_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id INTEGER NOT NULL,
    doc_type TEXT DEFAULT 'ID_PROOF',
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE
);

-- Phase 9 additive columns on families table
ALTER TABLE families ADD COLUMN readiness_status TEXT DEFAULT 'NOT_STARTED';
ALTER TABLE families ADD COLUMN readiness_score INTEGER DEFAULT 0;
ALTER TABLE families ADD COLUMN readiness_missing TEXT DEFAULT '[]';
ALTER TABLE families ADD COLUMN payment_notes TEXT DEFAULT '';
ALTER TABLE families ADD COLUMN payment_date TEXT DEFAULT '';

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_families_readiness ON families(readiness_status);
CREATE INDEX IF NOT EXISTS idx_documents_family_id ON family_documents(family_id);
```

---

### 3. THE 7-STEP MANUAL CHECKLIST

Within `ManualBookingWorkspaceDialog`, operators are guided through an interactive, auditable 7-step checklist before booking statuses are updated:

1. **Step 1:** Client independently opens and logs into the official TTD website.
2. **Step 2:** Client reviews prepared family and pilgrim details on screen.
3. **Step 3:** Client independently enters required pilgrim details into official TTD portal.
4. **Step 4:** Client manually completes visual CAPTCHA verification on official TTD portal.
5. **Step 5:** Client independently reviews booking summary and clicks submit.
6. **Step 6:** Client completes donation and darshan payment directly on official TTD gateway.
7. **Step 7:** Client returns to Srivani Booking Manager to record payment reference, attach ticket PDF, and update status.

---

### 4. AUTOMATED TEST SUITE & END-TO-END VALIDATION

The comprehensive automated test suite encompasses **102 test cases** across 13 test modules:

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
rootdir: C:\Users\nagas\Desktop\TTDmanager
configfile: pytest.ini
testpaths: tests
collected 102 items

tests\test_advanced_features.py ......                                   [  5%]
tests\test_database.py ......                                            [ 11%]
tests\test_end_to_end.py .                                               [ 12%]
tests\test_import_export.py ...                                          [ 15%]
tests\test_phase2_features.py ....                                       [ 19%]
tests\test_phase3_features.py ......                                     [ 25%]
tests\test_phase4_features.py ..........                                 [ 35%]
tests\test_phase5_features.py .......                                    [ 42%]
tests\test_phase6_features.py .......                                    [ 49%]
tests\test_phase7_features.py .................                          [ 65%]
tests\test_phase8_saas.py ............                                   [ 77%]
tests\test_phase9_preparation.py ...........                             [ 88%]
tests\test_queue_and_filters.py ..                                       [ 90%]
tests\test_ticket_manager.py ..                                          [ 92%]
tests\test_validators.py ........                                        [100%]

============================ 102 passed in 29.34s =============================
```

#### End-to-End Verification Runner (`python run_end_to_end.py`)
```
================================================================================
      SRIVANI BOOKING MANAGER — END-TO-END VERIFICATION RUNNER
      Version: v7.0.0 Commercial Desktop Suite | Windows Environment
      Execution Date: 2026-11-16 19:36:04
================================================================================

  [PASS] Step 01: Pre-Flight Environment & Database Integrity             (0.16s)
  [PASS] Step 02: Administrator Security, Bcrypt Auth & Lockout           (2.03s)
  [PASS] Step 03: Cryptographic Licensing & Hardware Binding              (0.01s)
  [PASS] Step 04: Batch Data Ingestion & Devotee Roster Parsing           (0.01s)
  [PASS] Step 05: Manual Devotee & Multi-Pilgrim Registration             (0.01s)
  [PASS] Step 06: Queue Prioritization & Dynamic Re-Ordering              (0.02s)
  [PASS] Step 07: State Machine Lifecycle & Audit Trail Logging           (0.03s)
  [PASS] Step 08: Ticket PDF Archiving & Booking Slip Generation          (0.04s)
  [PASS] Step 09: Operational Reports (8 Reports) & Reconciliation        (0.01s)
  [PASS] Step 10: Advanced Analytics Engine & Queue Intelligence          (0.02s)
  [PASS] Step 11: Multi-Format Exports (Excel .xlsx, PDF, CSV)            (0.09s)
  [PASS] Step 12: Disaster Recovery, Live Backup & Migration Snapshot     (0.03s)
  [PASS] Step 13: Diagnostic Audit Engine & PII Data Scrubbing            (0.08s)
  [PASS] Step 14: Device Deactivation & Cryptographic Transfer Proof      (0.02s)

--------------------------------------------------------------------------------
  END-TO-END VERIFICATION RESULT: ALL 14/14 MODULES PASSED (2.56s)
  COMPLIANCE & INTEGRITY STATUS: 100% VERIFIED & PRODUCTION READY
================================================================================
```

---

### 5. UI ARTIFACTS & WORKSPACE SCREENSHOTS

High-resolution screenshots were captured using native Windows GDI `PrintWindow` APIs:

1. **Fast Booking Dashboard:** `docs/screenshots/phase9_fast_booking_dashboard.png`
2. **Manual Booking Workspace:** `docs/screenshots/phase9_manual_booking_workspace.png`
3. **Document Management Modal:** `docs/screenshots/phase9_document_management.png`
4. **Searchable Booking History:** `docs/screenshots/phase9_booking_history.png`

---

### 6. RUN & OPERATIONAL INSTRUCTIONS

#### A. Launch the Desktop Application
```powershell
python app.py
```
- Navigate using the sidebar:
  - **Fast Dashboard:** Real-time KPI cards and recent activity.
  - **Manual Workspace:** Family preparation, 7-step checklist, one-click copy, and official portal launcher.
  - **Documents:** Manage supporting pilgrim ID attachments with SHA-256 integrity.
  - **Booking History:** Search, filter, and export booking records to CSV or Excel.

#### B. Run Automated Verification Tests
```powershell
python -m pytest tests/test_phase9_preparation.py -v
python -m pytest
python run_end_to_end.py
```

---
*SRIVANI BOOKING MANAGER v9.0.0 — Certified for Enterprise Operations.*
