"""
SRIVANI BOOKING MANAGER - Family & Pilgrim Management Dialogs
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List

from config import (
    BOOKING_TYPES,
    BOOKING_STATUSES,
    PAYMENT_STATUSES,
    PRIORITIES,
    PRIORITY_NORMAL,
    BOOKING_TYPE_ADVANCE,
    STATUS_PENDING,
    PAYMENT_NOT_REQUESTED,
    GENDERS,
    ID_PROOF_TYPES,
    SRIVANI_DONATION_PER_PERSON,
)
from database import (
    get_family,
    get_family_pilgrims,
    add_family_with_pilgrims,
    update_family,
    add_pilgrim,
    update_pilgrim,
    delete_pilgrim,
    update_status_and_payment,
    check_existing_family,
    get_queue_history,
)
from validators import (
    clean_text,
    normalize_phone,
    normalize_date,
    validate_age,
    normalize_gender,
    normalize_id_proof_type,
    validate_id_proof_last4,
    validate_donation,
)
from ticket_manager import store_ticket_pdf, open_ticket_pdf, generate_booking_slip_pdf

class AddFamilyDialog(tk.Toplevel):
    """Dialog for creating a new family with multiple pilgrims."""

    def __init__(self, parent, on_save_callback: Callable[[], None]):
        super().__init__(parent)
        self.title("Add Srivani Family & Devotees")
        self.geometry("780x680")
        self.minsize(720, 600)
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save_callback
        self.pilgrims_list: List[Dict[str, Any]] = []

        self._build_ui()
        self.center_window(parent)

    def center_window(self, parent):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="New Srivani Family Registration", font=("Segoe UI", 13, "bold"), foreground="#1B365D").pack(anchor="w")
        ttk.Label(header, text="Register donor details and multiple family members in a single step", font=("Segoe UI", 9), foreground="#64748B").pack(anchor="w")

        # Top Section: Family / Donor Details Notebook or LabelFrame
        f_group = ttk.LabelFrame(container, text=" Primary Donor & Booking Information ", padding=12)
        f_group.pack(fill="x", pady=(0, 12))

        # Grid of fields
        # Row 0
        ttk.Label(f_group, text="Family Name *").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_family_name = ttk.Entry(f_group, width=24)
        self.ent_family_name.grid(row=0, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Primary Contact *").grid(row=0, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_contact_name = ttk.Entry(f_group, width=24)
        self.ent_contact_name.grid(row=0, column=3, sticky="ew", pady=4)

        # Row 1
        ttk.Label(f_group, text="Mobile Number").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_phone = ttk.Entry(f_group, width=24)
        self.ent_phone.grid(row=1, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Email (Optional)").grid(row=1, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_email = ttk.Entry(f_group, width=24)
        self.ent_email.grid(row=1, column=3, sticky="ew", pady=4)

        # Row 2
        ttk.Label(f_group, text="Booking Quota").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        self.cb_booking_type = ttk.Combobox(f_group, values=BOOKING_TYPES, state="readonly", width=22)
        self.cb_booking_type.set(BOOKING_TYPE_ADVANCE)
        self.cb_booking_type.grid(row=2, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Preferred Date").grid(row=2, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_preferred_date = ttk.Entry(f_group, width=24)
        self.ent_preferred_date.grid(row=2, column=3, sticky="ew", pady=4)

        # Row 3
        ttk.Label(f_group, text="Donation (₹)").grid(row=3, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_donation = ttk.Entry(f_group, width=24)
        self.ent_donation.insert(0, "10000")
        self.ent_donation.grid(row=3, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Queue Priority").grid(row=3, column=2, sticky="w", pady=4, padx=(0, 8))
        self.cb_priority = ttk.Combobox(f_group, values=PRIORITIES, state="readonly", width=22)
        self.cb_priority.set(PRIORITY_NORMAL)
        self.cb_priority.grid(row=3, column=3, sticky="ew", pady=4)

        # Row 4 (Family ID & Notes)
        ttk.Label(f_group, text="Custom ID (Optional)").grid(row=4, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_family_code = ttk.Entry(f_group, width=24)
        self.ent_family_code.grid(row=4, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Special Notes").grid(row=4, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_notes = ttk.Entry(f_group, width=24)
        self.ent_notes.grid(row=4, column=3, sticky="ew", pady=4)

        f_group.columnconfigure(1, weight=1)
        f_group.columnconfigure(3, weight=1)

        # Bottom Section: Multiple Pilgrims List
        p_group = ttk.LabelFrame(container, text=" Family Pilgrims / Devotees (Minimum 1 Required) ", padding=10)
        p_group.pack(fill="both", expand=True, pady=(0, 12))

        # Pilgrim quick input bar
        input_bar = ttk.Frame(p_group)
        input_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(input_bar, text="Name:").pack(side="left", padx=(0, 4))
        self.p_name_entry = ttk.Entry(input_bar, width=18)
        self.p_name_entry.pack(side="left", padx=(0, 8))

        ttk.Label(input_bar, text="Age:").pack(side="left", padx=(0, 4))
        self.p_age_entry = ttk.Entry(input_bar, width=4)
        self.p_age_entry.pack(side="left", padx=(0, 8))

        ttk.Label(input_bar, text="Gender:").pack(side="left", padx=(0, 4))
        self.p_gender_cb = ttk.Combobox(input_bar, values=GENDERS, state="readonly", width=8)
        self.p_gender_cb.set("Male")
        self.p_gender_cb.pack(side="left", padx=(0, 8))

        ttk.Label(input_bar, text="ID Type:").pack(side="left", padx=(0, 4))
        self.p_id_type_cb = ttk.Combobox(input_bar, values=ID_PROOF_TYPES, state="readonly", width=12)
        self.p_id_type_cb.set("Aadhaar")
        self.p_id_type_cb.pack(side="left", padx=(0, 8))

        ttk.Label(input_bar, text="Last 4:").pack(side="left", padx=(0, 4))
        self.p_last4_entry = ttk.Entry(input_bar, width=6)
        self.p_last4_entry.pack(side="left", padx=(0, 8))

        ttk.Button(input_bar, text="+ Add Pilgrim", command=self._add_pilgrim_to_table).pack(side="left", padx=4)

        # Pilgrims Treeview
        tree_frame = ttk.Frame(p_group)
        tree_frame.pack(fill="both", expand=True)

        cols = ("idx", "name", "age", "gender", "id_type", "last4")
        self.p_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=5)
        self.p_tree.heading("idx", text="#")
        self.p_tree.heading("name", text="Full Name")
        self.p_tree.heading("age", text="Age")
        self.p_tree.heading("gender", text="Gender")
        self.p_tree.heading("id_type", text="ID Proof")
        self.p_tree.heading("last4", text="Last 4 Digits")

        self.p_tree.column("idx", width=35, anchor="center")
        self.p_tree.column("name", width=180, anchor="w")
        self.p_tree.column("age", width=50, anchor="center")
        self.p_tree.column("gender", width=75, anchor="center")
        self.p_tree.column("id_type", width=110, anchor="w")
        self.p_tree.column("last4", width=90, anchor="center")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.p_tree.yview)
        self.p_tree.configure(yscrollcommand=scroll.set)
        self.p_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Table buttons
        btn_bar = ttk.Frame(p_group)
        btn_bar.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_bar, text="Remove Selected Devotee", command=self._remove_selected_pilgrim).pack(side="left")
        self.lbl_p_count = ttk.Label(btn_bar, text="Total Pilgrims: 0 (Calculated Donation: ₹0)", font=("Segoe UI", 9, "bold"), foreground="#0D5C75")
        self.lbl_p_count.pack(side="right")

        # Bottom Actions
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        save_btn = ttk.Button(actions, text="Save & Add to Queue", command=self._save_family)
        save_btn.pack(side="right")

    def _add_pilgrim_to_table(self):
        name = clean_text(self.p_name_entry.get())
        if not name:
            messagebox.showwarning("Missing Name", "Please enter the devotee's full name.", parent=self)
            self.p_name_entry.focus_set()
            return

        age_val, valid_age = validate_age(self.p_age_entry.get())
        if not valid_age:
            messagebox.showwarning("Invalid Age", "Devotee age must be a valid number between 0 and 120.", parent=self)
            self.p_age_entry.focus_set()
            return

        gender = normalize_gender(self.p_gender_cb.get())
        id_type = normalize_id_proof_type(self.p_id_type_cb.get())
        last4, _ = validate_id_proof_last4(self.p_last4_entry.get())

        # Check duplicate
        for existing in self.pilgrims_list:
            if existing["full_name"].lower() == name.lower():
                messagebox.showwarning("Duplicate Devotee", f"Devotee '{name}' is already in this family list.", parent=self)
                return

        pilgrim_obj = {
            "full_name": name,
            "age": age_val,
            "gender": gender,
            "id_proof_type": id_type,
            "id_proof_last4": last4,
        }
        self.pilgrims_list.append(pilgrim_obj)

        # Clear inputs
        self.p_name_entry.delete(0, tk.END)
        self.p_age_entry.delete(0, tk.END)
        self.p_last4_entry.delete(0, tk.END)
        self.p_name_entry.focus_set()

        self._refresh_pilgrims_table()

    def _remove_selected_pilgrim(self):
        sel = self.p_tree.selection()
        if not sel:
            messagebox.showinfo("Select Devotee", "Select a devotee from the table to remove.", parent=self)
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.pilgrims_list):
            del self.pilgrims_list[idx]
            self._refresh_pilgrims_table()

    def _refresh_pilgrims_table(self):
        for item in self.p_tree.get_children():
            self.p_tree.delete(item)
        for idx, p in enumerate(self.pilgrims_list):
            self.p_tree.insert("", "end", iid=str(idx), values=(
                idx + 1,
                p["full_name"],
                p["age"] if p["age"] is not None else "-",
                p["gender"],
                p["id_proof_type"],
                p["id_proof_last4"] or "-",
            ))
        p_count = len(self.pilgrims_list)
        calc_donation = p_count * SRIVANI_DONATION_PER_PERSON
        self.lbl_p_count.config(text=f"Total Pilgrims: {p_count} (Standard Srivani Donation: ₹{calc_donation:,.2f})")
        if p_count > 0:
            self.ent_donation.delete(0, tk.END)
            self.ent_donation.insert(0, str(int(calc_donation)))

    def _save_family(self):
        family_name = clean_text(self.ent_family_name.get())
        if not family_name:
            messagebox.showerror("Required", "Family Name is required.", parent=self)
            self.ent_family_name.focus_set()
            return

        contact_name = clean_text(self.ent_contact_name.get()) or family_name

        # Validate Phone
        phone, valid_phone = normalize_phone(self.ent_phone.get())
        if not valid_phone:
            messagebox.showerror("Invalid Phone", "Please enter a valid 10-digit mobile number.", parent=self)
            self.ent_phone.focus_set()
            return

        # Validate Date
        pref_date, valid_date = normalize_date(self.ent_preferred_date.get())
        if not valid_date:
            messagebox.showerror("Invalid Date", "Please enter a valid date (YYYY-MM-DD or DD-MM-YYYY).", parent=self)
            self.ent_preferred_date.focus_set()
            return

        # Validate Donation
        donation, valid_don = validate_donation(self.ent_donation.get())
        if not valid_don:
            messagebox.showerror("Invalid Donation", "Please enter a valid non-negative donation amount.", parent=self)
            self.ent_donation.focus_set()
            return

        # Pilgrims check
        if not self.pilgrims_list:
            messagebox.showerror("No Devotees", "Please add at least one devotee/pilgrim before saving.", parent=self)
            return

        family_code = clean_text(self.ent_family_code.get())

        # Duplicate Family check
        existing_dup = check_existing_family(phone, family_name, family_code=family_code)
        if existing_dup:
            dup_msg = (
                f"A family with matching details was found in the database:\n\n"
                f"• Existing: {existing_dup['family_name']} ({existing_dup['family_code']})\n"
                f"• Phone: {existing_dup['phone']}\n\n"
                f"Do you want to proceed and create a separate family record anyway?"
            )
            if not messagebox.askyesno("Potential Duplicate Family", dup_msg, default="no", parent=self):
                return

        family_data = {
            "family_code": family_code,
            "family_name": family_name,
            "contact_name": contact_name,
            "phone": phone,
            "email": clean_text(self.ent_email.get()),
            "donation_amount": donation,
            "booking_type": self.cb_booking_type.get(),
            "preferred_date": pref_date,
            "priority": self.cb_priority.get(),
            "notes": clean_text(self.ent_notes.get()),
        }

        try:
            add_family_with_pilgrims(family_data, self.pilgrims_list)
            self.on_save()
            self.destroy()
            messagebox.showinfo("Success", f"Family '{family_name}' successfully added with {len(self.pilgrims_list)} devotee(s)!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save family: {e}", parent=self)


class EditFamilyDialog(tk.Toplevel):
    """Dialog for editing an existing family and managing all its pilgrims."""

    def __init__(self, parent, family_id: int, on_save_callback: Callable[[], None]):
        super().__init__(parent)
        self.family_id = family_id
        self.on_save = on_save_callback
        self.family = get_family(family_id)
        if not self.family:
            messagebox.showerror("Error", "Family record not found.")
            self.destroy()
            return

        self.title(f"Edit Family — {self.family['family_name']} ({self.family['family_code']})")
        self.geometry("820x700")
        self.minsize(740, 620)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.load_data()
        self.refresh_pilgrims()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text=f"Edit Family: {self.family['family_name']}", font=("Segoe UI", 13, "bold"), foreground="#1B365D").pack(anchor="w")
        ttk.Label(header, text=f"Family ID: {self.family['family_code']} • Created: {self.family['created_at']}", font=("Segoe UI", 9), foreground="#64748B").pack(anchor="w")

        # Family Info Form
        f_group = ttk.LabelFrame(container, text=" Family & Booking Settings ", padding=12)
        f_group.pack(fill="x", pady=(0, 12))

        # Row 0
        ttk.Label(f_group, text="Family Name *").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_family_name = ttk.Entry(f_group, width=24)
        self.ent_family_name.grid(row=0, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Primary Contact *").grid(row=0, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_contact_name = ttk.Entry(f_group, width=24)
        self.ent_contact_name.grid(row=0, column=3, sticky="ew", pady=4)

        # Row 1
        ttk.Label(f_group, text="Mobile Number").grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_phone = ttk.Entry(f_group, width=24)
        self.ent_phone.grid(row=1, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Email").grid(row=1, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_email = ttk.Entry(f_group, width=24)
        self.ent_email.grid(row=1, column=3, sticky="ew", pady=4)

        # Row 2
        ttk.Label(f_group, text="Booking Quota").grid(row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        self.cb_booking_type = ttk.Combobox(f_group, values=BOOKING_TYPES, state="readonly", width=22)
        self.cb_booking_type.grid(row=2, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Preferred Date").grid(row=2, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_preferred_date = ttk.Entry(f_group, width=24)
        self.ent_preferred_date.grid(row=2, column=3, sticky="ew", pady=4)

        # Row 3
        ttk.Label(f_group, text="Donation (₹)").grid(row=3, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_donation = ttk.Entry(f_group, width=24)
        self.ent_donation.grid(row=3, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Queue Priority").grid(row=3, column=2, sticky="w", pady=4, padx=(0, 8))
        self.cb_priority = ttk.Combobox(f_group, values=PRIORITIES, state="readonly", width=22)
        self.cb_priority.grid(row=3, column=3, sticky="ew", pady=4)

        # Row 4 (Statuses)
        ttk.Label(f_group, text="Booking Status").grid(row=4, column=0, sticky="w", pady=4, padx=(0, 8))
        self.cb_status = ttk.Combobox(f_group, values=BOOKING_STATUSES, state="readonly", width=22)
        self.cb_status.grid(row=4, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Payment Status").grid(row=4, column=2, sticky="w", pady=4, padx=(0, 8))
        self.cb_payment = ttk.Combobox(f_group, values=PAYMENT_STATUSES, state="readonly", width=22)
        self.cb_payment.grid(row=4, column=3, sticky="ew", pady=4)

        # Row 5 (Ticket & Notes)
        ttk.Label(f_group, text="Ticket / Ref No.").grid(row=5, column=0, sticky="w", pady=4, padx=(0, 8))
        self.ent_ticket_no = ttk.Entry(f_group, width=24)
        self.ent_ticket_no.grid(row=5, column=1, sticky="ew", pady=4, padx=(0, 16))

        ttk.Label(f_group, text="Notes").grid(row=5, column=2, sticky="w", pady=4, padx=(0, 8))
        self.ent_notes = ttk.Entry(f_group, width=24)
        self.ent_notes.grid(row=5, column=3, sticky="ew", pady=4)

        f_group.columnconfigure(1, weight=1)
        f_group.columnconfigure(3, weight=1)

        # Pilgrims Sub-Section
        p_group = ttk.LabelFrame(container, text=" Manage Devotees / Pilgrims ", padding=10)
        p_group.pack(fill="both", expand=True, pady=(0, 12))

        # Pilgrim input / edit row
        p_bar = ttk.Frame(p_group)
        p_bar.pack(fill="x", pady=(0, 8))

        ttk.Label(p_bar, text="Devotee:").pack(side="left", padx=(0, 4))
        self.p_name_entry = ttk.Entry(p_bar, width=18)
        self.p_name_entry.pack(side="left", padx=(0, 8))

        ttk.Label(p_bar, text="Age:").pack(side="left", padx=(0, 4))
        self.p_age_entry = ttk.Entry(p_bar, width=4)
        self.p_age_entry.pack(side="left", padx=(0, 8))

        ttk.Label(p_bar, text="Gender:").pack(side="left", padx=(0, 4))
        self.p_gender_cb = ttk.Combobox(p_bar, values=GENDERS, state="readonly", width=8)
        self.p_gender_cb.set("Male")
        self.p_gender_cb.pack(side="left", padx=(0, 8))

        ttk.Label(p_bar, text="ID:").pack(side="left", padx=(0, 4))
        self.p_id_type_cb = ttk.Combobox(p_bar, values=ID_PROOF_TYPES, state="readonly", width=11)
        self.p_id_type_cb.set("Aadhaar")
        self.p_id_type_cb.pack(side="left", padx=(0, 8))

        ttk.Label(p_bar, text="Last 4:").pack(side="left", padx=(0, 4))
        self.p_last4_entry = ttk.Entry(p_bar, width=6)
        self.p_last4_entry.pack(side="left", padx=(0, 8))

        self.btn_add_or_update_p = ttk.Button(p_bar, text="+ Add Devotee", command=self._save_pilgrim_entry)
        self.btn_add_or_update_p.pack(side="left", padx=4)
        self.editing_pilgrim_id: Optional[int] = None

        # Devotees Treeview
        tree_frame = ttk.Frame(p_group)
        tree_frame.pack(fill="both", expand=True)

        cols = ("id", "name", "age", "gender", "id_type", "last4")
        self.p_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=5)
        self.p_tree.heading("id", text="ID")
        self.p_tree.heading("name", text="Full Name")
        self.p_tree.heading("age", text="Age")
        self.p_tree.heading("gender", text="Gender")
        self.p_tree.heading("id_type", text="ID Proof")
        self.p_tree.heading("last4", text="Last 4 Digits")

        self.p_tree.column("id", width=40, anchor="center")
        self.p_tree.column("name", width=180, anchor="w")
        self.p_tree.column("age", width=50, anchor="center")
        self.p_tree.column("gender", width=75, anchor="center")
        self.p_tree.column("id_type", width=110, anchor="w")
        self.p_tree.column("last4", width=90, anchor="center")

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.p_tree.yview)
        self.p_tree.configure(yscrollcommand=scroll.set)
        self.p_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.p_tree.bind("<<TreeviewSelect>>", self._on_pilgrim_select)

        # Actions on devotees
        dev_actions = ttk.Frame(p_group)
        dev_actions.pack(fill="x", pady=(6, 0))
        ttk.Button(dev_actions, text="Edit Selected Devotee", command=self._load_selected_for_edit).pack(side="left", padx=(0, 6))
        ttk.Button(dev_actions, text="Delete Devotee", command=self._delete_selected_pilgrim).pack(side="left", padx=(0, 6))
        ttk.Button(dev_actions, text="Clear Devotee Inputs", command=self._clear_pilgrim_inputs).pack(side="left")

        # Bottom Actions
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Save Changes", command=self._save_family_changes).pack(side="right")

    def load_data(self):
        f = self.family
        self.ent_family_name.insert(0, f["family_name"] or "")
        self.ent_contact_name.insert(0, f["contact_name"] or "")
        self.ent_phone.insert(0, f["phone"] or "")
        self.ent_email.insert(0, f["email"] or "")
        self.cb_booking_type.set(f["booking_type"] or BOOKING_TYPE_ADVANCE)
        self.ent_preferred_date.insert(0, f["preferred_date"] or "")
        self.ent_donation.insert(0, str(f["donation_amount"] or 10000.0))
        self.cb_priority.set(f["priority"] or PRIORITY_NORMAL)
        self.cb_status.set(f["status"] or STATUS_PENDING)
        self.cb_payment.set(f["payment_status"] or PAYMENT_NOT_REQUESTED)
        self.ent_ticket_no.insert(0, f["ticket_number"] or "")
        self.ent_notes.insert(0, f["notes"] or "")

    def refresh_pilgrims(self):
        for item in self.p_tree.get_children():
            self.p_tree.delete(item)
        pilgrims = get_family_pilgrims(self.family_id)
        for p in pilgrims:
            self.p_tree.insert("", "end", iid=str(p["id"]), values=(
                p["id"],
                p["full_name"],
                p["age"] if p["age"] is not None else "-",
                p["gender"],
                p["id_proof_type"],
                p["id_proof_last4"] or "-",
            ))

    def _on_pilgrim_select(self, event=None):
        pass

    def _load_selected_for_edit(self):
        sel = self.p_tree.selection()
        if not sel:
            messagebox.showinfo("Select Devotee", "Select a devotee from the table to edit.", parent=self)
            return
        p_id = int(sel[0])
        pilgrims = get_family_pilgrims(self.family_id)
        target = next((p for p in pilgrims if p["id"] == p_id), None)
        if not target:
            return

        self.editing_pilgrim_id = p_id
        self.p_name_entry.delete(0, tk.END)
        self.p_name_entry.insert(0, target["full_name"])

        self.p_age_entry.delete(0, tk.END)
        if target["age"] is not None:
            self.p_age_entry.insert(0, str(target["age"]))

        self.p_gender_cb.set(target["gender"] or "Male")
        self.p_id_type_cb.set(target["id_proof_type"] or "Aadhaar")

        self.p_last4_entry.delete(0, tk.END)
        self.p_last4_entry.insert(0, target["id_proof_last4"] or "")

        self.btn_add_or_update_p.config(text="✓ Update Devotee")

    def _clear_pilgrim_inputs(self):
        self.editing_pilgrim_id = None
        self.p_name_entry.delete(0, tk.END)
        self.p_age_entry.delete(0, tk.END)
        self.p_last4_entry.delete(0, tk.END)
        self.btn_add_or_update_p.config(text="+ Add Devotee")

    def _save_pilgrim_entry(self):
        name = clean_text(self.p_name_entry.get())
        if not name:
            messagebox.showwarning("Missing Name", "Devotee full name is required.", parent=self)
            self.p_name_entry.focus_set()
            return

        age_val, valid_age = validate_age(self.p_age_entry.get())
        if not valid_age:
            messagebox.showwarning("Invalid Age", "Age must be between 0 and 120.", parent=self)
            self.p_age_entry.focus_set()
            return

        gender = normalize_gender(self.p_gender_cb.get())
        id_type = normalize_id_proof_type(self.p_id_type_cb.get())
        last4, _ = validate_id_proof_last4(self.p_last4_entry.get())

        p_data = {
            "full_name": name,
            "age": age_val,
            "gender": gender,
            "id_proof_type": id_type,
            "id_proof_last4": last4,
        }

        if self.editing_pilgrim_id:
            update_pilgrim(self.editing_pilgrim_id, p_data)
        else:
            add_pilgrim(self.family_id, p_data)

        self._clear_pilgrim_inputs()
        self.refresh_pilgrims()

    def _delete_selected_pilgrim(self):
        sel = self.p_tree.selection()
        if not sel:
            messagebox.showinfo("Select Devotee", "Select a devotee from the table to delete.", parent=self)
            return
        p_id = int(sel[0])
        if messagebox.askyesno("Confirm Delete", "Remove this devotee from the family?", parent=self):
            delete_pilgrim(p_id)
            self._clear_pilgrim_inputs()
            self.refresh_pilgrims()

    def _save_family_changes(self):
        family_name = clean_text(self.ent_family_name.get())
        if not family_name:
            messagebox.showerror("Required", "Family Name is required.", parent=self)
            return

        contact_name = clean_text(self.ent_contact_name.get()) or family_name

        phone, valid_phone = normalize_phone(self.ent_phone.get())
        if not valid_phone:
            messagebox.showerror("Invalid Phone", "Please enter a valid mobile number.", parent=self)
            return

        pref_date, valid_date = normalize_date(self.ent_preferred_date.get())
        if not valid_date:
            messagebox.showerror("Invalid Date", "Please enter a valid date format.", parent=self)
            return

        donation, valid_don = validate_donation(self.ent_donation.get())
        if not valid_don:
            messagebox.showerror("Invalid Donation", "Please enter a valid donation amount.", parent=self)
            return

        update_data = {
            "family_name": family_name,
            "contact_name": contact_name,
            "phone": phone,
            "email": clean_text(self.ent_email.get()),
            "donation_amount": donation,
            "booking_type": self.cb_booking_type.get(),
            "preferred_date": pref_date,
            "priority": self.cb_priority.get(),
            "status": self.cb_status.get(),
            "payment_status": self.cb_payment.get(),
            "ticket_number": clean_text(self.ent_ticket_no.get()),
            "notes": clean_text(self.ent_notes.get()),
        }

        update_family(self.family_id, update_data)
        self.on_save()
        self.destroy()
        messagebox.showinfo("Success", "Family details updated successfully!")


class UpdateStatusDialog(tk.Toplevel):
    """Quick modal for updating booking & payment status with notes and ticket number."""

    def __init__(self, parent, family_id: int, on_save_callback: Callable[[], None]):
        super().__init__(parent)
        self.family_id = family_id
        self.on_save = on_save_callback
        self.family = get_family(family_id)
        if not self.family:
            self.destroy()
            return

        self.title("Update Status & Payment")
        self.geometry("420x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=18)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"{self.family['family_name']} ({self.family['family_code']})", font=("Segoe UI", 11, "bold"), foreground="#1B365D").pack(anchor="w", pady=(0, 10))

        ttk.Label(frm, text="Booking Status:").pack(anchor="w")
        self.cb_status = ttk.Combobox(frm, values=BOOKING_STATUSES, state="readonly")
        self.cb_status.set(self.family["status"] or STATUS_PENDING)
        self.cb_status.pack(fill="x", pady=(2, 8))

        ttk.Label(frm, text="Payment Status:").pack(anchor="w")
        self.cb_payment = ttk.Combobox(frm, values=PAYMENT_STATUSES, state="readonly")
        self.cb_payment.set(self.family["payment_status"] or PAYMENT_NOT_REQUESTED)
        self.cb_payment.pack(fill="x", pady=(2, 8))

        ttk.Label(frm, text="Transaction Ref / UTR / Order ID:").pack(anchor="w")
        self.ent_pref = ttk.Entry(frm)
        self.ent_pref.insert(0, self.family["payment_ref"] or "")
        self.ent_pref.pack(fill="x", pady=(2, 8))

        ttk.Label(frm, text="Ticket / Reference Number:").pack(anchor="w")
        self.ent_ticket_no = ttk.Entry(frm)
        self.ent_ticket_no.insert(0, self.family["ticket_number"] or "")
        self.ent_ticket_no.pack(fill="x", pady=(2, 8))

        ttk.Label(frm, text="Notes / Remarks:").pack(anchor="w")
        self.ent_notes = ttk.Entry(frm)
        self.ent_notes.insert(0, self.family["notes"] or "")
        self.ent_notes.pack(fill="x", pady=(2, 14))

        btn_box = ttk.Frame(frm)
        btn_box.pack(fill="x")
        ttk.Button(btn_box, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Save Status", command=self._save).pack(side="right")

    def _save(self):
        status = self.cb_status.get()
        payment = self.cb_payment.get()
        pref = clean_text(self.ent_pref.get())
        ticket_no = clean_text(self.ent_ticket_no.get())
        notes = clean_text(self.ent_notes.get())

        update_status_and_payment(self.family_id, status, payment, notes=notes, payment_ref=pref)
        if ticket_no != (self.family["ticket_number"] or ""):
            update_family(self.family_id, {"ticket_number": ticket_no})

        self.on_save()
        self.destroy()


class TicketPDFDialog(tk.Toplevel):
    """Dialog to attach ticket PDF, view existing PDF, or generate official booking slip."""

    def __init__(self, parent, family_id: int, on_save_callback: Callable[[], None]):
        super().__init__(parent)
        self.family_id = family_id
        self.on_save = on_save_callback
        self.family = get_family(family_id)
        if not self.family:
            self.destroy()
            return

        self.title("Ticket PDF & Slips Management")
        self.geometry("520x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text=f"Ticket PDF & Documentation", font=("Segoe UI", 12, "bold"), foreground="#1B365D").pack(anchor="w")
        ttk.Label(frm, text=f"Family: {self.family['family_name']} ({self.family['family_code']})", font=("Segoe UI", 9), foreground="#64748B").pack(anchor="w", pady=(2, 14))

        # Current attachment status box
        status_box = ttk.LabelFrame(frm, text=" Current Ticket Attachment ", padding=12)
        status_box.pack(fill="x", pady=(0, 14))

        current_path = self.family["ticket_pdf_path"]
        if current_path:
            self.lbl_status = ttk.Label(status_box, text=f"📄 File Attached:\n{current_path}", font=("Segoe UI", 9), foreground="#0F5132")
            self.lbl_status.pack(anchor="w", pady=(0, 8))
            ttk.Button(status_box, text="Open Ticket PDF in Viewer", command=self._open_pdf).pack(anchor="w")
        else:
            self.lbl_status = ttk.Label(status_box, text="⚠️ No ticket PDF currently attached for this family.", font=("Segoe UI", 9), foreground="#842029")
            self.lbl_status.pack(anchor="w")

        # Action: Attach new PDF
        attach_box = ttk.LabelFrame(frm, text=" Upload / Replace Ticket PDF ", padding=12)
        attach_box.pack(fill="x", pady=(0, 14))

        row1 = ttk.Frame(attach_box)
        row1.pack(fill="x", pady=4)
        ttk.Label(row1, text="Ticket / E-Receipt No:").pack(side="left", padx=(0, 8))
        self.ent_ticket_number = ttk.Entry(row1, width=20)
        self.ent_ticket_number.insert(0, self.family["ticket_number"] or "")
        self.ent_ticket_number.pack(side="left")

        ttk.Button(attach_box, text="Select PDF File to Attach...", command=self._browse_and_attach).pack(anchor="w", pady=6)

        # Action: Generate official booking slip
        slip_box = ttk.LabelFrame(frm, text=" Print / Generate Summary Slip ", padding=12)
        slip_box.pack(fill="x")
        ttk.Button(slip_box, text="Generate Srivani Devotee Summary Slip (PDF)", command=self._generate_slip).pack(anchor="w")

    def _open_pdf(self):
        path = self.family["ticket_pdf_path"]
        if not path or not open_ticket_pdf(path):
            messagebox.showerror("Error", "Could not open ticket PDF. The file may have been moved or deleted.", parent=self)

    def _browse_and_attach(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Select Official TTD Ticket PDF",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        t_num = clean_text(self.ent_ticket_number.get())
        try:
            stored_path = store_ticket_pdf(self.family_id, self.family["family_code"], file_path, ticket_number=t_num)
            self.on_save()
            messagebox.showinfo("Attached", f"Ticket PDF stored and organized successfully at:\n{stored_path}", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to attach ticket PDF: {e}", parent=self)

    def _generate_slip(self):
        pilgrims = [dict(p) for p in get_family_pilgrims(self.family_id)]
        try:
            slip_path = generate_booking_slip_pdf(dict(self.family), pilgrims)
            if messagebox.askyesno("Generated", f"Booking slip generated at:\n{slip_path}\n\nWould you like to open it now?", parent=self):
                open_ticket_pdf(slip_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate summary slip: {e}", parent=self)


class QueueHistoryDialog(tk.Toplevel):
    """Dialog showing the audit trail and queue history of all families."""

    def __init__(self, parent, family_id: Optional[int] = None):
        super().__init__(parent)
        self.family_id = family_id
        title = "Queue & Booking Activity History"
        if family_id:
            fam = get_family(family_id)
            if fam:
                title += f" — {fam['family_name']} ({fam['family_code']})"
        self.title(title)
        self.geometry("900x560")
        self.minsize(780, 460)
        self.transient(parent)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        hdr = ttk.Frame(container)
        hdr.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr, text="Queue & Status Activity Log", font=("Segoe UI", 13, "bold"), foreground="#1B365D").pack(anchor="w")
        ttk.Label(hdr, text="Chronological audit history of family registrations, queue transitions, and status updates", font=("Segoe UI", 9), foreground="#64748B").pack(anchor="w")

        # Table
        tbl_frame = ttk.Frame(container)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("time", "action", "code", "family", "status_change", "priority_change", "notes")
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", selectmode="browse")

        headings = {
            "time": "Timestamp",
            "action": "Event",
            "code": "Family ID",
            "family": "Family Name",
            "status_change": "Status Change",
            "priority_change": "Priority Change",
            "notes": "Details / Notes",
        }
        widths = {
            "time": 140,
            "action": 120,
            "code": 110,
            "family": 130,
            "status_change": 130,
            "priority_change": 110,
            "notes": 220,
        }

        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="center" if c in ("time", "action") else "w")

        y_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(tbl_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        tbl_frame.rowconfigure(0, weight=1)
        tbl_frame.columnconfigure(0, weight=1)

        bottom = ttk.Frame(container)
        bottom.pack(fill="x")
        self.lbl_count = ttk.Label(bottom, text="0 event(s) recorded", font=("Segoe UI", 9), foreground="#64748B")
        self.lbl_count.pack(side="left")
        ttk.Button(bottom, text="Refresh", command=self.refresh).pack(side="right", padx=(8, 0))
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right")

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        events = get_queue_history(family_id=self.family_id, limit=200)
        for ev in events:
            st_change = "—"
            if ev["old_status"] or ev["new_status"]:
                st_change = f"{ev['old_status'] or 'None'} ➔ {ev['new_status'] or 'None'}"

            pr_change = "—"
            if ev["old_priority"] or ev["new_priority"]:
                pr_change = f"{ev['old_priority'] or 'None'} ➔ {ev['new_priority'] or 'None'}"

            self.tree.insert("", "end", values=(
                ev["created_at"],
                ev["action"],
                ev["family_code"] or "—",
                ev["family_name"] or "—",
                st_change,
                pr_change,
                ev["notes"] or "",
            ))

        self.lbl_count.config(text=f"{len(events)} event(s) recorded")

