"""
SRIVANI BOOKING MANAGER - Admin Authentication & Session Management
Provides single-admin authentication, secure password hashing (bcrypt),
account lockout protection, session locking, and first-run wizard dialogs.
"""
import sqlite3
import datetime
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import tkinter as tk
from tkinter import ttk, messagebox

import bcrypt

from config import DB_PATH
from database import get_connection
from logger import get_logger

logger = get_logger("auth")

# Lockout configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 5

def init_auth_db(db_path: Optional[Path] = None):
    """Ensure the admin_users table exists with proper columns and index."""
    with get_connection(db_path) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT DEFAULT 'Administrator',
            created_at TEXT NOT NULL,
            last_login TEXT,
            failed_attempts INTEGER DEFAULT 0,
            locked_until TEXT
        );
        """)
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_username ON admin_users(username);")

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def has_admin_user(db_path: Optional[Path] = None) -> bool:
    """Check if any admin account has been created."""
    init_auth_db(db_path)
    with get_connection(db_path) as con:
        row = con.execute("SELECT COUNT(*) FROM admin_users").fetchone()
        return bool(row and row[0] > 0)

def get_admin_user(username: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve admin user details (excluding password hash) by username."""
    init_auth_db(db_path)
    with get_connection(db_path) as con:
        row = con.execute(
            "SELECT id, username, display_name, created_at, last_login, failed_attempts, locked_until FROM admin_users WHERE username = ?",
            (username.strip(),)
        ).fetchone()
        if row:
            return dict(row)
        return None

def create_admin_user(
    username: str,
    password: str,
    display_name: str = "Administrator",
    db_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """Create a new admin user record. Enforces password strength rules."""
    init_auth_db(db_path)
    username = username.strip()
    display_name = display_name.strip() or "Administrator"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", username):
        return False, "Username can only contain letters, numbers, hyphens, and underscores."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    pwd_hash = hash_password(password)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_connection(db_path) as con:
            con.execute("""
            INSERT INTO admin_users (username, password_hash, display_name, created_at, last_login, failed_attempts)
            VALUES (?, ?, ?, ?, ?, 0)
            """, (username, pwd_hash, display_name, now_str, now_str))
            con.commit()
        logger.info(f"Admin account created successfully for user: {username}")
        return True, "Admin account created successfully."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' already exists."
    except Exception as e:
        logger.error(f"Error creating admin account: {e}")
        return False, f"Database error: {e}"

def authenticate_admin(
    username: str,
    password: str,
    db_path: Optional[Path] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticate an admin user. Handles failed attempt counting and temporary lockouts.
    """
    init_auth_db(db_path)
    username = username.strip()
    if not username or not password:
        return False, "Please provide both username and password.", None

    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    with get_connection(db_path) as con:
        row = con.execute(
            "SELECT id, username, password_hash, display_name, failed_attempts, locked_until FROM admin_users WHERE username = ?",
            (username,)
        ).fetchone()

        if not row:
            logger.warning(f"Failed login attempt: non-existent username '{username}'")
            return False, "Invalid username or password.", None

        # Check if temporarily locked
        locked_until_str = row["locked_until"]
        if locked_until_str:
            try:
                locked_until = datetime.datetime.strptime(locked_until_str, "%Y-%m-%d %H:%M:%S")
                if now < locked_until:
                    remaining_sec = int((locked_until - now).total_seconds())
                    remaining_min = max(1, (remaining_sec + 59) // 60)
                    logger.warning(f"Login blocked: Account '{username}' is locked for {remaining_min} more minute(s).")
                    return False, f"Account is temporarily locked due to multiple failed attempts. Try again in {remaining_min} minute(s).", None
            except ValueError:
                pass  # Corrupt timestamp format, continue

        stored_hash = row["password_hash"]
        if verify_password(password, stored_hash):
            # Reset failed attempts and update last_login
            con.execute(
                "UPDATE admin_users SET failed_attempts = 0, locked_until = NULL, last_login = ? WHERE id = ?",
                (now_str, row["id"])
            )
            con.commit()
            user_info = {
                "id": row["id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "last_login": now_str,
            }
            logger.info(f"Admin login successful: {username}")
            return True, "Login successful.", user_info
        else:
            # Failed attempt
            attempts = (row["failed_attempts"] or 0) + 1
            locked_until_val = None
            msg = "Invalid username or password."

            if attempts >= MAX_FAILED_ATTEMPTS:
                lock_time = now + datetime.timedelta(minutes=LOCKOUT_MINUTES)
                locked_until_val = lock_time.strftime("%Y-%m-%d %H:%M:%S")
                msg = f"Account locked for {LOCKOUT_MINUTES} minutes due to {MAX_FAILED_ATTEMPTS} failed attempts."
                logger.warning(f"Account '{username}' locked until {locked_until_val} due to failed attempts.")
            else:
                remaining = MAX_FAILED_ATTEMPTS - attempts
                msg += f" ({remaining} attempt(s) remaining before temporary lockout)"

            con.execute(
                "UPDATE admin_users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                (attempts, locked_until_val, row["id"])
            )
            con.commit()
            return False, msg, None

def change_admin_password(
    username: str,
    old_password: str,
    new_password: str,
    db_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """Change an admin's password after verifying the old password."""
    init_auth_db(db_path)
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    with get_connection(db_path) as con:
        row = con.execute("SELECT id, password_hash FROM admin_users WHERE username = ?", (username,)).fetchone()
        if not row:
            return False, "Admin user not found."

        if not verify_password(old_password, row["password_hash"]):
            return False, "Current password is incorrect."

        new_hash = hash_password(new_password)
        con.execute("UPDATE admin_users SET password_hash = ? WHERE id = ?", (new_hash, row["id"]))
        con.commit()

    logger.info(f"Password changed successfully for user: {username}")
    return True, "Password updated successfully."

def update_admin_profile(
    username: str,
    display_name: str,
    db_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """Update admin display name."""
    init_auth_db(db_path)
    display_name = display_name.strip()
    if not display_name:
        return False, "Display name cannot be blank."

    with get_connection(db_path) as con:
        con.execute("UPDATE admin_users SET display_name = ? WHERE username = ?", (display_name, username))
        con.commit()
    logger.info(f"Admin profile updated for: {username}")
    return True, "Profile updated successfully."

# ---------------------------------------------------------
# Session State Management
# ---------------------------------------------------------

class AdminSession:
    """Manages runtime admin session state (authentication, lock, active user)."""

    def __init__(self):
        self._authenticated: bool = False
        self._locked: bool = False
        self._current_user: Optional[Dict[str, Any]] = None

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def is_locked(self) -> bool:
        return self._locked

    @property
    def current_user(self) -> Optional[Dict[str, Any]]:
        return self._current_user

    @property
    def display_name(self) -> str:
        if self._current_user:
            return self._current_user.get("display_name", "Admin")
        return "Admin"

    @property
    def username(self) -> str:
        if self._current_user:
            return self._current_user.get("username", "admin")
        return "admin"

    def login(self, user_info: Dict[str, Any]):
        self._authenticated = True
        self._locked = False
        self._current_user = user_info

    def lock(self):
        if self._authenticated:
            self._locked = True
            logger.info("Session locked by administrator.")

    def unlock(self, user_info: Dict[str, Any]):
        if self._authenticated:
            self._locked = False
            self._current_user = user_info
            logger.info("Session unlocked successfully.")

    def logout(self):
        self._authenticated = False
        self._locked = False
        self._current_user = None
        logger.info("Session logged out.")

session = AdminSession()

# ---------------------------------------------------------
# Authentication UI Dialogs (Tkinter)
# ---------------------------------------------------------

class AdminSetupDialog(tk.Toplevel):
    """First-run wizard for creating the initial administrator account."""

    def __init__(self, parent, db_path: Optional[Path] = None, on_success=None):
        super().__init__(parent)
        self.db_path = db_path
        self.on_success = on_success
        self.success = False

        self.title("SRIVANI BOOKING MANAGER - First-Run Admin Setup")
        self.geometry("480x420")
        self.minsize(440, 380)
        self.resizable(False, False)
        self.configure(bg="#f8fafc")

        self.transient(parent)
        self.grab_set()

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
        header = tk.Frame(self, bg="#1e293b", padx=20, pady=16)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="🔐 First-Run Administrator Setup",
            font=("Segoe UI", 13, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Create your primary administrator account to secure this system.",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(4, 0))

        # Form body
        form = tk.Frame(self, bg="#f8fafc", padx=24, pady=16)
        form.pack(fill=tk.BOTH, expand=True)

        tk.Label(form, text="Admin Username:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=0, column=0, sticky="w", pady=(4, 2))
        self.ent_user = ttk.Entry(form, font=("Segoe UI", 10), width=32)
        self.ent_user.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.ent_user.insert(0, "admin")

        tk.Label(form, text="Display Name / Full Name:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=2, column=0, sticky="w", pady=(4, 2))
        self.ent_name = ttk.Entry(form, font=("Segoe UI", 10), width=32)
        self.ent_name.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.ent_name.insert(0, "Administrator")

        tk.Label(form, text="Master Password (min 6 characters):", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=4, column=0, sticky="w", pady=(4, 2))
        self.ent_pwd = ttk.Entry(form, font=("Segoe UI", 10), width=32, show="*")
        self.ent_pwd.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        tk.Label(form, text="Confirm Password:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=6, column=0, sticky="w", pady=(4, 2))
        self.ent_pwd2 = ttk.Entry(form, font=("Segoe UI", 10), width=32, show="*")
        self.ent_pwd2.grid(row=7, column=0, sticky="ew", pady=(0, 10))

        self.lbl_error = tk.Label(form, text="", font=("Segoe UI", 9), fg="#dc2626", bg="#f8fafc", wraplength=400)
        self.lbl_error.grid(row=8, column=0, sticky="w", pady=(2, 6))

        # Action button
        btn_box = tk.Frame(self, bg="#f1f5f9", padx=20, pady=12)
        btn_box.pack(fill=tk.X, side=tk.BOTTOM)

        btn_submit = tk.Button(
            btn_box,
            text="✨ Create Administrator Account & Continue",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_submit,
        )
        btn_submit.pack(fill=tk.X)

        self.ent_pwd2.bind("<Return>", lambda e: self._on_submit())
        self.ent_pwd.focus_set()

    def _on_submit(self):
        user = self.ent_user.get().strip()
        name = self.ent_name.get().strip()
        pwd = self.ent_pwd.get()
        pwd2 = self.ent_pwd2.get()

        if not user or not pwd:
            self.lbl_error.config(text="Please fill in all required fields.")
            return

        if pwd != pwd2:
            self.lbl_error.config(text="Passwords do not match. Please re-enter.")
            return

        success, msg = create_admin_user(user, pwd, name, self.db_path)
        if success:
            self.success = True
            messagebox.showinfo("Setup Complete", "Administrator account created successfully! You may now proceed.", parent=self)
            if self.on_success:
                self.on_success(user, pwd)
            self.destroy()
        else:
            self.lbl_error.config(text=msg)

class LoginDialog(tk.Toplevel):
    """
    Login and Session Unlock dialog.
    Supports startup login, session unlocking, and password visibility toggle.
    """

    def __init__(self, parent, db_path: Optional[Path] = None, is_unlock: bool = False, locked_username: str = ""):
        super().__init__(parent)
        self.db_path = db_path
        self.is_unlock = is_unlock
        self.locked_username = locked_username
        self.authenticated_user: Optional[Dict[str, Any]] = None

        title_text = "Unlock Session - SRIVANI BOOKING MANAGER" if is_unlock else "Admin Login - SRIVANI BOOKING MANAGER"
        self.title(title_text)
        self.geometry("440x360")
        self.minsize(400, 320)
        self.resizable(False, False)
        self.configure(bg="#f8fafc")

        self.transient(parent)
        self.grab_set()

        # Handle window close button gracefully
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        header_title = "🔒 Session Locked" if self.is_unlock else "🔐 Administrator Sign In"
        header_desc = (
            "Enter your password to unlock the booking workspace."
            if self.is_unlock
            else "Sign in with your local administrator credentials."
        )

        header = tk.Frame(self, bg="#1e293b", padx=20, pady=16)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=header_title,
            font=("Segoe UI", 12, "bold"),
            fg="#f8fafc",
            bg="#1e293b",
        ).pack(anchor="w")

        tk.Label(
            header,
            text=header_desc,
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#1e293b",
        ).pack(anchor="w", pady=(3, 0))

        # Body
        body = tk.Frame(self, bg="#f8fafc", padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(body, text="Username:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=0, column=0, sticky="w", pady=(4, 2))
        self.ent_user = ttk.Entry(body, font=("Segoe UI", 10), width=30)
        self.ent_user.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        if self.is_unlock and self.locked_username:
            self.ent_user.insert(0, self.locked_username)
            self.ent_user.config(state="readonly")
        else:
            self.ent_user.insert(0, "admin")

        tk.Label(body, text="Password:", font=("Segoe UI", 9, "bold"), bg="#f8fafc", fg="#334155").grid(row=2, column=0, sticky="w", pady=(4, 2))
        
        pwd_row = tk.Frame(body, bg="#f8fafc")
        pwd_row.grid(row=3, column=0, sticky="ew", pady=(0, 6))

        self.show_pwd_var = tk.BooleanVar(value=False)
        self.ent_pwd = ttk.Entry(pwd_row, font=("Segoe UI", 10), width=24, show="*")
        self.ent_pwd.pack(side=tk.LEFT, fill=tk.X, expand=True)

        chk_show = tk.Checkbutton(
            pwd_row,
            text="Show",
            variable=self.show_pwd_var,
            font=("Segoe UI", 8),
            bg="#f8fafc",
            activebackground="#f8fafc",
            command=self._toggle_show_pwd,
        )
        chk_show.pack(side=tk.RIGHT, padx=(6, 0))

        self.lbl_error = tk.Label(body, text="", font=("Segoe UI", 8, "bold"), fg="#dc2626", bg="#f8fafc", wraplength=380, justify=tk.LEFT)
        self.lbl_error.grid(row=4, column=0, sticky="w", pady=(4, 4))

        # Bottom actions
        btn_box = tk.Frame(self, bg="#f1f5f9", padx=20, pady=12)
        btn_box.pack(fill=tk.X, side=tk.BOTTOM)

        btn_action_text = "🔓 Unlock Workspace" if self.is_unlock else "🚀 Sign In"
        self.btn_submit = tk.Button(
            btn_box,
            text=btn_action_text,
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_login,
        )
        self.btn_submit.pack(side=tk.RIGHT)

        if not self.is_unlock:
            btn_exit = tk.Button(
                btn_box,
                text="Exit Application",
                font=("Segoe UI", 9),
                bg="#e2e8f0",
                fg="#334155",
                relief="flat",
                padx=12,
                pady=6,
                command=self._on_close,
            )
            btn_exit.pack(side=tk.LEFT)

        self.ent_pwd.bind("<Return>", lambda e: self._on_login())
        self.ent_pwd.focus_set()

    def _toggle_show_pwd(self):
        if self.show_pwd_var.get():
            self.ent_pwd.config(show="")
        else:
            self.ent_pwd.config(show="*")

    def _on_login(self):
        user = self.ent_user.get().strip()
        pwd = self.ent_pwd.get()

        if not user or not pwd:
            self.lbl_error.config(text="Please enter both username and password.")
            return

        ok, msg, user_dict = authenticate_admin(user, pwd, self.db_path)
        if ok and user_dict:
            self.authenticated_user = user_dict
            self.destroy()
        else:
            self.lbl_error.config(text=msg)
            self.ent_pwd.delete(0, tk.END)
            self.ent_pwd.focus_set()

    def _on_close(self):
        if self.is_unlock:
            # If user closes lock dialog without unlocking, keep locked
            messagebox.showwarning("Locked Session", "Please authenticate to unlock the booking manager session.", parent=self)
            return
        # If startup login cancelled, exit application
        self.authenticated_user = None
        self.destroy()
