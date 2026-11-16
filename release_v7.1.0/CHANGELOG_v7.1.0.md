# SRIVANI BOOKING MANAGER — Changelog v7.1.0

## Release Summary
**Version:** 7.1.0 Commercial Production Suite  
**Release Date:** 2026-11-16  
**Type:** Production Maintenance, Bug Fixes & Windows Release Package  

---

### Key Bug Fixes in v7.1.0

1. **Dataset Import Column Aliasing (Fix #1)**:
   - Added support for `"yatri full name"` and `"yatri"` to `COLUMN_ALIASES["full_name"]` in `dataset_importer.py`.
   - Added support for `"contact mobile"` in `COLUMN_ALIASES["phone"]`.
   - Solved header mapping mismatches on non-standard client devotee spreadsheets.

2. **Duplicate Family Prevention Under SKIP Policy (Fix #2)**:
   - Fixed `execute_dataset_import()` in `dataset_importer.py`.
   - When importing a spreadsheet containing new pilgrims for an existing family under `DUP_POLICY_SKIP`, the system now reuses `family_id = db_fid` instead of inserting an unnecessary duplicate family record into `families`.

3. **Document Readiness AttributeError Prevention (Fix #3)**:
   - Fixed `database.py:assess_document_readiness()`.
   - Safely converts `sqlite3.Row` instances to dictionaries and validates mappings without invoking `.get()` directly on `sqlite3.Row`.
   - Handles `sqlite3.Row`, dictionary records, empty lists, and records with missing optional fields.

4. **Family Code Collision Prevention in Bulk Ingestion**:
   - Upgraded `generate_family_code()` to use 8-hex-character randomness (`uuid.uuid4().hex[:8].upper()`), preventing collisions in high-speed bulk ingestion (100+ families per second).

5. **Packaging & Executable Updates**:
   - Re-compiled standalone Windows executable via PyInstaller 6.22 with updated hidden imports for Phase 8, Phase 9, and Phase 10 modules.
   - Built fresh Inno Setup 6 installer: `SrivaniBookingManager_Setup_v7.1.0.exe` (22.7 MB).
   - Created portable production zip archive: `SrivaniBookingManager_v7.1.0_Portable.zip` (27.8 MB).

---

### Automated Testing
- **Total Tests Collected:** 124 tests across 17 test modules.
- **Pass Rate:** **100% (124 Passed, 0 Failed)**.
- **End-to-End Suite:** 14/14 stages passed cleanly in `run_end_to_end.py`.
