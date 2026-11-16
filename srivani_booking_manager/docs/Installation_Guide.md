# SRIVANI BOOKING MANAGER v5.0.0
# Installation & Deployment Guide

## 1. System Requirements

| Component | Minimum Requirement | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 (64-bit) Build 1809+ | Windows 11 (64-bit) |
| **Processor** | Dual-Core 1.6 GHz or faster | Quad-Core 2.0 GHz or faster |
| **RAM** | 2 GB | 4 GB or higher |
| **Free Disk Space** | 200 MB for application files | 2 GB+ for ticket PDFs and backups |
| **Display Resolution** | 1280 x 720 (HD) | 1920 x 1080 (Full HD) |
| **Prerequisites** | None (All runtimes bundled) | PDF Viewer (Adobe Acrobat / Edge) |

---

## 2. Installation Options

### Option A: Standard Windows Setup Wizard (Recommended)
1. Locate the installer executable:
   `SrivaniBookingManager_Setup_v5.0.0.exe`
2. Double-click the file to start the setup wizard.
3. Choose the installation directory (Default: `C:\Program Files\SRIVANI BOOKING MANAGER`).
4. Select optional tasks:
   - `[x] Create a Desktop Shortcut`
   - `[x] Create a Start Menu Shortcut`
5. Click **Install**.
6. When installation finishes, check **"Launch SRIVANI BOOKING MANAGER"** and click **Finish**.

### Option B: Portable Package (No Installation Required)
1. Locate `SrivaniBookingManager_v5.0.0_Portable.zip`.
2. Right-click the zip archive and choose **Extract All...**.
3. Extract to your preferred location (e.g., `C:\SrivaniBookingManager` or a USB drive).
4. Double-click `SrivaniBookingManager.exe` to run immediately.

---

## 3. First-Run Setup Wizard

Upon launching the application for the first time, the **7-Step First-Run Setup Wizard** guides you through initialization:

1. **Step 1: Welcome & Compliance Agreement**:
   - Review the overview and acknowledge the official TTD portal guidelines.
   - Check the agreement box and click **Next Step >**.
2. **Step 2: Client Licensing**:
   - Note your unique **Machine Installation ID** (e.g., `SRVN-XXXX-XXXX-XXXX`).
   - Choose **"Start with 30-Day Evaluation License"** or enter your commercial license key.
3. **Step 3: Master Admin Account Setup**:
   - Enter your preferred Admin Username (default: `admin`).
   - Enter your Full Name / Display Name.
   - Enter a secure master password (minimum 6 characters) and confirm it.
4. **Step 4: Application Data Directory**:
   - Default: `%LOCALAPPDATA%\SrivaniBookingManager`.
   - Stores your SQLite database, queue rosters, and audit logs safely outside the program directory.
5. **Step 5: Ticket Storage Location**:
   - Default: `%LOCALAPPDATA%\SrivaniBookingManager\tickets`.
   - Location where downloaded ticket PDFs will be archived.
6. **Step 6: Backup Storage Location**:
   - Default: `%LOCALAPPDATA%\SrivaniBookingManager\backups`.
   - Folder where disaster recovery snapshots are preserved.
7. **Step 7: Confirmation & Launch**:
   - Review your configuration summary and click **✨ Finish & Open Application**.

---

## 4. Upgrading an Existing Installation

1. Before upgrading, create a manual database backup via `Backup & Recovery` -> `Create New Backup Now`.
2. Run the new installer `SrivaniBookingManager_Setup_vX.X.X.exe`.
3. The installer automatically replaces executable binaries while **preserving all client databases, imported ticket PDFs, and application settings** in `%LOCALAPPDATA%`.
4. Launch the application; automatic database migrations will seamlessly apply any new schema updates.

---

## 5. Uninstallation

1. Open **Windows Settings** -> **Apps** -> **Installed Apps** (or Control Panel -> Programs and Features).
2. Find **SRIVANI BOOKING MANAGER** and click **Uninstall**.
3. Follow the uninstallation prompts.
4. *Data Safety Note*: Your client database, ticket PDFs, and backups are kept safe in `%LOCALAPPDATA%\SrivaniBookingManager` unless manually deleted.
