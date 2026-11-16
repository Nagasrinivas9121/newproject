# SRIVANI BOOKING MANAGER
# Commercial Release Notes — Version 7.0.0

**Release Date:** November 2026  
**Target Platform:** Windows 10 / Windows 11 (64-bit)  
**Distribution Type:** Commercial Desktop Release (Standalone Executable + Setup Installer)  
**Architecture:** Python 3, Tkinter/TTK Modern GUI, SQLite3 Embedded Database, ReportLab Engine, OpenPyXL Engine

---

## 🌟 Version 7.0.0 Advanced Analytics & Operational Intelligence Release Highlights

### 1. Interactive Analytics Dashboard (`analytics_view.py`)
- **Real-Time KPI Summary Cards**: Live cards displaying Total Families, Total Devotees, Completed Bookings, Pending Backlog, Unavailable, Cancelled, Completion Rate (%), Total Donations Pledged, and Total Collections Realized.
- **Dynamic Date Filtering**: Instant slicing across `Today`, `Last 7 Days`, `Last 30 Days`, `This Month`, `Custom Date Range`, and `All Time` with real-time reactive table and metric updates.
- **5-Tab Deep Dive Workspace**: Structured operational views covering Booking Performance, Queue Intelligence, Payment Reconciliation, Document Compliance, and Operational Insights.

### 2. Booking Performance & Turnaround Metrics (`analytics_engine.py`)
- **Activity Trends**: Daily, weekly, and monthly trend breakdowns showing activity rates and booking outcomes.
- **Turnaround Lead-Time Analysis**: Precise calculation of average family processing turnaround time (lead time in hours and days) from record creation to final booking completion.
- **Throughput & Backlog Ratios**: Tracks the ratio of completed vs pending records to ensure administrative velocity matches demand.

### 3. Queue Intelligence & Bottleneck Detection
- **Queue Aging Categorization**: Classifies pending families into operational aging tiers (`< 24 Hours`, `1–3 Days`, `4–7 Days`, `> 7 Days`).
- **Attention Alerts Engine**: Automatically flags stalled requests, imminent preferred dates (within 3 days), high/urgent priority flags, and missing identity documents.
- **Bottleneck Diagnostics**: Identifies oldest pending records and status holding durations directly from actual SQLite database audit logs.

### 4. Payment Analytics & Reference Reconciliation
- **Financial Status Breakdown**: Direct aggregation of Paid, Pending, Failed, and Refunded transaction totals and monetary sums.
- **Reference Capture Rate**: Tracks payment transaction reference capture percentage to guarantee accounting audit readiness.
- **Date-Wise Collection Trends**: Daily donation collection summaries for finance reconciliation.

### 5. Document Analytics & Ticket Verification
- **Devotee Profile Completeness**: Audits ID proof records across all devotees, highlighting incomplete profiles.
- **Ticket Compliance Auditing**: Automatically identifies booked families lacking attached ticket PDFs and computes the ticket compliance rate (%).
- **Duplicate Prevention**: SHA-256 checksum tracking prevents identical ticket re-import across families.

### 6. Deterministic Operational Intelligence
- **Rule-Based Prioritization Engine**: Scores pending families using transparent, deterministic factors: priority flags (Urgent: +40, High: +25), preferred date imminence (+20 to +50), queue age (+5 to +25), and document readiness (+15 / -10).
- **Zero AI Hallucination**: No fake TTD availability predictions; all recommendations are grounded strictly in local administrative database records.

### 7. Multi-Format Analytics Exports (`analytics_export.py`)
- **Multi-Tab Formatted Excel Workbook (`.xlsx`)**: Comprehensive multi-tab export (Summary, Performance, Queue Intelligence, Payments, Documents) featuring auto-fitted column widths, styled header rows, and currency number formatting (`₹#,##0.00`).
- **Standardized CSV Exports**: Tabular CSV summaries for integration with spreadsheets and external data pipelines.
- **Executive Printable PDF**: Multi-page formatted PDF report with running headers, footers, and two-pass total page numbering.

---

## 🌟 Version 6.0.0 Commercial Operations Release Highlights

### 1. Commercial Client Onboarding & Environment Verification
- **Automated Verification Engine** (`client_verification.py`): Performs full pre-flight audit of SQLite database connectivity, PRAGMA integrity check, core table presence, admin account setup, ticket directory permissions, backup directory permissions, and hardware licensing status.
- **Client Configuration & Acceptance Checklists**: Structured 15-point functional sign-off checklists for formal commercial handovers.

### 2. Transparent Licensing & Device Transfer
- **Proactive Expiry Notifications**: Real-time visual banners notify operators when 14 or fewer days remain on an evaluation or subscription key.
- **Hardware Device Transfer Engine**: Built-in "Deactivate for Transfer" routine generates cryptographically signed Deactivation Proof codes (`DEACT-XXXX-XXXX-XXXX-XXXX`) allowing smooth re-issuance on new workstations without data loss.
- **Plaintext Certificate Export**: In-app export of official License Certificates (`srivani_license_certificate_*.txt`) for client IT records.

### 3. Safe Application Updates & Migration Safeguards
- **Pre-Update Atomic Snapshots** (`update_manager.py`): Automatically creates verified online snapshots (`srivani_pre_update_vX_*.db`) prior to any schema modification.
- **Migration Rollback Protection**: Schema migrations run inside transactions. Any failure or corruption automatically triggers an immediate rollback to the pre-update snapshot.
- **Protection Against Data Overwrite**: User data remains strictly preserved across application version updates.

### 4. Customer Support Hub & Sanitized Diagnostics
- **Customer Support Hub** (`support_diagnostics.py`): Dedicated in-app interface displaying helpdesk contact details, service hours, SLA commitments, and release history.
- **Sanitized Diagnostic Reports**: Generates detailed system and database health reports completely stripped of Personally Identifiable Information (zero donor names, phone numbers, Aadhaar numbers, or credentials).
- **Explicit Consent Gating**: Diagnostic reports can only be saved or exported after explicit user checkbox consent.

### 5. Commercial Legal Documentation Templates
- Comprehensive, professional contract templates marked for legal counsel review:
  - Client Software License Agreement Template.
  - Commercial License Terms Template.
  - Support & Maintenance Terms (SLA) Template.
  - Data Privacy Notice (Local Data Sovereignty guarantee).
  - Software Usage & Troubleshooting Guides.

---

## 🌟 Version 5.0.0 Commercial Release Highlights

### 1. Final Packaging & Windows Installer
- **Official Inno Setup Installer**: High-compression installer (`SrivaniBookingManager_Setup_v5.0.0.exe`) with installation directory selection, Desktop and Start Menu shortcuts, version metadata, and clean uninstaller.
- **Data Isolation Guarantee**: User databases, logs, and ticket PDFs are stored in `%LOCALAPPDATA%\SrivaniBookingManager`, completely isolated from application binaries. Upgrading the application will never overwrite or erase existing client data.
- **Portable Distribution Archive**: Standalone zero-install package (`SrivaniBookingManager_v5.0.0_Portable.zip`) ready for USB flash drive and offline workstation deployments.
- **Embedded PE Version Metadata**: Full Windows PE version resource info embedded into the executable with company branding and product identifiers.

### 2. Client Licensing & Machine Binding
- **Cryptographic Offline Verification**: HMAC-SHA256 signature verification enabling 100% offline activation without requiring internet access or network calls.
- **Machine Installation ID**: Salted hardware and OS binding (`SRVN-XXXX-XXXX-XXXX`) for single-admin workstation compliance.
- **30-Day Evaluation License**: Built-in instant evaluation mode allowing fresh users to explore all features immediately.
- **Non-Destructive Behavior**: Software never locks users out of their data; expired state operates in a transparent safe mode.
- **Vendor License Generator**: Standalone utility (`license_generator.py`) for distributors to issue commercial licenses.

### 3. 7-Step First-Run Setup Wizard
- Comprehensive setup workflow guiding administrators through:
  1. Welcome & TTD Portal Compliance Agreement.
  2. License Key Activation / Evaluation Launch.
  3. Master Admin Account Creation (salted bcrypt password).
  4. Data Directory Path Configuration.
  5. Ticket Storage Path Configuration.
  6. Disaster Recovery Backup Path Configuration.
  7. Final Confirmation & Workspace Initialization.

### 4. Enterprise Dual-Theming Engine
- Seamless real-time theme switching between **Modern Light** (clean executive daytime UI) and **Slate Dark** (low-strain evening mode).
- Custom TTK style configurations across Treeview tables, cards, tabs, and buttons.

### 5. Advanced Analytics & Printable PDF Reports
- 8 comprehensive operational reports:
  - Daily Completed Bookings
  - Weekly Operational Analysis
  - Monthly Executive Summary
  - Booking Status Summary
  - Pending Queue Roster
  - Unavailable & Cancelled Bookings
  - Payment Reconciliation
  - Devotee Demographic Distribution
- Executive multi-page PDF generation via ReportLab with running headers, footers, and page numbers.
- Automated totals reconciliation tool (`validate_report_totals()`) verifying zero database discrepancies or orphan records.

### 6. Security, Reliability & Compliance
- **Salted Bcrypt Hashing**: Industry-standard password hashing with brute-force lockout protection (5 attempts -> 5-minute cooldown).
- **PII Log Redaction**: Automatic masking of 12-digit identification numbers and passwords in rotating log files.
- **Ticket Checksumming**: SHA-256 duplicate verification preventing identical ticket re-import.
- **Online Hot Backups**: SQLite hot backup engine with pre-restore safety snapshots.
- **TTD Manual Operational Compliance**: Official portal login, CAPTCHA solutions, OTP verifications, and payments remain strictly under the client's manual control.

---

## 📋 Comprehensive Feature Evolution Summary

| Phase | Milestone Description | Status |
| :---: | :--- | :---: |
| **Phase 1** | Foundation architecture, initial SQLite schema, basic CSV import, queue tracking | **Completed** |
| **Phase 2** | Professional Dashboard, KPI summary cards, Excel (.xlsx) preview dialog, pilgrim CRUD, queue sorting | **Completed** |
| **Phase 3** | Family Booking Workspace, Document Readiness assessment, ticket PDF organization, payment tracking, backup manager | **Completed** |
| **Phase 4** | Production readiness, single-admin auth, bcrypt, light/dark themes, advanced reports, printable PDFs, PyInstaller build | **Completed** |
| **Phase 5** | Commercial release, Inno Setup installer, client licensing, 7-step setup wizard, full user documentation, QA release package | **Delivered** |
| **Phase 6** | Commercial operations, client onboarding, license management & transfer, pre-update backup, diagnostic reports, legal contracts | **Delivered** |
| **Phase 7** | Advanced Analytics & Operational Intelligence: Interactive dashboard, queue aging, payment/document auditing, heuristic prioritization, multi-tab Excel & PDF exports | **Delivered** |

---

## 🔒 TTD Portal Compliance Guarantee

The application is explicitly designed as an **Assisted Administrative Tool**. The client must manually log into the official TTD portal (`https://ttdevasthanams.ap.gov.in`), solve CAPTCHA challenges, enter SMS OTPs, and authorize payments. The application contains no bots, automated submission scripts, or security bypass mechanisms.
