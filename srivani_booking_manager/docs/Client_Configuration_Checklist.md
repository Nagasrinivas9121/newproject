# CLIENT CONFIGURATION CHECKLIST

Use this checklist during client deployment to verify that all installation, security, and storage settings are correctly established.

| Category | Item | Verification Steps | Status |
| :--- | :--- | :--- | :---: |
| **System** | Windows Version | Windows 10 (64-bit) or Windows 11 verified. | [ ] |
| **System** | Display Scaling | Application text and icons render cleanly at client's resolution. | [ ] |
| **Installer** | Shortcuts | Desktop icon and Start Menu program group operational. | [ ] |
| **Security** | Master Admin | Master administrator password configured (minimum 8 characters). | [ ] |
| **Security** | Brute-force Lockout | 5-attempt brute-force protection active. | [ ] |
| **Security** | Session Timeout | Inactivity auto-lock configured (default 30 mins). | [ ] |
| **Licensing** | Hardware Binding | Installation ID matches physical PC (`SRVN-XXXX-XXXX-XXXX`). | [ ] |
| **Licensing** | Commercial Key | Commercial license activated or 30-day evaluation active. | [ ] |
| **Storage** | Database Path | SQLite database writable in `%LOCALAPPDATA%\SrivaniBookingManager`. | [ ] |
| **Storage** | Ticket Directory | Ticket PDF storage directory writable (`tickets/`). | [ ] |
| **Storage** | Backup Directory | Backup directory writable (`backups/`). | [ ] |
| **Storage** | Free Disk Space | At least 2 GB free disk space on storage drive. | [ ] |
| **Assisted Portal** | Browser Link | "Open TTD Portal" successfully launches `https://ttdevasthanams.ap.gov.in`. | [ ] |
| **Compliance** | Zero Credentials | Verified: No TTD passwords, OTPs, or banking PINs stored. | [ ] |
| **Audit** | Health Audit | In-app "Run Environment Audit" reports [PASS] on all checks. | [ ] |

---

**Configured By:** ___________________________  
**Client Sign-off:** ___________________________  
**Date:** ___________________________  
