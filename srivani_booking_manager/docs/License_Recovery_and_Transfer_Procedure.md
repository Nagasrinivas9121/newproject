# LICENSE RECOVERY AND HARDWARE DEVICE TRANSFER PROCEDURE

## 1. Overview
The commercial license for SRIVANI Booking Manager is bound to a single physical workstation using a salted hardware Installation ID (`SRVN-XXXX-XXXX-XXXX`). 

When an organization upgrades, replaces, or repairs a computer, the license can be smoothly transferred to the new machine without losing any donor data or ticket records.

---

## 2. Pre-Transfer Checklist
Before transferring or decommissioning the existing computer:
1. **Take a Full Database Backup:**
   - In the application, navigate to **💾 Backup & Recovery**.
   - Click **💾 Create Backup Now**.
   - Copy the generated `.db` backup file from `%LOCALAPPDATA%\SrivaniBookingManager\backups` to a secure USB drive or network share.
2. **Back Up Your Ticket PDFs:**
   - Copy the entire `%LOCALAPPDATA%\SrivaniBookingManager\tickets` folder to your backup storage.

---

## 3. Method A: Deactivate for Transfer (Recommended)
1. On the **old computer**, launch SRIVANI Booking Manager and log in.
2. Click **⚙️ Preferences & About** on the bottom sidebar.
3. Open the **🔑 Client Licensing** tab.
4. Click **🔄 Deactivate for Transfer...**.
5. Read and confirm the dialog prompt. The application will:
   - Mark the license status as `TRANSFERRED`.
   - Leave all donor and booking records completely intact.
   - Generate a signed **Deactivation Proof Code** (e.g., `DEACT-XXXX-XXXX-XXXX-XXXX`).
6. Record or screenshot this Deactivation Proof Code.

---

## 4. Method B: License Certificate Recovery
If the old computer suffered an unexpected operating system failure or hardware crash:
1. Locate the **License Certificate** exported during initial onboarding (`srivani_license_certificate_*.txt`), or find your original purchase invoice / commercial key.
2. Email vendor customer support (`support@srivani-booking-manager.local`) with:
   - Your Registered Client / Organization Name.
   - Old Installation ID or Commercial Key.
   - Deactivation Proof Code (if Method A was used).

---

## 5. Activating on the New Workstation
1. Install SRIVANI Booking Manager on the new computer using `SrivaniBookingManager_Setup_v6.0.0.exe`.
2. Launch the application to find the new machine's **Installation ID**.
3. Send the new Installation ID to vendor support (or enter the replacement key provided by vendor support).
4. In the application, click **✨ Enter / Activate Commercial Key...** and enter the new key.
5. In **💾 Backup & Recovery**, restore your database snapshot to instantly restore all family and pilgrim records.
6. Copy your ticket PDFs into the new machine's ticket directory.
7. Verification complete — you are back in business!
