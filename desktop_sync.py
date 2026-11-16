#!/usr/bin/env python3
"""
SRIVANI BOOKING MANAGER - PHASE 8
Desktop to Cloud SaaS Migration and Synchronization Layer

Enables seamless, audited, non-destructive migration of local desktop SQLite records
into the multi-tenant SaaS cloud platform.
"""

import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple
import requests


class DesktopMigrator:
    """Manages the extraction, validation, and secure transmission of local client records."""

    def __init__(self, local_db_path: str = "./data/srivani_manager.db"):
        self.local_db_path = os.path.abspath(local_db_path)

    def verify_local_database(self) -> Tuple[bool, str, Dict[str, int]]:
        """Audit the local database structure and verify record counts and referential integrity."""
        if not os.path.exists(self.local_db_path):
            return False, f"Database file not found at: {self.local_db_path}", {}

        conn = sqlite3.connect(self.local_db_path)
        cur = conn.cursor()

        try:
            # Check families count
            cur.execute("SELECT count(*) FROM families")
            fam_count = cur.fetchone()[0]

            # Check pilgrims count
            cur.execute("SELECT count(*) FROM pilgrims")
            pil_count = cur.fetchone()[0]

            # Check orphaned pilgrims
            cur.execute(
                "SELECT count(*) FROM pilgrims WHERE family_id NOT IN (SELECT id FROM families)"
            )
            orphaned = cur.fetchone()[0]
            if orphaned > 0:
                conn.close()
                return False, f"Referential integrity error: Found {orphaned} orphaned pilgrim records.", {}

            conn.close()
            return True, "Integrity verified successfully.", {
                "families_count": fam_count,
                "pilgrims_count": pil_count,
                "orphaned_count": orphaned,
            }
        except Exception as e:
            conn.close()
            return False, f"Database read error: {e}", {}

    def extract_records(self) -> Dict[str, Any]:
        """Extract and structure families and pilgrims from local SQLite database."""
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM families ORDER BY id ASC")
        family_rows = cur.fetchall()

        families_payload = []
        total_pilgrims = 0

        for f in family_rows:
            f_dict = dict(f)
            fam_id = f_dict["id"]

            cur.execute("SELECT * FROM pilgrims WHERE family_id = ? ORDER BY id ASC", (fam_id,))
            pil_rows = cur.fetchall()

            pilgrims_list = []
            for p in pil_rows:
                p_dict = dict(p)
                pilgrims_list.append({
                    "name": p_dict.get("name", "Unknown"),
                    "age": int(p_dict.get("age", 0)),
                    "gender": p_dict.get("gender", "Male"),
                    "id_type": p_dict.get("id_type", "Aadhaar"),
                    "id_number": p_dict.get("id_number", "XXXX"),
                    "desktop_source_id": p_dict.get("id"),
                })
                total_pilgrims += 1

            families_payload.append({
                "desktop_source_id": f_dict["id"],
                "family_id_str": f_dict.get("family_id", f"FAM-{f_dict['id']}"),
                "head_name": f_dict.get("head_name", "Primary Devotee"),
                "contact_number": f_dict.get("contact_number", ""),
                "email": f_dict.get("email"),
                "city": f_dict.get("city"),
                "state": f_dict.get("state"),
                "preferred_date": f_dict.get("preferred_date"),
                "priority": f_dict.get("priority", "Normal"),
                "status": f_dict.get("status", "Pending"),
                "donation_amount": float(f_dict.get("donation_amount", 0.0) or 0.0),
                "payment_status": f_dict.get("payment_status", "Pending"),
                "payment_reference": f_dict.get("payment_reference"),
                "notes": f_dict.get("notes"),
                "pilgrims": pilgrims_list,
            })

        conn.close()

        # Compute payload checksum
        raw_json = json.dumps(families_payload, sort_keys=True)
        checksum = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

        return {
            "source_app": "SRIVANI BOOKING MANAGER Desktop",
            "client_version": "7.0.0",
            "families_count": len(families_payload),
            "pilgrims_count": total_pilgrims,
            "checksum": checksum,
            "families": families_payload,
        }

    def export_to_file(self, output_path: str) -> Tuple[bool, str]:
        """Export local records to an audited JSON migration archive."""
        valid, msg, counts = self.verify_local_database()
        if not valid:
            return False, msg

        payload = self.extract_records()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return True, f"Successfully exported {payload['families_count']} families and {payload['pilgrims_count']} devotees to {output_path}"

    def upload_to_saas(
        self,
        server_url: str,
        token: str,
    ) -> Dict[str, Any]:
        """Upload validated records directly to cloud tenant via authenticated REST API."""
        valid, msg, counts = self.verify_local_database()
        if not valid:
            return {"success": False, "error": msg}

        payload = self.extract_records()
        endpoint = f"{server_url.rstrip('/')}/api/v1/sync/import-desktop"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "server_response": data,
                    "reconciliation": {
                        "local_families": payload["families_count"],
                        "local_pilgrims": payload["pilgrims_count"],
                        "imported_families": data.get("imported_families", 0),
                        "imported_pilgrims": data.get("imported_pilgrims", 0),
                        "skipped_duplicates": data.get("skipped_duplicates", 0),
                    },
                }
            else:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="SRIVANI Desktop-to-SaaS Migration Tool")
    parser.add_argument("--db", default="./data/srivani_manager.db", help="Path to local SQLite DB")
    parser.add_argument("--action", choices=["verify", "export", "sync"], required=True)
    parser.add_argument("--output", default="./data/desktop_migration_export.json", help="Path for JSON export")
    parser.add_argument("--server", default="http://localhost:8000", help="SaaS Server URL")
    parser.add_argument("--token", help="Bearer authentication token for tenant")

    args = parser.parse_args()
    migrator = DesktopMigrator(args.db)

    if args.action == "verify":
        valid, msg, stats = migrator.verify_local_database()
        print("Database Audit Status:", "PASSED" if valid else "FAILED")
        print("Message:", msg)
        print("Record Stats:", json.dumps(stats, indent=2))
        sys.exit(0 if valid else 1)

    elif args.action == "export":
        success, msg = migrator.export_to_file(args.output)
        print(msg)
        sys.exit(0 if success else 1)

    elif args.action == "sync":
        if not args.token:
            print("Error: --token is required for cloud synchronization.")
            sys.exit(1)
        res = migrator.upload_to_saas(args.server, args.token)
        print("Sync Result:", json.dumps(res, indent=2))
        sys.exit(0 if res.get("success") else 1)


if __name__ == "__main__":
    main()
