# SRIVANI BOOKING MANAGER — v7.1.0 Client Release Guide

**Product:** SRIVANI BOOKING MANAGER  
**Release Version:** 7.1.0 Commercial Production Suite  
**Target Platform:** Windows 10 & 11 (64-bit)  
**Release Date:** 2026-11-16  

---

## 1. OVERVIEW

**SRIVANI BOOKING MANAGER v7.1.0** is an enterprise-grade Windows desktop application built to organize, validate, manage, and prepare Srivani Trust darshan bookings. It features offline devotee roster management, multi-pilgrim relationships, document indexing, payment tracking, queue prioritization, fast booking preparation workspaces, and a universal dataset import engine.

---

## 2. INSTALLATION INSTRUCTIONS

You can choose either the Windows Setup Installer or the Portable Edition:

### Option A: Windows Installer (Recommended)
1. Double-click `SrivaniBookingManager_Setup_v7.1.0.exe`.
2. Follow the standard installation wizard steps.
3. The installer creates a desktop shortcut and a Start Menu entry.
4. Launch the application from your desktop or Start Menu.

### Option B: Portable Edition
1. Extract `SrivaniBookingManager_v7.1.0_Portable.zip` into any folder (e.g., `C:\SRIVANI_Manager`).
2. Run `SrivaniBookingManager.exe` directly.
3. No administrative rights or external dependencies are required.

---

## 3. FIRST-RUN SETUP & AUTHENTICATION

1. **Initial Launch**:
   - On first startup, the Setup Wizard prompts you to create a master Administrator account.
   - Enter your preferred username and a secure password (stored using salted bcrypt hashing).
2. **License Activation**:
   - The application binds securely to your machine hardware.
   - Enter your client organization name and license key to activate commercial access.
3. **Clean Database**:
   - The system starts with an authentic 0-state database without sample or mock data.

---

## 4. DATASET IMPORT INSTRUCTIONS

To import existing devotee rosters from Excel or CSV:
1. Open the application and select **"📥 DATA IMPORT"** from the left navigation sidebar.
2. Click **"Select Dataset File"** and choose your `.csv` or `.xlsx` file.
3. The smart column mapper automatically correlates column headers:
   - `Household Name` / `Family Name` → `Family Name`
   - `Yatri Full Name` / `Devotee Name` → `Pilgrim Full Name`
   - `Contact Mobile` / `Phone` → `Mobile Number`
   - `Devotee Age` → `Age`
   - `ID Document` / `ID Reference` → `ID Proof Details`
4. Review the preview and real-time validation table.
5. Select your duplicate policy:
   - **Skip Duplicates**: Skips existing devotees and imports new ones.
   - **Update Existing**: Refreshes existing family contact info and pilgrim records.
   - **Cancel on Duplicate**: Aborts the import if any duplicate is found.
6. Click **"🚀 Import Valid Records"** to commit the batch.

---

## 5. FAST BOOKING WORKSPACE & MANUAL ASSISTANCE

1. Navigate to **"⚡ FAST BOOKING"** or select a family from the list.
2. Verify devotee readiness status (Green: `READY FOR MANUAL BOOKING`).
3. Click **"🌐 Open Official TTD Website"** to open `https://tirupatibalaji.ap.gov.in` in your standard browser.
4. Log into the official portal independently.
5. Use the 1-click **"📋 Copy"** buttons to copy pilgrim details to your clipboard and paste them (`Ctrl+V`) into the official TTD forms.

---

## 6. OPTIONAL POSTGRESQL / SAAS BACKEND

The standard desktop release runs entirely on an embedded, zero-configuration SQLite database engine. 

If you require the optional multi-client SaaS backend with PostgreSQL:
- Requirements: PostgreSQL 14+, Python 3.10+, FastAPI, `asyncpg`, `alembic`.
- See `OPTIONAL_BACKEND_DEPENDENCIES.md` for full setup instructions.
- The standalone desktop executable does not require PostgreSQL or external servers.
