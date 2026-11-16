"""
SRIVANI BOOKING MANAGER - Vendor License Key Generator
Utility for software vendor/distributor to issue cryptographically signed
client license keys for commercial deployments.
"""
import sys
import argparse
from licensing import generate_license_key, get_installation_id

def issue_license(client_name: str, installation_id: str = "ANY", expiry: str = "PERPETUAL", tier: str = "COMMERCIAL"):
    key = generate_license_key(client_name, installation_id, expiry, tier)
    print("\n==========================================================")
    print("      SRIVANI BOOKING MANAGER - COMMERCIAL LICENSE KEY")
    print("==========================================================")
    print(f"Client / Organization : {client_name.strip().upper()}")
    print(f"Installation ID       : {installation_id.strip().upper()}")
    print(f"License Tier          : {tier.strip().upper()}")
    print(f"Validity / Expiry     : {expiry.strip().upper()}")
    print("----------------------------------------------------------")
    print(f"LICENSE KEY           : {key}")
    print("==========================================================\n")
    print("Activation Instructions for Client:")
    print("1. Launch SRIVANI BOOKING MANAGER.")
    print("2. Navigate to Preferences (or First-Run Setup Wizard).")
    print(f"3. Enter Client Name exactly as: {client_name.strip().upper()}")
    print(f"4. Enter License Key: {key}")
    print("5. Click 'Activate License'.\n")
    return key

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate commercial license key for SRIVANI BOOKING MANAGER.")
    parser.add_argument("--client", "-c", type=str, default="TIRUMALA PILGRIM SERVICES", help="Client / Organization name")
    parser.add_argument("--inst-id", "-i", type=str, default="ANY", help="Installation ID (or 'ANY' for multi-seat)")
    parser.add_argument("--expiry", "-e", type=str, default="PERPETUAL", help="Expiry date (YYYY-MM-DD or 'PERPETUAL')")
    parser.add_argument("--tier", "-t", type=str, default="COMMERCIAL", help="License tier ('COMMERCIAL' or 'TRIAL')")

    args = parser.parse_args()
    issue_license(args.client, args.inst_id, args.expiry, args.tier)
