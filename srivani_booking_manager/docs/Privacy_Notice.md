# DATA PRIVACY & COMPLIANCE NOTICE

> **Notice Date:** November 2026  
> **Applies to:** SRIVANI Booking Manager Desktop Suite (All Versions)

---

### 1. PRINCIPLE OF LOCAL DATA SOVEREIGNTY
SRIVANI Booking Manager is engineered around the principle of **Local Data Sovereignty**.
- **100% Offline Operation:** All family profiles, pilgrim rosters, phone numbers, ID proof references, donation amounts, queue sequences, and ticket PDFs are stored exclusively on your local workstation's hard drive.
- **Zero External Telemetry:** The application contains no background telemetry engines, tracking scripts, web beacons, or analytics daemons. No data is silently uploaded to cloud servers.
- **No Advertising:** The application contains zero promotional third-party software or tracking code.

---

### 2. STRICT PROHIBITION ON BANKING & TTD CREDENTIAL STORAGE
In compliance with data protection best practices and statutory payment guidelines:
- **Zero TTD Password / OTP Capture:** The application never requests, captures, logs, or stores TTD portal login passwords or SMS one-time passwords (OTPs).
- **Zero Payment Credential Capture:** The application never requests, handles, or saves UPI PINs, card CVVs, debit/credit card numbers, or Net Banking credentials.
- **Client Manual Control:** When completing donations and bookings, the client interacts directly with the official TTD website and their chosen banking provider in an external web browser.

---

### 3. PERSONAL DATA HANDLED LOCALLY
The following data fields are stored in the local SQLite database for roster management purposes:
- Primary Contact Name, Phone Number, Email, and Address.
- Devotee Full Name, Age, Gender, and ID Proof Type (e.g., Aadhaar / Voter ID).
- Last 4 digits of ID proof (the application discourages storing full 12-digit Aadhaar numbers).
- Booking preference dates, quota type (Advance vs. Current), and donation figures.
- Downloaded ticket PDF files stored in the local ticket storage directory.

---

### 4. LOGS & DIAGNOSTIC SANITIZATION
- Application diagnostic logs stored locally in `%LOCALAPPDATA%\SrivaniBookingManager\srivani_manager.log` systematically redact phone numbers, ID proof numbers, and passwords.
- The **Customer Support Diagnostic Report** generated via the UI is 100% scrubbed of Personally Identifiable Information (PII) and is only exported or shared upon explicit user confirmation.

---

### 5. DATA RETENTION & REMOVAL
Because all records exist solely on the client's local PC, data retention is entirely under the client's direct control. Deleting a family record or deleting the database file permanently removes that data from the machine.
