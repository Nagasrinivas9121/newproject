# SRIVANI BOOKING MANAGER v5.0.0
# Administrator User Manual

## 1. Introduction
The **SRIVANI BOOKING MANAGER** is a single-administrator Windows desktop suite engineered to streamline the registration, queue sequencing, assisted booking workflow, and ticket archiving for families offering donations under the **Sri Venkateswara Aalaya Nirmanam (SRIVANI) Trust** for VIP Break Darshan at Tirumala.

---

## 2. Security & Session Management

### 2.1 Administrator Sign-In
- When the application starts, enter your Admin Username and Password.
- Click **"Show"** to view masked password characters if needed.
- Press **Enter** or click **Sign In**.

### 2.2 Brute-Force Protection
- Entering an incorrect password 5 consecutive times triggers a **5-minute security lockout**.
- A countdown timer informs the user when authentication can be retried.

### 2.3 Locking Your Workstation Session
- If stepping away from your computer, click **"🔒 Lock Session"** in the lower-left sidebar.
- The workspace is immediately hidden from view.
- To resume work, enter your administrator password and click **Unlock Workspace**.

### 2.4 Changing Your Password
1. Click **"⚙️ Preferences & About"** in the sidebar.
2. Select the **Admin Security** tab.
3. Enter your current password.
4. Enter and confirm your new password (minimum 6 characters).
5. Click **Save Preferences**.

---

## 3. Dashboard & Summary KPIs

The primary dashboard displays 6 real-time operational KPI counters:
- **Total Families**: Total registered family units in the database.
- **Total Devotees**: Sum of all pilgrims across all registered families.
- **Pending Families**: Families awaiting active booking submission.
- **In Progress**: Families currently being processed in the assisted workspace.
- **Booked**: Successfully booked families with confirmed darshan slots.
- **Cancelled**: Families marked unavailable or cancelled.

---

## 4. Family & Pilgrim Management

### 4.1 Adding a New Family
1. Click the **"➕ Add Family"** button above the dashboard queue table.
2. Fill in Family Details:
   - **Family Name**: e.g., "Rao Family"
   - **Primary Contact Person**: e.g., "Srinivas Rao"
   - **Mobile Phone**: 10-digit Indian phone number
   - **Email Address**: (Optional) For e-receipt delivery
   - **Preferred Darshan Date**: Desired date (`YYYY-MM-DD`)
   - **Booking Quota**: `Advance` (online monthly release) or `Current`
   - **Priority**: `Normal`, `High`, `Urgent`, or `Low`
3. Add Devotees (Pilgrims):
   - Click **"➕ Add Devotee"** for each family member.
   - Enter Full Name, Age (0–120), Gender (`Male` / `Female` / `Other`).
   - Select ID Proof Type (`Aadhaar`, `Voter ID`, `Passport`, `Driving License`, `PAN Card`).
   - Enter the **Last 4 Digits** of the ID proof (for security and privacy).
4. Click **"Save Family Record"**.

### 4.2 Editing and Updating Records
- **Double-click** any family row in the queue table to open the full edit dialog.
- You can add additional pilgrims, update contact details, or correct ID numbers.

### 4.3 Updating Status & Payment Reference
1. Right-click a family in the queue table and choose **"Update Status & Payment"**.
2. Select Booking Status (`Pending`, `In progress`, `Booked`, `Unavailable`, `Cancelled`).
3. Select Payment Status (`Not requested`, `Request sent`, `Paid`, `Failed`, `Refunded`).
4. Enter Bank Transaction Reference / UTR Number (`payment_ref`).
5. Add internal administrative notes.
6. Click **"Save Changes"**.

---

## 5. Sequential Queue Prioritization

The application processes families one at a time in strict priority order:
1. **Urgent** priority families appear first.
2. **High** priority families appear second.
3. **Normal** priority families appear third.
4. **Low** priority families appear fourth.
- To adjust priority on the fly, select a family in the table and use the **"Set Priority"** dropdown or the **"▲ Move Up"** / **"▼ Move Down"** buttons.
- Every queue position change and status transition is permanently recorded in the **Queue History & Audit Trail**.

---

## 6. Searching & Filtering

Use the filter toolbar above the table to isolate records instantly:
- **Search Bar**: Type any text to match Family Name, Contact Name, Family Code, or Phone Number.
- **Status Filter**: Filter by All, Pending, In Progress, Booked, Unavailable, or Cancelled.
- **Payment Filter**: Filter by All, Paid, Request Sent, Not Requested, or Failed.
- **Quota Filter**: Filter by All, Advance, or Current.
- **Sort Dropdown**: Sort by Queue Priority, Date Ascending, Date Descending, or Family Name.
- Click **"Clear"** to reset all filters.

---

## 7. Customization & Theming

### 7.1 Light and Dark Modes
- Click **"🌓 Switch Theme"** in the sidebar to toggle between **Modern Light** (daytime work) and **Slate Dark** (low-strain evening work).
- Alternatively, select your preferred theme under **Preferences** -> **Appearance**.

### 7.2 Directory Configuration
Under **Preferences** -> **Storage & Paths**, you can configure custom folders for:
- **Ticket PDFs Folder**: Where downloaded tickets are archived.
- **Database Backups Folder**: Where recovery archives are created.
- **CSV & PDF Exports Folder**: Where exported reports are saved.
