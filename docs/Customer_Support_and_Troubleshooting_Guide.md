# CUSTOMER SUPPORT & TROUBLESHOOTING GUIDE

## 1. Official Support Helpdesk
- **Primary Support Email:** `support@srivani-booking-manager.local`
- **Helpdesk Operating Hours:** Monday to Saturday, 09:00 AM to 06:00 PM IST
- **Emergency Escalation:** In case of database integrity alerts, include `[CRITICAL-DB]` in your email subject line for prioritized 4-hour response.

---

## 2. Generating a Non-PII Diagnostic Report
When requesting technical assistance, always attach a sanitized diagnostic report so our engineers can understand your system state without exposing any donor names, phone numbers, or passwords:
1. In the application, click **🎧 Support & Diagnostics** on the bottom-left sidebar.
2. Select the **🩺 System Diagnostics** tab.
3. Review the preview: notice that all phone numbers, Aadhaar numbers, and passwords are fully redacted.
4. Check the consent box:  
   *`[x] I confirm this report contains no personal data and consent to export/share it with support.`*
5. Click **💾 Save Diagnostic Report to File...** and save `srivani_diagnostic_YYYYMMDD_HHMMSS.txt`.
6. Attach this file to your support email.

---

## 3. Common Issues & Fast Resolutions

### Issue 1: "Database Locked" or SQLite Access Error
- **Symptom:** Application shows `sqlite3.OperationalError: database is locked`.
- **Cause:** Another instance of the application is running, or a background process is holding the database file.
- **Resolution:**
  1. Open Windows Task Manager (`Ctrl + Shift + Esc`).
  2. End any running `SrivaniBookingManager.exe` or `python.exe` processes.
  3. Re-launch the application.

### Issue 2: Admin Account Locked (5 Consecutive Failed Logins)
- **Symptom:** Login screen reports `Account temporarily locked due to multiple failed attempts`.
- **Resolution:**
  1. Wait 5 minutes for the lockout timer to expire automatically.
  2. If the master password has been forgotten, restore a recent verified backup taken before the password change, or contact support with proof of ownership.

### Issue 3: "License Expired" or "Evaluation Period Ended"
- **Symptom:** Amber/Red banner appears at the top of the dashboard.
- **Explanation:** The 30-day evaluation has concluded.
- **Safety Guarantee:** Your data is completely safe and intact. The software operates in safe read-only/grace mode.
- **Resolution:**
  1. Click the **Activate / Renew Key** button on the banner.
  2. Copy your Installation ID and request a commercial renewal key from vendor support.
  3. Enter the key to instantly restore full commercial status.

### Issue 4: Missing Ticket PDF File
- **Symptom:** Clicking a ticket link reports `PDF file not found on disk`.
- **Cause:** The PDF file was moved or deleted from the tickets folder outside the application.
- **Resolution:**
  1. In the Queue table, right-click the family and select **📄 Manage Ticket PDF**.
  2. Re-import the downloaded ticket PDF from your browser downloads folder.
  3. The software will verify the SHA-256 hash and restore the file link.

### Issue 5: Safe Rollback After Interrupted Migration
- **Symptom:** Schema update was interrupted by a power failure or crash.
- **Resolution:**
  1. The software automatically takes an atomic snapshot named `srivani_pre_update_vX_*.db` before every migration.
  2. Navigate to **💾 Backup & Recovery**.
  3. Select the pre-update snapshot and click **Restore Selected Backup**.
  4. The database is restored to the exact pre-migration state.
