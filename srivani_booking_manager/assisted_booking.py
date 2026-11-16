"""
SRIVANI BOOKING MANAGER - Fast Assisted Booking Workflow Assistant
Compliant with TTD security policies: Keeps login, CAPTCHA, OTP, and payments
strictly under client/operator control. Provides high-speed copy-paste assistance.
"""
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable
import sqlite3

from config import (
    TTD_PORTAL_URL,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_BOOKED,
    STATUS_UNAVAILABLE,
    PAYMENT_PAID,
)
from database import (
    get_all_families,
    get_family,
    get_family_pilgrims,
    update_status_and_payment,
)

class AssistedBookingAssistant(tk.Toplevel):
    """
    Dedicated floating assisted booking panel for the operator.
    Enables sequential queue processing, rapid 1-click clipboard copying,
    and instantaneous status transitions.
    """

    def __init__(self, parent, on_update_callback: Callable[[], None], initial_family_id: Optional[int] = None):
        super().__init__(parent)
        self.title("⚡ Srivani Assisted Booking Assistant")
        self.geometry("700x720")
        self.minsize(640, 580)
        self.transient(parent)
        self.on_update = on_update_callback

        # Queue tracking
        self.queue_items: List[sqlite3.Row] = []
        self.current_index: int = 0
        self.initial_family_id = initial_family_id

        self._build_ui()
        self.load_queue()

    def _build_ui(self):
        container = ttk.Frame(self, padding=14)
        container.pack(fill="both", expand=True)

        # Top Bar: Security Compliance & Official Portal Button
        top_bar = ttk.Frame(container)
        top_bar.pack(fill="x", pady=(0, 10))

        title_box = ttk.Frame(top_bar)
        title_box.pack(side="left")
        ttk.Label(title_box, text="⚡ Fast Assisted Booking Assistant", font=("Segoe UI", 13, "bold"), foreground="#1B365D").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Official TTD login, CAPTCHA, OTP & payments remain under manual operator control.",
            font=("Segoe UI", 8),
            foreground="#64748B",
        ).pack(anchor="w")

        btn_portal = ttk.Button(top_bar, text="🌐 Open Official TTD Portal", command=self._open_portal)
        btn_portal.pack(side="right")

        # Queue Navigation Bar
        nav_bar = ttk.LabelFrame(container, text=" Sequential Queue Navigation ", padding=8)
        nav_bar.pack(fill="x", pady=(0, 10))

        self.btn_prev = ttk.Button(nav_bar, text="◀ Previous in Queue", command=self._prev_family)
        self.btn_prev.pack(side="left")

        self.lbl_queue_pos = ttk.Label(nav_bar, text="Family 0 of 0", font=("Segoe UI", 10, "bold"), foreground="#0D5C75")
        self.lbl_queue_pos.pack(side="left", expand=True)

        self.btn_next = ttk.Button(nav_bar, text="Next in Queue ▶", command=self._next_family)
        self.btn_next.pack(side="right")

        # Family / Donor Card
        self.card_donor = ttk.LabelFrame(container, text=" Donor & Family Info ", padding=10)
        self.card_donor.pack(fill="x", pady=(0, 10))

        # We will populate card_donor dynamically
        self.donor_content = ttk.Frame(self.card_donor)
        self.donor_content.pack(fill="x")

        # Pilgrims Card
        self.card_pilgrims = ttk.LabelFrame(container, text=" Devotee Details (One-Click Copy) ", padding=10)
        self.card_pilgrims.pack(fill="both", expand=True, pady=(0, 10))

        # Scrollable container for pilgrims
        canvas = tk.Canvas(self.card_pilgrims, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.card_pilgrims, orient="vertical", command=canvas.yview)
        self.scrollable_pilgrim_frame = ttk.Frame(canvas)

        self.scrollable_pilgrim_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_pilgrim_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Quick Copy Everything Bar
        all_bar = ttk.Frame(container)
        all_bar.pack(fill="x", pady=(0, 10))
        self.btn_copy_all = ttk.Button(
            all_bar,
            text="📋 Copy Entire Family Details (Formatted Text)",
            command=self._copy_all_formatted,
        )
        self.btn_copy_all.pack(side="left")

        self.lbl_copy_feedback = ttk.Label(all_bar, text="", font=("Segoe UI", 9, "bold"), foreground="#0F5132")
        self.lbl_copy_feedback.pack(side="left", padx=12)

        # Bottom Actions: Status Transitions
        action_bar = ttk.LabelFrame(container, text=" Rapid Booking Workflow Actions ", padding=10)
        action_bar.pack(fill="x")

        ttk.Button(action_bar, text="⚡ Mark In-Progress", command=self._mark_in_progress).pack(side="left", padx=(0, 6))
        ttk.Button(action_bar, text="✓ Mark Booked", command=self._mark_booked).pack(side="left", padx=(0, 6))
        ttk.Button(action_bar, text="💳 Mark Paid", command=self._mark_paid).pack(side="left", padx=(0, 6))
        ttk.Button(action_bar, text="✕ Mark Unavailable", command=self._mark_unavailable).pack(side="left", padx=(0, 6))
        ttk.Button(action_bar, text="Next Family ▶", command=self._next_family).pack(side="right")

    def _open_portal(self):
        webbrowser.open(TTD_PORTAL_URL)

    def load_queue(self):
        # Fetch queue ordered list (Pending & In progress first)
        self.queue_items = get_all_families(sort_by="queue")
        if not self.queue_items:
            self._render_empty_queue()
            return

        self.current_index = 0
        if self.initial_family_id:
            for idx, f in enumerate(self.queue_items):
                if f["id"] == self.initial_family_id:
                    self.current_index = idx
                    break

        self._render_current_family()

    def _render_empty_queue(self):
        self.lbl_queue_pos.config(text="Queue is Empty (0 families)")
        for widget in self.donor_content.winfo_children():
            widget.destroy()
        for widget in self.scrollable_pilgrim_frame.winfo_children():
            widget.destroy()
        ttk.Label(self.donor_content, text="No families currently found in database.").pack(pady=10)

    def _render_current_family(self):
        if not self.queue_items:
            self._render_empty_queue()
            return

        total = len(self.queue_items)
        curr = self.queue_items[self.current_index]
        self.lbl_queue_pos.config(text=f"Queue Position: {self.current_index + 1} of {total}  [{curr['priority']} Priority]")

        # Navigation button states
        self.btn_prev.config(state="normal" if self.current_index > 0 else "disabled")
        self.btn_next.config(state="normal" if self.current_index < total - 1 else "disabled")

        # Clear existing
        for widget in self.donor_content.winfo_children():
            widget.destroy()
        for widget in self.scrollable_pilgrim_frame.winfo_children():
            widget.destroy()

        # Render Donor Card
        d_frame = self.donor_content

        # Line 1: Family Name & Code
        r1 = ttk.Frame(d_frame)
        r1.pack(fill="x", pady=2)
        ttk.Label(r1, text=f"Family: {curr['family_name']} ({curr['family_code']})", font=("Segoe UI", 11, "bold"), foreground="#1B365D").pack(side="left")
        status_tag = f"Status: {curr['status']} | Payment: {curr['payment_status']}"
        ttk.Label(r1, text=status_tag, font=("Segoe UI", 9, "bold"), foreground="#0D5C75").pack(side="right")

        # Line 2: Contact, Phone & Email with copy buttons
        r2 = ttk.Frame(d_frame)
        r2.pack(fill="x", pady=3)

        ttk.Label(r2, text=f"Contact: {curr['contact_name']}").pack(side="left", padx=(0, 6))
        self._create_mini_copy_btn(r2, curr['contact_name'], "Copy Contact")

        ttk.Label(r2, text=f" | Phone: {curr['phone']}").pack(side="left", padx=(6, 6))
        self._create_mini_copy_btn(r2, curr['phone'], "Copy Phone")

        if curr['email']:
            ttk.Label(r2, text=f" | Email: {curr['email']}").pack(side="left", padx=(6, 6))
            self._create_mini_copy_btn(r2, curr['email'], "Copy Email")

        # Line 3: Booking Info
        r3 = ttk.Frame(d_frame)
        r3.pack(fill="x", pady=2)
        ttk.Label(
            r3,
            text=f"Quota: {curr['booking_type']} | Preferred Date: {curr['preferred_date'] or 'Any'} | Donation: ₹{curr['donation_amount']:,.2f}",
            font=("Segoe UI", 9),
            foreground="#333333",
        ).pack(side="left")

        # Render Pilgrims List
        pilgrims = get_family_pilgrims(curr["id"])
        if not pilgrims:
            ttk.Label(self.scrollable_pilgrim_frame, text="No devotees listed under this family.").pack(pady=10)
            return

        for idx, p in enumerate(pilgrims, start=1):
            p_card = ttk.Frame(self.scrollable_pilgrim_frame, padding=6)
            p_card.pack(fill="x", pady=3)

            # Pilgrim header line
            row_p = ttk.Frame(p_card)
            row_p.pack(fill="x")

            lbl_num = ttk.Label(row_p, text=f"#{idx}", font=("Segoe UI", 10, "bold"), foreground="#1B365D", width=3)
            lbl_num.pack(side="left")

            lbl_name = ttk.Label(row_p, text=p["full_name"], font=("Segoe UI", 10, "bold"), width=20)
            lbl_name.pack(side="left")
            self._create_mini_copy_btn(row_p, p["full_name"], "Copy Name")

            lbl_age = ttk.Label(row_p, text=f"Age: {p['age'] or '-'}", width=9)
            lbl_age.pack(side="left", padx=(8, 0))
            if p["age"]:
                self._create_mini_copy_btn(row_p, str(p["age"]), "Copy Age")

            lbl_gender = ttk.Label(row_p, text=f"Gender: {p['gender'] or '-'}", width=12)
            lbl_gender.pack(side="left", padx=(8, 0))
            if p["gender"]:
                self._create_mini_copy_btn(row_p, p["gender"], "Copy Gender")

            lbl_id = ttk.Label(row_p, text=f"{p['id_proof_type']}: {p['id_proof_last4'] or '-'}", width=18)
            lbl_id.pack(side="left", padx=(8, 0))
            if p["id_proof_last4"]:
                self._create_mini_copy_btn(row_p, p["id_proof_last4"], "Copy Last 4")

            # Separator
            ttk.Separator(self.scrollable_pilgrim_frame, orient="horizontal").pack(fill="x", pady=2)

    def _create_mini_copy_btn(self, parent, text_to_copy: str, label: str):
        if not text_to_copy:
            return
        btn = ttk.Button(parent, text="📋", width=3)
        btn.config(command=lambda: self._copy_to_clipboard(text_to_copy, label))
        btn.pack(side="left", padx=(1, 6))

    def _copy_to_clipboard(self, text: str, label: str = "Text"):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.lbl_copy_feedback.config(text=f"✓ {label} copied to clipboard!")
        self.after(2000, lambda: self.lbl_copy_feedback.config(text=""))

    def _copy_all_formatted(self):
        if not self.queue_items:
            return
        curr = self.queue_items[self.current_index]
        pilgrims = get_family_pilgrims(curr["id"])

        lines = [
            f"=== SRIVANI BOOKING DETAILS ===",
            f"Family ID: {curr['family_code']}",
            f"Family: {curr['family_name']}",
            f"Contact: {curr['contact_name']}",
            f"Mobile: {curr['phone']}",
            f"Quota Type: {curr['booking_type']}",
            f"Preferred Date: {curr['preferred_date']}",
            f"Donation Amount: ₹{curr['donation_amount']:,.2f}",
            "",
            "DEVOTEES:",
        ]
        for idx, p in enumerate(pilgrims, start=1):
            lines.append(f"{idx}. {p['full_name']} | Age: {p['age']} | Gender: {p['gender']} | {p['id_proof_type']}: {p['id_proof_last4']}")

        full_text = "\n".join(lines)
        self._copy_to_clipboard(full_text, "All Devotee Details")

    def _prev_family(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._render_current_family()

    def _next_family(self):
        if self.current_index < len(self.queue_items) - 1:
            self.current_index += 1
            self._render_current_family()

    def _mark_in_progress(self):
        if not self.queue_items:
            return
        curr = self.queue_items[self.current_index]
        update_status_and_payment(curr["id"], STATUS_IN_PROGRESS, curr["payment_status"])
        self.on_update()
        self._reload_and_stay()

    def _mark_booked(self):
        if not self.queue_items:
            return
        curr = self.queue_items[self.current_index]
        update_status_and_payment(curr["id"], STATUS_BOOKED, curr["payment_status"])
        self.on_update()
        self._copy_to_clipboard("", "")
        self.lbl_copy_feedback.config(text="✓ Marked as Booked! Moving to next family...")
        self.on_update()
        self.after(1000, self._reload_and_advance)

    def _mark_paid(self):
        if not self.queue_items:
            return
        curr = self.queue_items[self.current_index]
        update_status_and_payment(curr["id"], curr["status"], PAYMENT_PAID)
        self.on_update()
        self._reload_and_stay()

    def _mark_unavailable(self):
        if not self.queue_items:
            return
        curr = self.queue_items[self.current_index]
        update_status_and_payment(curr["id"], STATUS_UNAVAILABLE, curr["payment_status"])
        self.on_update()
        self._reload_and_advance()

    def _reload_and_stay(self):
        current_id = self.queue_items[self.current_index]["id"]
        self.queue_items = get_all_families(sort_by="queue")
        for idx, f in enumerate(self.queue_items):
            if f["id"] == current_id:
                self.current_index = idx
                break
        self._render_current_family()

    def _reload_and_advance(self):
        self.queue_items = get_all_families(sort_by="queue")
        if self.current_index >= len(self.queue_items):
            self.current_index = max(0, len(self.queue_items) - 1)
        self._render_current_family()
