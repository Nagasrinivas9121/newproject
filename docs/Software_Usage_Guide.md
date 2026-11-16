# SRIVANI BOOKING MANAGER — COMPREHENSIVE SOFTWARE USAGE GUIDE

## 1. Overview & Core Philosophy
SRIVANI Booking Manager provides an assisted, sequential queue workflow for pilgrimage managers, tour coordinators, and temple trusts. It bridges the gap between chaotic spreadsheet lists and manual bookings on the official Tirumala Tirupati Devasthanams (TTD) portal.

---

## 2. Navigating the Interface
The application features a modern sidebar navigation with six core views:
1. **📊 Dashboard & Queue:** Real-time metrics, sequential family queue table, search, status filters, and one-click quick actions.
2. **⚡ Family Workspace:** Dedicated focused workspace for the active family, showing pilgrim rosters, document readiness, copy shortcuts, and step-by-step checklist.
3. **👥 Families & Devotees:** Comprehensive directory of all registered families and devotees.
4. **📥 Import & Export:** Bulk Excel (`.xlsx`) and CSV import with duplicate detection; CSV and Excel export.
5. **📈 Reports & Analytics:** Daily completed bookings, weekly analysis, failed/unavailable logs, payment breakdowns, and printable PDF generation.
6. **📜 Queue History:** Chronological, tamper-evident audit trail of all queue events, status transitions, and priority modifications.
7. **💾 Backup & Recovery:** Point-in-time database snapshots, backup integrity validation, and one-click restoration.

---

## 3. Step-by-Step Assisted Booking Workflow
The application guides operators through an assisted 7-step process:
1. **Step 1 — Family Selection:** Select the pending family from the top of the queue table or in the Family Workspace.
2. **Step 2 — Devotee Details Review:** Verify full names, ages, genders, and ID proofs against original documents.
3. **Step 3 — Document Readiness Check:** Ensure all required proofs are verified and ready.
4. **Step 4 — Open Official TTD Portal:** Click the **🌐 Open Official TTD Portal** button to launch `https://ttdevasthanams.ap.gov.in` in your secure default browser.
5. **Step 5 — Client Manual Login & Booking:**
   - Log into the TTD portal manually using your registered mobile number and OTP.
   - Solve the CAPTCHA challenge personally.
   - Copy-paste devotee details from the Family Workspace using the convenient one-click copy buttons.
   - Submit the application and authorize payment directly via your bank / UPI app.
6. **Step 6 — Record Booking Result:**
   - In the application, update the booking status to **Booked** (or **Unavailable** if quotas were exhausted).
   - Enter the official TTD Booking Reference / Donation Receipt Number.
   - Update payment status to **Paid**.
7. **Step 7 — Import Downloaded Ticket PDF:**
   - Download the official ticket PDF from the TTD portal.
   - Click **📄 Import Ticket PDF** to store it in organized local folders. The application calculates an SHA-256 checksum to prevent accidental duplicate ticket imports.

---

## 4. Family & Devotee Management
- **Add Family:** Click **➕ Add Family** to enter primary contact information, donation figures, quota type (Advance vs. Current), and preferred date. Add multiple devotees to the family roster.
- **Edit Family:** Double-click any row in the queue table to modify family details or add/remove devotees.
- **Priority Re-ordering:** Assign priorities (**Urgent**, **High**, **Normal**, **Low**) to push urgent families to the front of the booking queue.

---

## 5. Data Import & Duplicate Safeguards
- **Excel (.xlsx) and CSV:** Use the **📥 Import & Export** view to import bulk donor rosters.
- **Preview & Validation:** The system validates phone numbers (10 digits) and Aadhaar last-4 digits before import.
- **Duplicate Prevention:** Matches against existing family names, codes, and primary contact phone numbers. Duplicate records are detected and skipped with clear error reporting.

---

## 6. Backups & Disaster Recovery
- To create a point-in-time snapshot, navigate to **💾 Backup & Recovery** and click **💾 Create Backup Now**.
- Backups are stored in `%LOCALAPPDATA%\SrivaniBookingManager\backups` with verified SQLite online backup integrity checks.
- Restoration can be performed anytime from the backup list. The system automatically creates a pre-restore safety copy before overwriting the active database.
