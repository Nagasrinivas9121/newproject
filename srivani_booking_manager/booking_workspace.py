"""
SRIVANI BOOKING MANAGER - Dedicated Family Booking Workspace & Step-by-Step Assistant
Modules 1, 2, and 3: Family Booking Workspace, Official TTD Portal Access,
and Step-by-Step Assisted Booking Checklist.
"""
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

import config
from database import (
    get_family,
    get_family_pilgrims,
    update_status_and_payment,
    update_family,
    assess_document_readiness,
    get_all_families,
)
from ticket_manager import store_ticket_pdf, open_ticket_pdf, generate_booking_slip_pdf

class BookingWorkspaceDialog(tk.Toplevel):
    """
    Dedicated Family Booking Workspace.
    Provides complete devotee details, document readiness verification,
    step-by-step booking checklist, official TTD portal launcher,
    and rapid status/ticket recording.
    """

    def __init__(
        self,
        parent,
        family_id: int,
        on_update_callback: Callable[[], None],
    ):
        super().__init__(parent)
        self.family_id = family_id
        self.on_update = on_update_callback
        self.family = get_family(family_id)

        if not self.family:
            messagebox.showerror("Error", "Family record not found.")
            self.destroy()
            return

        self.title(f"Booking Workspace — {self.family['family_name']} ({self.family['family_code']})")
        self.geometry("1060x780")
        self.minsize(940, 640)
        self.transient(parent)

        # Checklist state tracking
        self.step_vars = [
            tk.BooleanVar(value=True),   # Step 1: Family selected
            tk.BooleanVar(value=False),  # Step 2: Review devotee roster
            tk.BooleanVar(value=False),  # Step 3: Verify document readiness
            tk.BooleanVar(value=False),  # Step 4: Client logs into official portal
            tk.BooleanVar(value=False),  # Step 5: Client completes booking manually
            tk.BooleanVar(value=False),  # Step 6: Admin records booking result
            tk.BooleanVar(value=False),  # Step 7: Admin imports ticket PDF
        ]

        self._build_ui()
        self.load_family_data()

    def _build_ui(self):
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        # Top Bar: Workspace Title + Official Portal Launcher Button
        top_bar = ttk.Frame(container)
        top_bar.pack(fill="x", pady=(0, 10))

        title_box = ttk.Frame(top_bar)
        title_box.pack(side="left")
        self.lbl_ws_title = ttk.Label(
            title_box,
            text=f"Family Booking Workspace: {self.family['family_name']}",
            font=("Segoe UI", 14, "bold"),
            foreground="#1B365D",
        )
        self.lbl_ws_title.pack(anchor="w")

        self.lbl_ws_sub = ttk.Label(
            title_box,
            text=f"Family ID: {self.family['family_code']} • Quota: {self.family['booking_type']} • Created: {self.family['created_at']}",
            font=("Segoe UI", 9),
            foreground="#64748B",
        )
        self.lbl_ws_sub.pack(anchor="w", pady=(2, 0))

        btn_box = ttk.Frame(top_bar)
        btn_box.pack(side="right")

        # Module 2: Official TTD Website Launcher
        btn_ttd = ttk.Button(
            btn_box,
            text="🌐 Open Official TTD Website",
            style="Primary.TButton",
            command=self._open_ttd_portal,
        )
        btn_ttd.pack(side="right", padx=(8, 0))

        ttk.Button(btn_box, text="🔄 Refresh", command=self.load_family_data).pack(side="right")

        # Two-Column Workspace Layout:
        # Left Pane: Family Overview, Devotee Roster, Document Readiness
        # Right Pane: Step-by-Step Checklist, Portal Helper & Quick Copy, Booking/Payment Action Box
        paned = ttk.PanedWindow(container, orient="horizontal")
        paned.pack(fill="both", expand=True, pady=(0, 10))

        left_pane = ttk.Frame(paned, padding=4)
        right_pane = ttk.Frame(paned, padding=4)
        paned.add(left_pane, weight=3)
        paned.add(right_pane, weight=2)

        # --- LEFT PANE ---
        # 1. Family Overview Card
        f_card = ttk.LabelFrame(left_pane, text=" Family & Booking Overview ", padding=10)
        f_card.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(f_card)
        row1.pack(fill="x", pady=2)
        self.lbl_contact = ttk.Label(row1, text="Contact: —", font=("Segoe UI", 9, "bold"))
        self.lbl_contact.pack(side="left", padx=(0, 10))
        self.lbl_phone = ttk.Label(row1, text="Phone: —", font=("Segoe UI", 9))
        self.lbl_phone.pack(side="left", padx=(0, 10))
        self.lbl_email = ttk.Label(row1, text="Email: —", font=("Segoe UI", 9))
        self.lbl_email.pack(side="left")

        row2 = ttk.Frame(f_card)
        row2.pack(fill="x", pady=2)
        self.lbl_date = ttk.Label(row2, text="Preferred Date: —", font=("Segoe UI", 9))
        self.lbl_date.pack(side="left", padx=(0, 10))
        self.lbl_donation = ttk.Label(row2, text="Donation: ₹0.00", font=("Segoe UI", 9))
        self.lbl_donation.pack(side="left", padx=(0, 10))
        self.lbl_priority = ttk.Label(row2, text="Priority: Normal", font=("Segoe UI", 9))
        self.lbl_priority.pack(side="left")

        # Status & Readiness Row
        row3 = ttk.Frame(f_card)
        row3.pack(fill="x", pady=(4, 0))
        self.lbl_b_status = ttk.Label(row3, text="Booking: Pending", font=("Segoe UI", 9, "bold"), foreground="#B45309")
        self.lbl_b_status.pack(side="left", padx=(0, 12))

        self.lbl_p_status = ttk.Label(row3, text="Payment: Not requested", font=("Segoe UI", 9, "bold"), foreground="#0D5C75")
        self.lbl_p_status.pack(side="left", padx=(0, 12))

        self.lbl_doc_readiness = ttk.Label(row3, text="Documents: Checking...", font=("Segoe UI", 9, "bold"))
        self.lbl_doc_readiness.pack(side="left")

        # 2. Pilgrim / Devotee Roster
        p_card = ttk.LabelFrame(left_pane, text=" Devotee Roster & Identity Verification ", padding=10)
        p_card.pack(fill="both", expand=True)

        tbl_frame = ttk.Frame(p_card)
        tbl_frame.pack(fill="both", expand=True, pady=(0, 6))

        cols = ("idx", "name", "age", "gender", "id_type", "last4", "ready")
        self.p_tree = ttk.Treeview(tbl_frame, columns=cols, show="headings", height=8)
        self.p_tree.heading("idx", text="#")
        self.p_tree.heading("name", text="Full Name")
        self.p_tree.heading("age", text="Age")
        self.p_tree.heading("gender", text="Gender")
        self.p_tree.heading("id_type", text="ID Proof")
        self.p_tree.heading("last4", text="Last 4")
        self.p_tree.heading("ready", text="Doc Verified")

        self.p_tree.column("idx", width=35, anchor="center")
        self.p_tree.column("name", width=170)
        self.p_tree.column("age", width=45, anchor="center")
        self.p_tree.column("gender", width=70, anchor="center")
        self.p_tree.column("id_type", width=105)
        self.p_tree.column("last4", width=75, anchor="center")
        self.p_tree.column("ready", width=95, anchor="center")

        p_scroll = ttk.Scrollbar(tbl_frame, orient="vertical", command=self.p_tree.yview)
        self.p_tree.configure(yscrollcommand=p_scroll.set)
        self.p_tree.pack(side="left", fill="both", expand=True)
        p_scroll.pack(side="right", fill="y")

        # Quick Copy Devotee Bar
        copy_bar = ttk.Frame(p_card)
        copy_bar.pack(fill="x", pady=4)
        ttk.Button(copy_bar, text="📋 Copy Selected Devotee Details", command=self._copy_selected_pilgrim).pack(side="left", padx=(0, 6))
        ttk.Button(copy_bar, text="📋 Copy All Devotees (Tabbed Format)", command=self._copy_all_pilgrims).pack(side="left")
        self.lbl_copy_msg = ttk.Label(copy_bar, text="", font=("Segoe UI", 9, "bold"), foreground="#0F5132")
        self.lbl_copy_msg.pack(side="left", padx=10)

        # --- RIGHT PANE ---
        # 1. Step-by-Step Booking Checklist (Module 3)
        chk_card = ttk.LabelFrame(right_pane, text=" Step-by-Step Booking Assistance Checklist ", padding=10)
        chk_card.pack(fill="x", pady=(0, 10))

        steps = [
            ("1. Select family in booking queue", self.step_vars[0]),
            ("2. Review devotee count and details", self.step_vars[1]),
            ("3. Verify document readiness (ID proofs)", self.step_vars[2]),
            ("4. Client logs in to official TTD portal", self.step_vars[3]),
            ("5. Client completes booking manually", self.step_vars[4]),
            ("6. Admin records booking result & payment", self.step_vars[5]),
            ("7. Admin imports downloaded ticket PDF", self.step_vars[6]),
        ]

        for text, var in steps:
            chk = ttk.Checkbutton(chk_card, text=text, variable=var)
            chk.pack(anchor="w", pady=2)

        sec_tip = ttk.Label(
            chk_card,
            text="⚠️ TTD security controls (CAPTCHA, OTP, Login & Payment) remain under client's manual control.",
            font=("Segoe UI", 8, "italic"),
            foreground="#64748B",
            wraplength=380,
        )
        sec_tip.pack(anchor="w", pady=(8, 0))

        # 2. Action Panel: Record Results, Payment & Ticket
        action_card = ttk.LabelFrame(right_pane, text=" Booking Operations & Ticket Attachment ", padding=10)
        action_card.pack(fill="both", expand=True)

        # Action: Update Status & Payment
        f_status_box = ttk.Frame(action_card)
        f_status_box.pack(fill="x", pady=(0, 8))

        ttk.Label(f_status_box, text="Booking Status:").grid(row=0, column=0, sticky="w", pady=3)
        self.cb_b_status = ttk.Combobox(f_status_box, values=config.BOOKING_STATUSES, state="readonly", width=18)
        self.cb_b_status.grid(row=0, column=1, sticky="ew", padx=6, pady=3)

        ttk.Label(f_status_box, text="Payment Status:").grid(row=1, column=0, sticky="w", pady=3)
        self.cb_p_status = ttk.Combobox(f_status_box, values=config.PAYMENT_STATUSES, state="readonly", width=18)
        self.cb_p_status.grid(row=1, column=1, sticky="ew", padx=6, pady=3)

        ttk.Label(f_status_box, text="Payment Ref / UTR:").grid(row=2, column=0, sticky="w", pady=3)
        self.ent_pref = ttk.Entry(f_status_box, width=18)
        self.ent_pref.grid(row=2, column=1, sticky="ew", padx=6, pady=3)

        ttk.Label(f_status_box, text="Ticket / Ref No:").grid(row=3, column=0, sticky="w", pady=3)
        self.ent_ticket_no = ttk.Entry(f_status_box, width=18)
        self.ent_ticket_no.grid(row=3, column=1, sticky="ew", padx=6, pady=3)

        f_status_box.columnconfigure(1, weight=1)

        btn_save_status = ttk.Button(action_card, text="💾 Save Booking & Payment Status", command=self._save_status)
        btn_save_status.pack(fill="x", pady=(2, 8))

        # Ticket PDF section
        tk_box = ttk.LabelFrame(action_card, text=" Official Ticket PDF ", padding=8)
        tk_box.pack(fill="x", pady=(0, 8))

        self.lbl_ticket_file = ttk.Label(tk_box, text="No ticket attached", font=("Segoe UI", 9))
        self.lbl_ticket_file.pack(anchor="w", pady=(0, 4))

        tk_btns = ttk.Frame(tk_box)
        tk_btns.pack(fill="x")
        ttk.Button(tk_btns, text="📥 Import Ticket PDF", command=self._import_ticket_pdf).pack(side="left", padx=(0, 6))
        self.btn_open_pdf = ttk.Button(tk_btns, text="📄 Open Ticket PDF", command=self._open_ticket_pdf)
        self.btn_open_pdf.pack(side="left")

        # Summary Slip
        ttk.Button(action_card, text="🖨️ Generate Official Summary Slip (PDF)", command=self._generate_slip).pack(fill="x", pady=4)

        # Bottom Dialog Bar
        bottom_bar = ttk.Frame(container)
        bottom_bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bottom_bar, text="Close Workspace", command=self.destroy).pack(side="right")

    def _open_ttd_portal(self):
        webbrowser.open(config.TTD_PORTAL_URL)
        self.step_vars[3].set(True)

    def load_family_data(self):
        self.family = get_family(self.family_id)
        if not self.family:
            return

        f = self.family
        pilgrims = get_family_pilgrims(self.family_id)
        p_count = len(pilgrims)

        # Update labels
        self.lbl_contact.config(text=f"Contact: {f['contact_name'] or f['family_name']}")
        self.lbl_phone.config(text=f"Phone: {f['phone'] or '—'}")
        self.lbl_email.config(text=f"Email: {f['email'] or '—'}")
        self.lbl_date.config(text=f"Preferred Date: {f['preferred_date'] or 'Any'}")
        self.lbl_donation.config(text=f"Donation: ₹{f['donation_amount']:,.2f}")
        self.lbl_priority.config(text=f"Priority: {f['priority']}")

        self.lbl_b_status.config(text=f"Booking: {f['status']}")
        self.lbl_p_status.config(text=f"Payment: {f['payment_status']}")

        # Document readiness evaluation
        readiness = assess_document_readiness(pilgrims)
        if readiness["is_ready"]:
            self.lbl_doc_readiness.config(text="✓ Documents: Verified Ready", foreground="#15803D")
            self.step_vars[2].set(True)
        else:
            self.lbl_doc_readiness.config(text=f"✕ Documents: {readiness['details']}", foreground="#DC2626")
            self.step_vars[2].set(False)

        # Populate Comboboxes / Entries
        self.cb_b_status.set(f["status"] or config.STATUS_PENDING)
        self.cb_p_status.set(f["payment_status"] or config.PAYMENT_NOT_REQUESTED)

        self.ent_pref.delete(0, tk.END)
        if f["payment_ref"]:
            self.ent_pref.insert(0, f["payment_ref"])

        self.ent_ticket_no.delete(0, tk.END)
        if f["ticket_number"]:
            self.ent_ticket_no.insert(0, f["ticket_number"])

        # Populate pilgrims tree
        for item in self.p_tree.get_children():
            self.p_tree.delete(item)

        for idx, p in enumerate(pilgrims, start=1):
            is_p_ready = bool(p["full_name"] and p["id_proof_type"] and p["id_proof_last4"] and p["age"] and p["gender"])
            ready_str = "✓ Ready" if is_p_ready else "✕ Missing info"
            self.p_tree.insert("", "end", iid=str(p["id"]), values=(
                idx,
                p["full_name"],
                p["age"] if p["age"] is not None else "-",
                p["gender"],
                p["id_proof_type"] or "—",
                p["id_proof_last4"] or "—",
                ready_str,
            ))

        if p_count > 0:
            self.step_vars[1].set(True)

        if f["status"] == config.STATUS_BOOKED:
            self.step_vars[4].set(True)
            self.step_vars[5].set(True)

        # Ticket info
        if f["ticket_pdf_path"] and Path(f["ticket_pdf_path"]).exists():
            p_name = Path(f["ticket_pdf_path"]).name
            self.lbl_ticket_file.config(text=f"📄 {p_name}\nImported: {f['ticket_imported_at'] or 'Yes'}", foreground="#15803D")
            self.btn_open_pdf.config(state="normal")
            self.step_vars[6].set(True)
        else:
            self.lbl_ticket_file.config(text="⚠️ No ticket PDF currently attached", foreground="#64748B")
            self.btn_open_pdf.config(state="disabled")
            self.step_vars[6].set(False)

    def _save_status(self):
        new_status = self.cb_b_status.get()
        new_payment = self.cb_p_status.get()
        p_ref = self.ent_pref.get().strip()
        t_no = self.ent_ticket_no.get().strip()

        try:
            update_status_and_payment(
                self.family_id,
                status=new_status,
                payment_status=new_payment,
                payment_ref=p_ref,
            )
            if t_no:
                update_family(self.family_id, {"ticket_number": t_no})

            self.on_update()
            self.load_family_data()
            self.step_vars[5].set(True)
            messagebox.showinfo("Status Updated", "Booking & Payment status saved successfully!", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save status: {e}", parent=self)

    def _import_ticket_pdf(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title=f"Select Official Ticket PDF for {self.family['family_name']}",
            filetypes=[("PDF Documents (*.pdf)", "*.pdf"), ("All Files", "*.*")],
        )
        if not file_path:
            return

        t_no = self.ent_ticket_no.get().strip()
        try:
            stored_path = store_ticket_pdf(
                self.family_id,
                self.family["family_code"],
                file_path,
                ticket_number=t_no,
                allow_reimport_same_family=False,
            )
            # Mark as booked automatically if not already
            if self.family["status"] != config.STATUS_BOOKED:
                update_status_and_payment(self.family_id, config.STATUS_BOOKED, self.family["payment_status"])

            self.on_update()
            self.load_family_data()
            self.step_vars[6].set(True)
            messagebox.showinfo(
                "Ticket Imported",
                f"Ticket PDF successfully imported and verified!\nStored at:\n{stored_path}",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror("Import Error", str(e), parent=self)

    def _open_ticket_pdf(self):
        path = self.family["ticket_pdf_path"]
        if not path or not open_ticket_pdf(path):
            messagebox.showerror("Error", "Could not open ticket PDF. File may have been moved or deleted.", parent=self)

    def _generate_slip(self):
        pilgrims = [dict(p) for p in get_family_pilgrims(self.family_id)]
        try:
            slip_path = generate_booking_slip_pdf(dict(self.family), pilgrims)
            if messagebox.askyesno("Generated", f"Official summary slip generated at:\n{slip_path}\n\nOpen it now?", parent=self):
                open_ticket_pdf(slip_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate summary slip: {e}", parent=self)

    def _copy_selected_pilgrim(self):
        sel = self.p_tree.selection()
        if not sel:
            messagebox.showinfo("Select Devotee", "Select a devotee row from the roster first.", parent=self)
            return

        p_id = int(sel[0])
        pilgrims = get_family_pilgrims(self.family_id)
        target = next((p for p in pilgrims if p["id"] == p_id), None)
        if not target:
            return

        formatted = f"{target['full_name']}\t{target['age']}\t{target['gender']}\t{target['id_proof_type']}\t{target['id_proof_last4']}"
        self.clipboard_clear()
        self.clipboard_append(formatted)
        self.lbl_copy_msg.config(text=f"✓ Copied: {target['full_name']}")
        self.after(2000, lambda: self.lbl_copy_msg.config(text=""))

    def _copy_all_pilgrims(self):
        pilgrims = get_family_pilgrims(self.family_id)
        if not pilgrims:
            return
        lines = []
        for p in pilgrims:
            lines.append(f"{p['full_name']}\t{p['age']}\t{p['gender']}\t{p['id_proof_type']}\t{p['id_proof_last4']}")
        full_text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(full_text)
        self.lbl_copy_msg.config(text=f"✓ Copied all {len(pilgrims)} devotees!")
        self.after(2000, lambda: self.lbl_copy_msg.config(text=""))
