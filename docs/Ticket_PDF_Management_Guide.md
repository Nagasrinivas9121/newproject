# SRIVANI BOOKING MANAGER v5.0.0
# Ticket PDF Management & Document Organization Guide

## 1. Overview
The **Ticket Management Engine** organizes, validates, archives, and displays official Srivani Trust donation receipts and VIP Break Darshan admission tickets.

Key features:
- Automated folder organization by Family Code (`data/tickets/<family_code>/`).
- SHA-256 cryptographic duplicate detection.
- Fast 1-click native Windows viewer launching.
- Devotee Summary Slip generation (PDF) using ReportLab.

---

## 2. Importing Downloaded Ticket PDFs

### 2.1 How to Import
1. Select the family in the queue table or booking workspace.
2. Click **"📥 Import Ticket PDF"** (or right-click -> `Manage Ticket PDF`).
3. Browse and select the downloaded PDF from your computer (e.g. from `Downloads`).
4. Enter the official **Ticket / Booking Reference Number** (optional, extracted from portal).
5. Click **"Import & Archive Ticket"**.

### 2.2 Organized Folder Structure
Imported ticket files are renamed and archived systematically:
```
data/
└── tickets/
    └── FAM-20261114-A1B2/
        ├── FAM-20261114-A1B2_Ticket_20261114_143000.pdf
        └── FAM-20261114-A1B2_DevoteeSlip.pdf
```
This ensures tickets are never misplaced, overwritten, or accidentally scrambled between families.

---

## 3. Cryptographic Duplicate Prevention

To prevent human error during fast booking sessions (such as importing the same ticket twice or attaching a ticket to the wrong family):
1. The application computes a **SHA-256 cryptographic checksum** of every imported PDF.
2. The checksum is recorded in the `families.ticket_checksum` database column.
3. If an operator attempts to import a ticket file identical to an already imported ticket, the system intercepts the action:
   > **⚠️ Duplicate Ticket Detected**: This exact PDF document has already been imported for family 'Sharma Family' (FAM-20261114-9988) on 2026-11-14 14:15. Duplicate import rejected.
4. This ensures total audit integrity and prevents multiple donors from being issued duplicate tickets.

---

## 4. Opening and Viewing Tickets

- In the queue table or family workspace, click **"📂 Open Ticket PDF"**.
- The application invokes the Windows default PDF reader (Adobe Acrobat Reader, Microsoft Edge, or Chrome) via native Windows process launching (`os.startfile`).
- You can print or email the ticket directly from your native viewer.

---

## 5. Generating Official Devotee Summary Slips

Before darshan or travel, operators can generate an executive **Devotee Summary Slip**:
1. Select the family and right-click -> **"Generate Devotee Summary Slip"**.
2. The ReportLab engine compiles a formatted document containing:
   - Srivani Trust Donation Reference
   - Family ID and Primary Contact Details
   - Devotee Roster (Names, Ages, Genders, ID Proof Types, Masked Numbers)
   - Reporting instructions and darshan slot recommendations.
3. The slip is saved as a PDF and can be printed or handed directly to the family head.

---

## 6. Document Integrity & Safety Rules

- **Do Not Modify Official PDFs**: This software never alters or tampers with official e-receipts issued by the Tirumala Tirupati Devasthanams.
- **Backing Up Tickets**: Ticket PDFs stored in `data/tickets/` should be included in your weekly off-site backups or archived to an external drive.
