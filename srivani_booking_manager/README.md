# SRIVANI BOOKING MANAGER — Production Desktop Suite (v4.0.0)
## Complete Professional Family & Devotee Booking Management System

A production-grade Windows desktop application engineered specifically for managing Srivani Trust (Sri Venkateswara Aalaya Nirmanam Trust) family records, multi-devotee rosters, sequential queue prioritization, ticket PDF archiving, advanced operational analytics, and automated disaster recovery.

Built for single-admin / operator desktop workflows using Python 3, Tkinter/TTK, and SQLite, with full Windows 10/11 native compatibility.

---

## 🌟 Key Capabilities & Architecture

### MODULE 1 – Professional UI & Theming (`themes.py`, `app.py`)
- **Theme Engine**: Seamless real-time switching between **Modern Light** (default clean aesthetic) and **Slate Dark** (low-strain dark mode).
- **Executive Navigation Sidebar**: Intuitive navigation with quick indicators, session lock, preferences, and theme toggle.
- **Summary KPI Cards**: Real-time counter cards for Total Families, Total Devotees, Pending Queue, In Progress, Booked, and Cancelled.
- **Responsive Layout**: Designed for standard laptop and desktop displays with horizontal/vertical scrolling on all data tables.

### MODULE 2 – Admin Security & Authentication (`auth.py`)
- **Single-Admin Local Authentication**: First-run setup wizard creates the primary administrator credentials.
- **Bcrypt Password Hashing**: Cryptographic password hashing with salted rounds using `bcrypt`.
- **Brute-Force Lockout Protection**: Automatically locks the account for 5 minutes after 5 consecutive failed login attempts.
- **Session Locking & Logout**: Lock the workstation session anytime with one click; unlocks instantly upon entering the master password.
- **PII Data Protection**: Redacts 12-digit identification numbers and passwords from application logs automatically.

### MODULE 3 – Database & Performance (`database.py`)
- **Schema Migration Versioning**: Managed schema version tracking (`schema_version` table) supporting incremental upgrades (v1 through v4).
- **Composite Index Optimization**:
  - `idx_families_queue_sort` on `(status, priority, queue_order)`
  - `idx_families_phone` on `(phone)`
  - `idx_families_date` on `(preferred_date)`
  - `idx_pilgrims_name` on `(full_name)`
- **Database Integrity Checks**: Automated `PRAGMA integrity_check` and `PRAGMA foreign_key_check` diagnostic verification.

### MODULE 4 – Advanced Reports & Analytics (`reports.py`)
- **8 Comprehensive Operational Reports**:
  1. **Daily Completed Bookings**: Daily breakdowns of booked families, pilgrims, and donations.
  2. **Weekly Operational Analysis**: Grouped by calendar week (YYYY-Www) with booked vs. pending ratios.
  3. **Monthly Executive Summary**: Month-by-month financial and booking volume breakdown.
  4. **Booking Status Summary**: Aggregate snapshot across all operational statuses.
  5. **Pending Families in Queue**: Prioritized queue list awaiting darshan booking.
  6. **Failed or Unavailable Bookings**: Families marked Unavailable/Cancelled with administrative notes.
  7. **Payment Status Breakdown**: Financial reconciliation and transaction reference counts.
  8. **Total Pilgrims Demographics**: Devotee demographic breakdown by gender, age bracket, and booking quota.
- **Printable Executive PDF Generation**: Generates high-quality, formatted printable reports using ReportLab with running headers, footers, and page numbers.
- **CSV Data Export**: Single-click export for all reports.
- **Totals Reconciliation Verification**: Automated checksum validation ensuring devotee and financial totals match underlying tables without discrepancies.

### MODULE 5 – Reliability & Structured Logging (`logger.py`, `backup_manager.py`)
- **Structured Rotating File Logger**: 5MB rotating file handler with 5-file retention in `data/logs/srivani_manager.log`.
- **Duplicate Ticket Prevention**: SHA-256 cryptographic checksums prevent importing duplicate official ticket PDFs.
- **Disaster Recovery**: Online verified SQLite backup engine with pre-restore safety snapshots.

### MODULE 6 – Application Preferences (`settings.py`)
- Persistent application settings stored in SQLite (`app_settings` table).
- Customizable paths for Ticket PDFs, Database Backups, and CSV/PDF Exports.
- Inactivity timeout configuration and auto-backup toggle.
- Admin profile management (display name and password change dialogs).

### MODULE 7 – Windows Deployment & Packaging
- **Standalone Windows Executable**: Built with PyInstaller (`dist/SrivaniBookingManager/SrivaniBookingManager.exe`).
- **External User Data Preservation**: When frozen, automatically stores persistent user data in `%LOCALAPPDATA%\SrivaniBookingManager` so application updates never overwrite user databases.
- **Multi-Resolution Application Icon**: `assets/app_icon.ico` with 16x16, 32x32, 48x48, 64x64, 128x128, and 256x256 resolutions.
- **Portable Distribution Zip**: Complete self-contained package `dist/SrivaniBookingManager_v4.0.0_Windows_x64.zip` (27.6 MB).
- **Inno Setup Script**: `installer.iss` and `build_installer.ps1` for creating standard Windows setup installers.

---

## 🔒 TTD Portal Compliance & Operational Boundaries

1. **Manual Operator Control**: Login to the official TTD portal, CAPTCHA solutions, SMS OTP verifications, and payment authorizations remain strictly under the client's manual control.
2. **No Restricted Automation**: This software does **not** bypass quotas, automate bot submissions, or bypass CAPTCHA/OTP gates.
3. **Sensitive Credential Protection**: This application never asks for or stores banking credentials, debit/credit card numbers, UPI PINs, or TTD portal passwords.
4. **Official Website**: `https://ttdevasthanams.ap.gov.in` is launched in the user's native web browser.

---

## 🚀 Execution Instructions (Windows)

### Running from Python Source
1. Double-click `run_windows.bat` or run:
   ```cmd
   python app.py
   ```
2. First-Run Setup: Create your initial admin account in the setup dialog.
3. Sign in to access the booking manager.

### Running Standalone Executable
- Navigate to `dist/SrivaniBookingManager/` and double-click `SrivaniBookingManager.exe`.
- Or unzip `dist/SrivaniBookingManager_v4.0.0_Windows_x64.zip` on any 64-bit Windows machine and launch `SrivaniBookingManager.exe` directly (no Python installation required).

### Running Automated Test Suite
Execute all 47 tests across the 9 test suites:
```cmd
python -m pytest -v
```

---

## 📁 Project Architecture

```
TTDmanager/
├── app.py                     # Main Windows application & view controller
├── assisted_booking.py        # Assisted booking companion window with 1-click clipboard helpers
├── auth.py                    # Admin security, bcrypt hashing, lockout & session locking
├── backup_manager.py          # SQLite online backup & restore engine
├── booking_workspace.py       # Family booking workspace & step-by-step checklist
├── build_exe.py               # Automated PyInstaller packaging script
├── build_installer.ps1        # PowerShell Windows installer & portable zip builder
├── config.py                  # Global application configuration & paths
├── database.py                # SQLite persistence, schema migrations & composite indexes
├── family_dialogs.py          # Add/Edit Family, Status Update & History dialogs
├── import_export.py           # Excel (.xlsx) and CSV import/export engine
├── installer.iss              # Inno Setup Windows installer configuration
├── logger.py                  # Structured rotating logger with PII sanitization
├── reports.py                 # Advanced reporting, CSV export & ReportLab printable PDF generator
├── run_windows.bat            # Windows 1-click launch batch file
├── settings.py                # Persistent settings & Preferences dialog
├── srivani_manager.spec       # PyInstaller specification file
├── themes.py                  # Professional Light and Dark theme palettes & TTK styling
├── validators.py              # Phone, age, date & ID proof validation
├── version_info.txt           # Windows PE version resource metadata
├── assets/
│   ├── app_icon.ico           # Multi-resolution Windows icon (16x16 to 256x256)
│   └── app_icon.png           # High-resolution PNG logo
├── dist/
│   ├── SrivaniBookingManager/ # Packaged standalone Windows application folder
│   └── SrivaniBookingManager_v4.0.0_Windows_x64.zip # Portable distribution archive (27.6 MB)
└── tests/
    ├── test_advanced_features.py
    ├── test_database.py
    ├── test_import_export.py
    ├── test_phase2_features.py
    ├── test_phase3_features.py
    ├── test_phase4_features.py
    ├── test_queue_and_filters.py
    ├── test_ticket_manager.py
    └── test_validators.py
```
