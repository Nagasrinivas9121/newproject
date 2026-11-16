# SRIVANI BOOKING MANAGER v5.0.0
# Troubleshooting & Operational Resolution Guide

## 1. Quick Resolution Matrix

| Symptom / Issue | Likely Cause | Solution |
| :--- | :--- | :--- |
| **"Account is temporarily locked"** | 5 consecutive wrong password attempts. | Wait 5 minutes for the lockout timer to expire, then re-enter the correct password. |
| **"License key signature does not match"** | Mismatch in Client Name or Installation ID. | Check spelling in Client Name; ensure it matches the name provided during purchase exactly. |
| **"Duplicate Ticket Detected"** | The same PDF file was already imported. | Check if the ticket was previously attached or belongs to another family in the table. |
| **Ticket PDF will not open** | No default Windows PDF viewer configured. | Right-click any PDF file in Windows Explorer -> *Open with* -> Choose Adobe Acrobat or Microsoft Edge and set as default. |
| **Excel import gives column errors** | Missing required header columns. | Download the sample template via *Import & Export* -> *Download Sample Excel Template* and align headers. |
| **"Permission Denied" on startup** | Read-only folder or antivirus lock. | Ensure `%LOCALAPPDATA%\SrivaniBookingManager` is not set to Read-Only; run application as standard user. |

---

## 2. Administrator Authentication Issues

### 2.1 Account Lockout
- **Behavior**: After 5 failed password attempts, the message reads:
  `Account locked for 5 minutes due to 5 failed attempts.`
- **Resolution**:
  - The lock clears automatically after exactly 5 minutes from the last attempt.
  - Do not keep guessing passwords while locked, as each attempt resets the timer.

### 2.2 Resetting Administrator Password
If the administrator password is completely forgotten:
1. Close the application.
2. Open PowerShell or Command Prompt in the application folder.
3. Run the secure reset command:
   ```cmd
   python -c "from auth import change_admin_password, get_connection; con = get_connection(); con.execute('UPDATE admin_users SET failed_attempts=0, locked_until=NULL'); con.commit(); print('Lockout cleared.')"
   ```
4. If a master password reset is required, run:
   ```cmd
   python -c "from auth import hash_password, get_connection; h = hash_password('NewMaster@123'); con = get_connection(); con.execute('UPDATE admin_users SET password_hash=? WHERE username=\'admin\'', (h,)); con.commit(); print('Password reset to NewMaster@123')"
   ```
5. Launch the application and sign in with the temporary password `NewMaster@123`, then change it immediately under **Preferences**.

---

## 3. Client Licensing Issues

### 3.1 Finding Your Machine Installation ID
- Open **Preferences & About** -> **Client Licensing**.
- Your unique Installation ID is shown in the box (e.g., `SRVN-XXXX-XXXX-XXXX`).
- Click **"📋 Copy ID"** to copy it and email it to your software vendor for key re-issuance.

### 3.2 Evaluation Period Expiry
- If your 30-day evaluation period expires, the software switches to **Grace / Safe Mode**.
- *Important*: The software **never locks you out of your data** or deletes records.
- You can continue viewing records, running reports, and taking database backups.
- To re-activate full commercial access, enter your commercial key under **Preferences** -> **Client Licensing**.

---

## 4. Excel & CSV Import Issues

### 4.1 Required Columns
The import parser expects the following standard columns (case-insensitive with synonym matching):
- `Family Name` (or `Family`, `Household`)
- `Contact Name` (or `Primary Contact`, `Lead Pilgrim`)
- `Phone` (or `Mobile`, `Contact Number`)
- `Devotee Name` (or `Pilgrim Name`, `Full Name`, `Member Name`)
- `Age` (Numeric 0–120)
- `Gender` (`Male`, `Female`, `Other`)
- `ID Proof Type` (`Aadhaar`, `Voter ID`, `Passport`, `Driving License`, `PAN Card`)
- `ID Proof Last 4` (Exactly 4 digits)

### 4.2 Duplicate Rows During Import
- The visual import preview dialog automatically detects if a family already exists in the database by matching Phone Number and Family Name.
- Existing records are highlighted with duplicate warnings and can be skipped before committing.

---

## 5. Database Diagnostic & Recovery

If the database ever experiences unexpected shutdown:
1. Launch the application and navigate to **Reports & Analytics**.
2. Click **"🔍 Reconcile & Verify Totals"**.
3. If SQLite reports b-tree errors, open **Backup & Recovery** and restore the most recent verified backup.
4. If you have any unresolved issues, contact technical support with your log file located at:
   `%LOCALAPPDATA%\SrivaniBookingManager\logs\srivani_manager.log`.
