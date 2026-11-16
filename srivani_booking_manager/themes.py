"""
SRIVANI BOOKING MANAGER - Professional Theming Engine
Supports Modern Light and Slate Dark themes with consistent colors,
typography, card styles, and ttk widget styling.
"""
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

PALETTES: Dict[str, Dict[str, str]] = {
    "light": {
        "name": "light",
        "bg_app": "#f8fafc",
        "bg_card": "#ffffff",
        "bg_card_alt": "#f1f5f9",
        "bg_sidebar": "#1e293b",
        "fg_sidebar_title": "#ffffff",
        "fg_sidebar_text": "#f8fafc",
        "fg_sidebar_sub": "#94a3b8",
        "sidebar_active": "#2563eb",
        "sidebar_hover": "#334155",
        "fg_text": "#0f172a",
        "fg_muted": "#64748b",
        "border": "#e2e8f0",
        "border_dark": "#cbd5e1",
        "primary": "#2563eb",
        "primary_hover": "#1d4ed8",
        "primary_fg": "#ffffff",
        "success": "#16a34a",
        "success_hover": "#15803d",
        "warning": "#d97706",
        "danger": "#dc2626",
        "danger_hover": "#b91c1c",
        "info": "#0284c7",
        "table_bg": "#ffffff",
        "table_fg": "#0f172a",
        "table_alt": "#f8fafc",
        "table_selected": "#bfdbfe",
        "table_selected_fg": "#1e3a8a",
        "tree_heading_bg": "#e2e8f0",
        "tree_heading_fg": "#1e293b",
        "status_pending_bg": "#fef3c7",
        "status_pending_fg": "#92400e",
        "status_in_progress_bg": "#dbeafe",
        "status_in_progress_fg": "#1e40af",
        "status_booked_bg": "#dcfce7",
        "status_booked_fg": "#166534",
        "status_cancelled_bg": "#fee2e2",
        "status_cancelled_fg": "#991b1b",
    },
    "dark": {
        "name": "dark",
        "bg_app": "#0b1329",
        "bg_card": "#15203b",
        "bg_card_alt": "#1a2747",
        "bg_sidebar": "#080d1c",
        "fg_sidebar_title": "#ffffff",
        "fg_sidebar_text": "#f8fafc",
        "fg_sidebar_sub": "#64748b",
        "sidebar_active": "#3b82f6",
        "sidebar_hover": "#1e293b",
        "fg_text": "#f1f5f9",
        "fg_muted": "#94a3b8",
        "border": "#24355a",
        "border_dark": "#334155",
        "primary": "#3b82f6",
        "primary_hover": "#60a5fa",
        "primary_fg": "#ffffff",
        "success": "#22c55e",
        "success_hover": "#16a34a",
        "warning": "#f59e0b",
        "danger": "#ef4444",
        "danger_hover": "#dc2626",
        "info": "#38bdf8",
        "table_bg": "#15203b",
        "table_fg": "#f1f5f9",
        "table_alt": "#1a2747",
        "table_selected": "#1d4ed8",
        "table_selected_fg": "#ffffff",
        "tree_heading_bg": "#1e2d4d",
        "tree_heading_fg": "#e2e8f0",
        "status_pending_bg": "#78350f",
        "status_pending_fg": "#fef3c7",
        "status_in_progress_bg": "#1e3a8a",
        "status_in_progress_fg": "#dbeafe",
        "status_booked_bg": "#14532d",
        "status_booked_fg": "#dcfce7",
        "status_cancelled_bg": "#7f1d1d",
        "status_cancelled_fg": "#fee2e2",
    }
}

_active_theme = "light"

def get_current_theme_name() -> str:
    """Return currently active theme name ('light' or 'dark')."""
    return _active_theme

def get_theme_palette(name: str = "") -> Dict[str, str]:
    """Retrieve color palette dictionary for specified or active theme."""
    theme_key = name.lower() if name else _active_theme
    return PALETTES.get(theme_key, PALETTES["light"])

def apply_theme(root: tk.Misc, theme_name: str = "light") -> Dict[str, str]:
    """
    Apply theme styling to the given Tk window and configure ttk styles.
    Returns the active palette dictionary.
    """
    global _active_theme
    theme_name = theme_name.lower().strip()
    if theme_name not in PALETTES:
        theme_name = "light"
    _active_theme = theme_name
    p = PALETTES[theme_name]

    try:
        style = ttk.Style(root)
        # Use 'clam' or 'alt' as cross-platform baseline for reliable color customization
        available_themes = style.theme_names()
        if "clam" in available_themes:
            style.theme_use("clam")
        elif "alt" in available_themes:
            style.theme_use("alt")

        # Configure generic TTK widgets
        style.configure(".", background=p["bg_app"], foreground=p["fg_text"])
        style.configure("TFrame", background=p["bg_app"])
        style.configure("Card.TFrame", background=p["bg_card"], relief="solid", borderwidth=1)
        style.configure("TLabel", background=p["bg_app"], foreground=p["fg_text"], font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=p["bg_card"], foreground=p["fg_text"])
        style.configure("Muted.TLabel", foreground=p["fg_muted"])
        
        # Treeview styling
        style.configure(
            "Treeview",
            background=p["table_bg"],
            foreground=p["table_fg"],
            fieldbackground=p["table_bg"],
            rowheight=28,
            font=("Segoe UI", 9),
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", p["table_selected"])],
            foreground=[("selected", p["table_selected_fg"])],
        )

        style.configure(
            "Treeview.Heading",
            background=p["tree_heading_bg"],
            foreground=p["tree_heading_fg"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(6, 6),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", p["border_dark"])],
        )

        # Buttons
        style.configure(
            "Primary.TButton",
            background=p["primary"],
            foreground=p["primary_fg"],
            font=("Segoe UI", 9, "bold"),
            padding=(10, 6),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", p["primary_hover"])],
        )

        # Notebook (tabs)
        style.configure(
            "TNotebook",
            background=p["bg_app"],
            tabmargins=[2, 5, 2, 0],
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=p["bg_card"],
            foreground=p["fg_text"],
            padding=[12, 6],
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", p["primary"]), ("active", p["border_dark"])],
            foreground=[("selected", p["primary_fg"])],
        )

    except Exception as e:
        # Fallback if styling fails on minimal Tk
        pass

    return p
