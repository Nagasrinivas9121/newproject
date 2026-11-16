# SRIVANI BOOKING MANAGER v5.0.0
# Backup, Disaster Recovery & Data Integrity Guide

## 1. Overview
The **Disaster Recovery Engine** safeguards your critical client database (`srivani_manager.db`) against system crashes, disk failures, or accidental deletions.

Key capabilities:
- Online hot backup using SQLite's native backup API (`source_con.backup(dest_con)`).
- Pre-backup and post-backup integrity validation (`PRAGMA integrity_check`).
- Automatic pre-restore safety snapshots.
- Single-click restore with confirmation safeguards.

---

## 2. Creating a Database Backup

### 2.1 Manual Backup Creation
1. Click **"💾 Backup & Recovery"** in the sidebar navigation.
2. The **Database Backup & Recovery Manager** dialog appears, listing all historical backup archives with date, time, and file size.
3. Click the green button: **"✨ Create New Backup Now"**.
4. The system executes the following steps:
   - Validates the active database integrity.
   - Creates a snapshot: `data/backups/srivani_backup_YYYYMMDD_HHMMSS.db`.
   - Re-verifies the integrity of the newly created snapshot.
5. A confirmation message displays:
   > **Backup Created Successfully**: Snapshot created at `.../srivani_backup_20261114_153000.db` (Integrity: OK).

### 2.2 Automated Backups
- The application automatically generates a local backup:
  - Before performing any database restore operation.
  - Before executing mass Excel/CSV imports.
  - Whenever the auto-backup setting is enabled under **Preferences**.

---

## 3. Restoring from a Backup Archive

> [!CAUTION]
> Restoring a backup overwrites the current active database with the data contained in the chosen snapshot. Always verify which backup file you intend to restore.

### 3.1 Step-by-Step Restoration Procedure
1. Open **"💾 Backup & Recovery"** from the sidebar.
2. From the historical backup table, click on the desired backup snapshot.
3. Click the orange button: **"🔄 Restore Selected Backup"**.
4. Read the confirmation dialog carefully.
5. Click **"Yes"** to confirm.
6. The system automatically:
   - Takes a **Pre-Restore Safety Snapshot** (`srivani_backup_pre_restore_YYYYMMDD_HHMMSS.db`) of your current data.
   - Closes active database handles.
   - Restores the selected snapshot using the online backup engine.
   - Runs `PRAGMA integrity_check` on the restored database.
   - Refreshes all open dashboard tables and KPI counters immediately.
7. A success dialog confirms completion.

---

## 4. Database Integrity Verification

To inspect the structural health of your database:
1. Navigate to **"📈 Reports & Analytics"** in the sidebar.
2. Click **"🔍 Reconcile & Verify Totals"**.
3. The system checks:
   - **SQLite PRAGMA Integrity**: Checks for b-tree page corruption.
   - **Foreign Key Constraints**: Confirms that all pilgrim records belong to valid families.
   - **Orphan Record Check**: Verifies that no devotees exist without an associated family.
   - **Financial Reconciliation**: Confirms that donation totals match individual records.
4. If healthy, the report displays:
   > **Database Integrity & Totals Reconciliation**: All checks passed (0 anomalies).

---

## 5. Recommended Backup Routine for Administrators

| Frequency | Action | Destination |
| :--- | :--- | :--- |
| **Daily** | Click "Create New Backup Now" after daily bookings. | Local `data/backups/` |
| **Weekly** | Copy the `data/` directory (database + tickets) to an external USB drive or network share. | External Hard Drive / Flash Drive |
| **Monthly** | Generate and export the Monthly Executive Summary PDF and CSV report. | Accounting / Audit Folder |

---

## 6. Disaster Recovery in Case of Hardware Failure

If the computer fails or needs replacement:
1. Install **SRIVANI BOOKING MANAGER v5.0.0** on the new computer.
2. Complete the First-Run Setup Wizard.
3. Locate your latest backup file (`srivani_backup_*.db`) from your external drive.
4. Copy the file into the new computer's backup directory:
   `%LOCALAPPDATA%\SrivaniBookingManager\backups\`
5. Open the application, go to **Backup & Recovery**, select the copied snapshot, and click **Restore Selected Backup**.
6. Copy your archived ticket PDFs into `%LOCALAPPDATA%\SrivaniBookingManager\tickets\`.
7. All families, devotees, queue positions, and tickets are fully restored!
