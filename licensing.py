"""
SRIVANI BOOKING MANAGER - Commercial Client Licensing Engine
Provides offline cryptographic license key validation, machine-bound Installation IDs,
trial activation, license recovery, and an activation UI dialog.
Strictly offline: Does not transmit device information over the network.
Non-destructive: Expired state operates safely in grace/read-only mode.
"""
import sys
import os
import hmac
import hashlib
import uuid
import platform
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tkinter as tk
from tkinter import ttk, messagebox

from config import DB_PATH
from database import get_connection
from logger import get_logger

logger = get_logger("licensing")

VENDOR_SECRET = b"SRIVANI-COMMERCIAL-SECURE-VENDOR-KEY-2026-RELEASE"
TRIAL_DAYS = 30

def get_installation_id() -> str:
    """
    Generate a stable, unique Installation ID for the current machine.
    Uses Windows MachineGuid from the registry when available,
    falling back to salted hardware MAC address and hostname.
    Format: SRVN-XXXX-XXXX-XXXX (16 chars)
    """
    raw_id = ""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )
            raw_id, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
        except Exception:
            pass

    if not raw_id:
        # Fallback to hardware MAC + node name
        raw_id = f"{uuid.getnode()}-{platform.node()}-{platform.machine()}"

    h = hashlib.sha256(f"SRIVANI-INSTALL-SALT-{raw_id}".encode("utf-8")).hexdigest().upper()
    return f"SRVN-{h[0:4]}-{h[4:8]}-{h[8:12]}"

def init_licensing_db(db_path: Optional[Path] = None):
    """Ensure the license_info table exists with appropriate schema."""
    with get_connection(db_path) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS license_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT NOT NULL,
            license_type TEXT NOT NULL,
            client_name TEXT NOT NULL,
            installation_id TEXT NOT NULL,
            issued_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            activated_at TEXT NOT NULL,
            status TEXT NOT NULL
        );
        """)
        con.commit()

def generate_license_key(
    client_name: str,
    installation_id: str = "ANY",
    expiry_date: str = "PERPETUAL",
    tier: str = "COMMERCIAL",
) -> str:
    """
    Generate a cryptographically signed commercial license key.
    Format: SRVN-XXXX-XXXX-XXXX-XXXX
    """
    norm_client = client_name.strip().upper()
    norm_id = installation_id.strip().upper()
    norm_exp = expiry_date.strip().upper()
    norm_tier = tier.strip().upper()

    payload = f"{norm_client}|{norm_id}|{norm_exp}|{norm_tier}".encode("utf-8")
    sig = hmac.new(VENDOR_SECRET, payload, hashlib.sha256).hexdigest().upper()

    # Create 16-character payload digest (4 blocks of 4)
    # Block 1: Type prefix (COMMERCIAL=C, TRIAL=T, PERPETUAL=P) + first 3 chars
    prefix_char = "P" if norm_exp == "PERPETUAL" else ("T" if norm_tier == "TRIAL" else "C")
    block1 = f"{prefix_char}{sig[0:3]}"
    block2 = sig[3:7]
    block3 = sig[7:11]
    block4 = sig[11:15]

    return f"SRVN-{block1}-{block2}-{block3}-{block4}"

def verify_license_key(
    license_key: str,
    client_name: str,
    installation_id: Optional[str] = None,
    expected_expiry: str = "PERPETUAL",
    tier: str = "COMMERCIAL",
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verify a license key against the given client name and current Installation ID.
    Supports both machine-bound keys and site-wide (ANY) keys.
    """
    key = license_key.strip().upper()
    client = client_name.strip().upper()
    current_inst_id = (installation_id or get_installation_id()).strip().upper()

    if not key.startswith("SRVN-") or len(key) != 24:
        return False, "Invalid license key format. Key must be in format: SRVN-XXXX-XXXX-XXXX-XXXX", {}

    # 1. Test bound to current machine
    key_bound = generate_license_key(client, current_inst_id, expected_expiry, tier)
    if key == key_bound:
        return True, "Valid machine-bound commercial license.", {
            "license_key": key,
            "client_name": client,
            "installation_id": current_inst_id,
            "expiry_date": expected_expiry,
            "tier": tier,
            "is_machine_bound": True,
        }

    # 2. Test site-wide (ANY)
    key_any = generate_license_key(client, "ANY", expected_expiry, tier)
    if key == key_any:
        return True, "Valid multi-seat commercial license.", {
            "license_key": key,
            "client_name": client,
            "installation_id": "ANY",
            "expiry_date": expected_expiry,
            "tier": tier,
            "is_machine_bound": False,
        }

    # 3. Check if key matches with a 1-year date format (YYYY-MM-DD)
    # Check if key starts with standard commercial prefix
    return False, "License key signature does not match the provided Client Name or Installation ID.", {}

def activate_license(
    license_key: str,
    client_name: str,
    expiry_date: str = "PERPETUAL",
    tier: str = "COMMERCIAL",
    db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Validate and persist license activation into SQLite."""
    init_licensing_db(db_path)
    current_id = get_installation_id()

    # Try verifying with given expiry, or check trial/commercial
    ok, msg, details = verify_license_key(license_key, client_name, current_id, expiry_date, tier)
    if not ok:
        # Also check with PERPETUAL if user gave a date or vice-versa
        ok, msg, details = verify_license_key(license_key, client_name, current_id, "PERPETUAL", tier)

    if not ok:
        return False, msg

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection(db_path) as con:
        # Deactivate any previous licenses
        con.execute("UPDATE license_info SET status = 'SUPERSEDED' WHERE status = 'ACTIVE'")
        con.execute("""
        INSERT INTO license_info (
            license_key, license_type, client_name, installation_id,
            issued_date, expiry_date, activated_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (
            details["license_key"],
            details["tier"],
            details["client_name"],
            current_id,
            now_str[:10],
            details["expiry_date"],
            now_str,
        ))
        con.commit()

    logger.info(f"Commercial license successfully activated for: {client_name}")
    return True, "Commercial license activated successfully!"

def activate_trial_license(
    client_name: str = "Evaluation User",
    days: int = TRIAL_DAYS,
    db_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """Activate an offline 30-day evaluation license on this machine."""
    init_licensing_db(db_path)
    current_id = get_installation_id()
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    exp_date = (now + datetime.timedelta(days=days)).strftime("%Y-%m-%d")

    # Generate valid trial key for this machine
    trial_key = generate_license_key(client_name, current_id, exp_date, "TRIAL")

    with get_connection(db_path) as con:
        con.execute("UPDATE license_info SET status = 'SUPERSEDED' WHERE status = 'ACTIVE'")
        con.execute("""
        INSERT INTO license_info (
            license_key, license_type, client_name, installation_id,
            issued_date, expiry_date, activated_at, status
        ) VALUES (?, 'TRIAL', ?, ?, ?, ?, ?, 'ACTIVE')
        """, (trial_key, client_name, current_id, now_str[:10], exp_date, now_str))
        con.commit()

    logger.info(f"Trial license activated for {days} days on machine {current_id}")
    return True, f"Evaluation license activated! Valid for {days} days until {exp_date}."

def get_license_info(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieve current license details and operational status."""
    init_licensing_db(db_path)
    current_inst_id = get_installation_id()

    with get_connection(db_path) as con:
        row = con.execute("""
        SELECT license_key, license_type, client_name, installation_id,
               issued_date, expiry_date, activated_at, status
        FROM license_info
        WHERE status = 'ACTIVE'
        ORDER BY id DESC LIMIT 1
        """).fetchone()

        if not row:
            return {
                "is_licensed": False,
                "status": "UNLICENSED",
                "license_type": "NONE",
                "client_name": "Unregistered Installation",
                "installation_id": current_inst_id,
                "license_key": "None",
                "expiry_date": "N/A",
                "days_remaining": 0,
                "is_expired": False,
            }

        rec = dict(row)
        expiry_str = rec["expiry_date"]
        is_perpetual = (expiry_str.upper() == "PERPETUAL")
        is_expired = False
        days_remaining = 9999

        if not is_perpetual:
            try:
                exp_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d").date()
                today = datetime.date.today()
                delta = (exp_date - today).days
                days_remaining = max(0, delta)
                if delta < 0:
                    is_expired = True
            except ValueError:
                pass

        status_str = "EXPIRED" if is_expired else "ACTIVE"
        is_warning_period = (not is_expired and not is_perpetual and days_remaining <= 14)
        
        warning_msg = ""
        if is_expired:
            warning_msg = (
                f"License Expired: The license for '{rec['client_name']}' expired on {expiry_str}. "
                "Operating in safe read-only/grace mode. Donor data remains preserved."
            )
        elif is_warning_period:
            warning_msg = (
                f"License Expiry Notice: {days_remaining} day(s) remaining until expiry ({expiry_str}). "
                "Please contact support to renew your license."
            )

        return {
            "is_licensed": not is_expired,
            "status": status_str,
            "license_type": rec["license_type"],
            "client_name": rec["client_name"],
            "installation_id": current_inst_id,
            "license_key": rec["license_key"],
            "expiry_date": expiry_str,
            "days_remaining": days_remaining,
            "is_expired": is_expired,
            "is_warning_period": is_warning_period,
            "warning_message": warning_msg,
            "activated_at": rec["activated_at"],
        }

def is_licensed(db_path: Optional[Path] = None) -> bool:
    """Check if the application has an active, unexpired license or trial."""
    info = get_license_info(db_path)
    return info["is_licensed"]

def recover_license_details(db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve preserved license record for disaster recovery or migration."""
    info = get_license_info(db_path)
    if info["status"] in ("ACTIVE", "EXPIRED", "DEACTIVATED", "TRANSFERRED"):
        return info
    return None

def export_license_certificate(output_path: Path, db_path: Optional[Path] = None) -> Path:
    """
    Export an official plaintext License Certificate / Receipt for client records.
    Provides verified installation details, license key, and transfer policy.
    """
    info = get_license_info(db_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    cert_text = [
        "================================================================================",
        "               SRIVANI BOOKING MANAGER — CLIENT LICENSE CERTIFICATE             ",
        "================================================================================",
        f"Generated At:       {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Client Name:        {info.get('client_name', 'N/A')}",
        f"Installation ID:    {info.get('installation_id', 'N/A')}",
        f"License Key:        {info.get('license_key', 'N/A')}",
        f"License Tier:       {info.get('license_type', 'N/A')}",
        f"License Status:     {info.get('status', 'N/A')}",
        f"Activation Date:    {info.get('activated_at', 'N/A')}",
        f"Expiry Date:        {info.get('expiry_date', 'N/A')}",
        f"Days Remaining:     {info.get('days_remaining', 'N/A')}",
        "--------------------------------------------------------------------------------",
        "LICENSE CONDITIONS & DEVICE TRANSFER POLICY:",
        "1. Single-installation license bound to the verified hardware Installation ID.",
        "2. To transfer this license to a new PC, use the in-app 'Deactivate for Transfer'",
        "   feature or contact vendor customer support with this Certificate.",
        "3. This software operates as an assisted workflow booking management tool.",
        "4. Official TTD login, CAPTCHA, and payments remain under manual client control.",
        "================================================================================",
        "SUPPORT CONTACT:",
        "Email: support@srivani-booking-manager.local",
        "Portal: https://ttdevasthanams.ap.gov.in (Official Devasthanams Booking)",
        "================================================================================",
    ]
    out.write_text("\n".join(cert_text), encoding="utf-8")
    return out

def deactivate_license_for_transfer(db_path: Optional[Path] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Deactivate the license on the current machine to permit transfer to another device.
    Generates a cryptographically signed Deactivation Proof receipt.
    Does NOT delete or harm any pilgrim or booking data.
    """
    info = get_license_info(db_path)
    if not info.get("is_licensed") and info.get("status") not in ("ACTIVE", "EXPIRED"):
        return False, "No active license found to deactivate.", {}

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_name = info.get("client_name", "UNKNOWN")
    inst_id = info.get("installation_id", get_installation_id())
    lic_key = info.get("license_key", "UNKNOWN")

    # Generate signed Deactivation Proof token
    proof_payload = f"{client_name}|{inst_id}|{lic_key}|DEACTIVATED|{now_str}".encode("utf-8")
    proof_sig = hmac.new(VENDOR_SECRET, proof_payload, hashlib.sha256).hexdigest().upper()
    proof_code = f"DEACT-{proof_sig[:4]}-{proof_sig[4:8]}-{proof_sig[8:12]}-{proof_sig[12:16]}"

    with get_connection(db_path) as con:
        con.execute("""
        UPDATE license_info
        SET status = 'TRANSFERRED'
        WHERE status = 'ACTIVE'
        """)
        con.commit()

    logger.info(f"License deactivated for transfer: Client '{client_name}', Proof: {proof_code}")

    details = {
        "client_name": client_name,
        "old_installation_id": inst_id,
        "license_key": lic_key,
        "deactivated_at": now_str,
        "deactivation_proof": proof_code,
    }
    return True, f"License deactivated successfully. Deactivation Proof: {proof_code}", details

# ---------------------------------------------------------
# License Activation Dialog (Tkinter)
# ---------------------------------------------------------

class LicenseActivationDialog(tk.Toplevel):
    """
    User-friendly modal dialog for entering commercial license keys,
    copying Installation ID, or launching evaluation mode.
    """

    def __init__(self, parent, db_path: Optional[Path] = None, on_success=None):
        super().__init__(parent)
        self.db_path = db_path
        self.on_success = on_success
        self.success = False

        self.title("Client License Activation — SRIVANI BOOKING MANAGER")
        self.geometry("540x480")
        self.minsize(500, 440)
        self.resizable(False, False)
        self.configure(bg="#f8fafc")

        self.transient(parent)
        self.grab_set()

        self.inst_id = get_installation_id()
        self.lic_info = get_license_info(self.db_path)

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self, bg="#1e293b", padx=20, pady=14)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="🔑 Software License & Activation",
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Activate your commercial license or begin an offline 30-day evaluation.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(3, 0))

        # Body form
        body = tk.Frame(self, bg="#f8fafc", padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        # Installation ID block
        tk.Label(body, text="Your Machine Installation ID:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=0, column=0, sticky="w", pady=(2, 2))

        id_box = tk.Frame(body, bg="#f8fafc")
        id_box.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ent_id = ttk.Entry(id_box, font=("Segoe UI", 10, "bold"), width=28)
        ent_id.insert(0, self.inst_id)
        ent_id.config(state="readonly")
        ent_id.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        btn_copy = tk.Button(
            id_box,
            text="📋 Copy ID",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            relief="flat",
            padx=10,
            pady=3,
            command=self._copy_inst_id,
        )
        btn_copy.pack(side=tk.RIGHT)

        tk.Label(body, text="Provide this Installation ID to your software provider to receive your license key.", font=("Segoe UI", 8), fg="#64748b", bg="#f8fafc").grid(row=2, column=0, sticky="w", pady=(0, 12))

        # Client / Organization Name
        tk.Label(body, text="Client / Organization Name:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=3, column=0, sticky="w", pady=(2, 2))
        self.ent_client = ttk.Entry(body, font=("Segoe UI", 10), width=38)
        self.ent_client.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        if self.lic_info["client_name"] != "Unregistered Installation":
            self.ent_client.insert(0, self.lic_info["client_name"])

        # License Key
        tk.Label(body, text="Commercial License Key (format: SRVN-XXXX-XXXX-XXXX-XXXX):", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=5, column=0, sticky="w", pady=(2, 2))
        self.ent_key = ttk.Entry(body, font=("Segoe UI", 10), width=38)
        self.ent_key.grid(row=6, column=0, sticky="ew", pady=(0, 6))
        if self.lic_info["license_key"] != "None":
            self.ent_key.insert(0, self.lic_info["license_key"])

        self.lbl_msg = tk.Label(body, text="", font=("Segoe UI", 8), fg="#dc2626", bg="#f8fafc", wraplength=440, justify=tk.LEFT)
        self.lbl_msg.grid(row=7, column=0, sticky="w", pady=(2, 6))

        # Action Buttons
        btn_bar = tk.Frame(self, bg="#f1f5f9", padx=20, pady=12)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        btn_trial = tk.Button(
            btn_bar,
            text="⏱️ Start 30-Day Evaluation",
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#1e293b",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._on_trial,
        )
        btn_trial.pack(side=tk.LEFT)

        btn_activate = tk.Button(
            btn_bar,
            text="✨ Activate License",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_activate,
        )
        btn_activate.pack(side=tk.RIGHT)

    def _copy_inst_id(self):
        self.clipboard_clear()
        self.clipboard_append(self.inst_id)
        messagebox.showinfo("Copied", f"Installation ID copied to clipboard:\n{self.inst_id}", parent=self)

    def _on_activate(self):
        client = self.ent_client.get().strip()
        key = self.ent_key.get().strip()

        if not client or not key:
            self.lbl_msg.config(text="Please enter both Client Name and License Key.", fg="#dc2626")
            return

        ok, msg = activate_license(key, client, db_path=self.db_path)
        if ok:
            self.success = True
            messagebox.showinfo("Activation Successful", msg, parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            self.lbl_msg.config(text=msg, fg="#dc2626")

    def _on_trial(self):
        client = self.ent_client.get().strip() or "Evaluation User"
        ok, msg = activate_trial_license(client, days=30, db_path=self.db_path)
        if ok:
            self.success = True
            messagebox.showinfo("Trial Activated", msg, parent=self)
            if self.on_success:
                self.on_success()
            self.destroy()
        else:
            self.lbl_msg.config(text=msg, fg="#dc2626")
