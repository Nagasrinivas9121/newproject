# CLIENT ACCEPTANCE & SIGN-OFF CHECKLIST

**Client Name:** __________________________________________________  
**Installation ID:** ______________________________________________  
**Software Version:** SRIVANI Booking Manager v6.0.0 Commercial Release  
**Deployment Date:** _____________________________________________  

---

### FUNCTIONAL VERIFICATION & ACCEPTANCE CRITERIA

| No. | Module / Feature | Acceptance Test Description | Result |
| :---: | :--- | :--- | :---: |
| 1 | **Dashboard & Queue** | Dashboard summary cards calculate correct counts; queue ordering respects priority (Urgent > High > Normal). | [ ] PASS / [ ] FAIL |
| 2 | **Excel / CSV Import** | Spreadsheet import correctly parses family contacts and devotee lists with preview and duplicate skipping. | [ ] PASS / [ ] FAIL |
| 3 | **Family Management** | Ability to add, edit, delete families and manage multiple pilgrims per family. | [ ] PASS / [ ] FAIL |
| 4 | **Assisted Workspace** | 7-Step assisted booking checklist displays correctly; one-click copy buttons copy devotee details. | [ ] PASS / [ ] FAIL |
| 5 | **Official TTD Access** | "Open TTD Portal" button opens external browser at `https://ttdevasthanams.ap.gov.in`. Manual login confirmed. | [ ] PASS / [ ] FAIL |
| 6 | **Ticket PDF Storage** | Ticket PDFs successfully imported, organized, verified by SHA-256 hash, and opened in default PDF viewer. | [ ] PASS / [ ] FAIL |
| 7 | **Payment Tracking** | Payment status (Pending, Paid, Failed, Refunded) and transaction references recorded accurately. | [ ] PASS / [ ] FAIL |
| 8 | **Queue History** | All family status changes and priority modifications logged chronologically in audit history. | [ ] PASS / [ ] FAIL |
| 9 | **Reports & Export** | Daily, weekly, status, and payment reports generated; printable PDF export verified against database totals. | [ ] PASS / [ ] FAIL |
| 10 | **Security & Auth** | Single-admin password protected with salted bcrypt; session locking and lockout work as expected. | [ ] PASS / [ ] FAIL |
| 11 | **Backup & Recovery** | Full online SQLite backup created, verified, and test restoration completed successfully. | [ ] PASS / [ ] FAIL |
| 12 | **Client Licensing** | Machine-bound license key activated; certificate exported; expiry warning displayed accurately. | [ ] PASS / [ ] FAIL |
| 13 | **Customer Support** | Support helpdesk information and sanitized non-PII diagnostic report export verified. | [ ] PASS / [ ] FAIL |
| 14 | **Compliance Guarantee** | Confirmed: Zero TTD credentials, OTPs, or banking details stored or requested by the software. | [ ] PASS / [ ] FAIL |

---

### ACCEPTANCE SIGN-OFF

The undersigned client representative confirms that the SRIVANI Booking Manager software has been successfully installed, configured, tested, and accepted for operational deployment.

**Client Authorized Representative:**  
Name: __________________________________________________  
Title: ___________________________________________________  
Signature: _______________________________________________  
Date: ___________________________________________________  

**Vendor Release Engineer:**  
Name: __________________________________________________  
Signature: _______________________________________________  
Date: ___________________________________________________  
