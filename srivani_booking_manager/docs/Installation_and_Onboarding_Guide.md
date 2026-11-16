# SRIVANI BOOKING MANAGER — INSTALLATION & ONBOARDING GUIDE

## 1. System Requirements
- **Operating System:** Microsoft Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Processor:** Intel Core i3 / AMD Ryzen 3 or higher.
- **Memory (RAM):** 4 GB RAM minimum (8 GB recommended).
- **Disk Storage:** 500 MB free space for application installation; additional space for ticket PDFs and automated backups.
- **Display Resolution:** 1280 x 720 minimum (1920 x 1080 recommended).
- **Web Browser:** Google Chrome, Microsoft Edge, or Mozilla Firefox for external TTD portal access.

---

## 2. Installation Walkthrough (Standard Inno Setup)
1. Locate `SrivaniBookingManager_Setup_v6.0.0.exe` in the `SRIVANI_BOOKING_MANAGER_RELEASE/Installer` directory.
2. Double-click the executable to launch the Setup Wizard. If prompted by Windows User Account Control (UAC), click **Yes**.
3. Select your desired installation destination (default: `C:\Program Files\Srivani Booking Manager`).
4. Select optional tasks:
   - [x] Create a desktop shortcut.
   - [x] Create a Start Menu shortcut group.
5. Click **Install**. The files will be deployed and verified in seconds.
6. Click **Finish** to complete setup and launch the application.

---

## 3. Portable Distribution (Zero-Install Alternative)
For environments where software cannot be installed into `Program Files`:
1. Extract `SrivaniBookingManager_v6.0.0_Portable.zip` to a secure local folder (e.g., `D:\SrivaniManager`).
2. Run `SrivaniBookingManager.exe` directly from the extracted folder.
3. User data, tickets, and backups will be safely stored in `%LOCALAPPDATA%\SrivaniBookingManager`.

---

## 4. First-Run Setup & Initialization
Upon launching the application for the first time, the **7-Step Guided Setup Wizard** automatically appears:
- **Step 1 — Welcome:** Review application purpose and assisted workflow guidelines.
- **Step 2 — License Terms:** Review commercial license and privacy conditions.
- **Step 3 — Client Licensing:** View your machine-bound Installation ID (`SRVN-XXXX-XXXX-XXXX`). Enter your commercial key or start the 30-day evaluation trial.
- **Step 4 — Master Administrator Setup:** Choose an admin username (minimum 3 characters) and a strong password (minimum 8 characters). Credentials are saved using salted bcrypt hashing.
- **Step 5 — Storage Paths:** Confirm or select custom storage folders for your database, ticket PDFs, and automated backups.
- **Step 6 — Configuration Confirmation:** Inspect all chosen parameters.
- **Step 7 — Initialization Complete:** Click **Complete Setup & Launch** to open the secure administrator login.

---

## 5. Environment Self-Check Verification
To confirm that your environment is 100% operational:
1. Open the application and log in as Administrator.
2. Click **⚙️ Preferences & About** on the bottom-left sidebar.
3. Navigate to **ℹ️ About & Version** and click **🔍 Run Environment Audit**.
4. Confirm that:
   - SQLite Database integrity reports **[PASS]**.
   - Database schema structure reports **[PASS]**.
   - Ticket and backup directories report **[PASS]**.
