"""
SRIVANI BOOKING MANAGER - Advanced Analytics & Operational Intelligence Engine
Calculates real-time KPIs, booking performance trends, queue intelligence,
payment summaries, document compliance, and rule-based operational insights.
Strictly relies on actual SQLite database records; zero fabricated figures.
"""
import sys
import os
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from config import DB_PATH, TICKETS_DIR
from database import get_connection
from logger import get_logger

logger = get_logger("analytics_engine")


# -----------------------------------------------------------------------------
# Date Filtering Helpers
# -----------------------------------------------------------------------------

def parse_date_filter(
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Resolve date filter into (start_date, end_date, label).
    Dates formatted as 'YYYY-MM-DD'.
    """
    today = datetime.date.today()
    f_type = (filter_type or "all").lower().strip()

    if f_type == "today":
        d_str = today.strftime("%Y-%m-%d")
        return d_str, d_str, f"Today ({d_str})"
    elif f_type in ("7days", "last_7_days", "7_days"):
        start_d = today - datetime.timedelta(days=6)
        return start_d.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), "Last 7 Days"
    elif f_type in ("30days", "last_30_days", "30_days"):
        start_d = today - datetime.timedelta(days=29)
        return start_d.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"), "Last 30 Days"
    elif f_type in ("this_month", "month"):
        start_d = today.replace(day=1)
        # End of current month
        next_month = today.replace(day=28) + datetime.timedelta(days=4)
        end_d = next_month - datetime.timedelta(days=next_month.day)
        return start_d.strftime("%Y-%m-%d"), end_d.strftime("%Y-%m-%d"), f"This Month ({today.strftime('%B %Y')})"
    elif f_type == "custom":
        s = custom_start.strip() if custom_start else None
        e = custom_end.strip() if custom_end else None
        lbl = f"Custom Range ({s or 'Beginning'} to {e or 'Present'})"
        return s, e, lbl
    else:
        return None, None, "All Time"


def _build_date_where_clause(
    start_date: Optional[str],
    end_date: Optional[str],
    date_col: str = "f.created_at",
) -> Tuple[str, List[Any]]:
    """Build parameterized SQL WHERE snippet for date filtering."""
    clauses = []
    params: List[Any] = []
    if start_date:
        clauses.append(f"substr({date_col}, 1, 10) >= ?")
        params.append(start_date)
    if end_date:
        clauses.append(f"substr({date_col}, 1, 10) <= ?")
        params.append(end_date)

    if clauses:
        return " AND " + " AND ".join(clauses), params
    return "", params


# -----------------------------------------------------------------------------
# MODULE 1: Analytics Dashboard Overview
# -----------------------------------------------------------------------------

def get_analytics_summary(
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate high-level dashboard metrics filtered by date range.
    Includes totals, status counts, completion %, and payment summary.
    """
    start_d, end_d, filter_label = parse_date_filter(filter_type, custom_start, custom_end)
    where_sql, params = _build_date_where_clause(start_d, end_d, date_col="f.created_at")

    with get_connection(db_path) as con:
        # Total families and status breakdown
        f_query = f"""
        SELECT
            COUNT(*) AS total_families,
            COALESCE(SUM(CASE WHEN f.status = 'Booked' THEN 1 ELSE 0 END), 0) AS completed_bookings,
            COALESCE(SUM(CASE WHEN f.status = 'Pending' THEN 1 ELSE 0 END), 0) AS pending_bookings,
            COALESCE(SUM(CASE WHEN f.status = 'In progress' THEN 1 ELSE 0 END), 0) AS in_progress_bookings,
            COALESCE(SUM(CASE WHEN f.status = 'Unavailable' THEN 1 ELSE 0 END), 0) AS unavailable_bookings,
            COALESCE(SUM(CASE WHEN f.status = 'Cancelled' THEN 1 ELSE 0 END), 0) AS cancelled_bookings,
            COALESCE(SUM(f.donation_amount), 0.0) AS total_donation_pledged
        FROM families f
        WHERE 1=1 {where_sql}
        """
        f_row = con.execute(f_query, params).fetchone()
        tot_fam = f_row["total_families"]
        completed = f_row["completed_bookings"]
        pending = f_row["pending_bookings"]
        in_prog = f_row["in_progress_bookings"]
        unavail = f_row["unavailable_bookings"]
        cancelled = f_row["cancelled_bookings"]
        pledged = f_row["total_donation_pledged"]

        # Total pilgrims in the filtered families
        p_query = f"""
        SELECT COUNT(p.id) AS total_pilgrims
        FROM pilgrims p
        JOIN families f ON p.family_id = f.id
        WHERE 1=1 {where_sql}
        """
        p_row = con.execute(p_query, params).fetchone()
        tot_pilgrims = p_row["total_pilgrims"] if p_row else 0

        # Completion percentage
        completion_pct = round((completed / tot_fam * 100.0), 1) if tot_fam > 0 else 0.0

        # Payment status breakdown
        pay_query = f"""
        SELECT
            COALESCE(f.payment_status, 'Not requested') AS pay_status,
            COUNT(*) AS cnt,
            COALESCE(SUM(f.donation_amount), 0.0) AS total_amount
        FROM families f
        WHERE 1=1 {where_sql}
        GROUP BY f.payment_status
        """
        pay_rows = con.execute(pay_query, params).fetchall()
        pay_summary: Dict[str, Dict[str, Any]] = {
            "Paid": {"count": 0, "amount": 0.0},
            "Pending": {"count": 0, "amount": 0.0},
            "Not requested": {"count": 0, "amount": 0.0},
            "Failed": {"count": 0, "amount": 0.0},
            "Refunded": {"count": 0, "amount": 0.0},
        }
        for r in pay_rows:
            pst = r["pay_status"]
            if pst in pay_summary:
                pay_summary[pst] = {"count": r["cnt"], "amount": r["total_amount"]}
            else:
                pay_summary[pst] = {"count": r["cnt"], "amount": r["total_amount"]}

        return {
            "filter_type": filter_type,
            "filter_label": filter_label,
            "start_date": start_d,
            "end_date": end_d,
            "total_families": tot_fam,
            "total_pilgrims": tot_pilgrims,
            "completed_bookings": completed,
            "pending_bookings": pending,
            "in_progress_bookings": in_prog,
            "unavailable_bookings": unavail,
            "cancelled_bookings": cancelled,
            "booking_completion_percentage": completion_pct,
            "total_donation_pledged": pledged,
            "payment_summary": pay_summary,
        }


# -----------------------------------------------------------------------------
# MODULE 2: Booking Performance Analytics
# -----------------------------------------------------------------------------

def get_booking_performance(
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate booking performance metrics: daily/weekly/monthly trends,
    outcomes by date, and family processing statistics.
    """
    start_d, end_d, filter_label = parse_date_filter(filter_type, custom_start, custom_end)
    where_sql, params = _build_date_where_clause(start_d, end_d, date_col="f.created_at")

    with get_connection(db_path) as con:
        # Daily trends
        daily_query = f"""
        SELECT
            substr(COALESCE(f.booked_at, f.created_at), 1, 10) AS activity_date,
            COUNT(DISTINCT f.id) AS total_families,
            COUNT(DISTINCT CASE WHEN f.status = 'Booked' THEN f.id END) AS booked,
            COUNT(DISTINCT CASE WHEN f.status = 'Pending' THEN f.id END) AS pending,
            COUNT(DISTINCT CASE WHEN f.status = 'Unavailable' THEN f.id END) AS unavailable,
            COUNT(DISTINCT CASE WHEN f.status = 'Cancelled' THEN f.id END) AS cancelled,
            COUNT(p.id) AS pilgrims_count,
            COALESCE(SUM(CASE WHEN f.status = 'Booked' THEN f.donation_amount ELSE 0 END), 0.0) AS booked_revenue
        FROM families f
        LEFT JOIN pilgrims p ON p.family_id = f.id
        WHERE 1=1 {where_sql}
        GROUP BY activity_date
        ORDER BY activity_date DESC
        LIMIT 60
        """
        daily_rows = [dict(r) for r in con.execute(daily_query, params).fetchall()]

        # Weekly trends
        weekly_query = f"""
        SELECT
            strftime('%Y-W%W', COALESCE(f.booked_at, f.created_at)) AS activity_week,
            COUNT(DISTINCT f.id) AS total_families,
            COUNT(DISTINCT CASE WHEN f.status = 'Booked' THEN f.id END) AS booked,
            COUNT(DISTINCT CASE WHEN f.status = 'Pending' THEN f.id END) AS pending,
            COUNT(p.id) AS pilgrims_count,
            COALESCE(SUM(CASE WHEN f.status = 'Booked' THEN f.donation_amount ELSE 0 END), 0.0) AS booked_revenue
        FROM families f
        LEFT JOIN pilgrims p ON p.family_id = f.id
        WHERE 1=1 {where_sql}
        GROUP BY activity_week
        ORDER BY activity_week DESC
        LIMIT 26
        """
        weekly_rows = [dict(r) for r in con.execute(weekly_query, params).fetchall()]

        # Monthly trends
        monthly_query = f"""
        SELECT
            substr(COALESCE(f.booked_at, f.created_at), 1, 7) AS activity_month,
            COUNT(DISTINCT f.id) AS total_families,
            COUNT(DISTINCT CASE WHEN f.status = 'Booked' THEN f.id END) AS booked,
            COUNT(DISTINCT CASE WHEN f.status = 'Pending' THEN f.id END) AS pending,
            COUNT(DISTINCT CASE WHEN f.status = 'Cancelled' THEN f.id END) AS cancelled,
            COUNT(p.id) AS pilgrims_count,
            COALESCE(SUM(CASE WHEN f.status = 'Booked' THEN f.donation_amount ELSE 0 END), 0.0) AS booked_revenue
        FROM families f
        LEFT JOIN pilgrims p ON p.family_id = f.id
        WHERE 1=1 {where_sql}
        GROUP BY activity_month
        ORDER BY activity_month DESC
        LIMIT 24
        """
        monthly_rows = [dict(r) for r in con.execute(monthly_query, params).fetchall()]

        # Processing Turnaround (Lead Time) for Booked records
        lead_time_query = f"""
        SELECT
            AVG((julianday(f.booked_at) - julianday(f.created_at)) * 24.0) AS avg_turnaround_hours,
            COUNT(*) AS completed_count
        FROM families f
        WHERE f.status = 'Booked' AND f.booked_at IS NOT NULL AND f.created_at IS NOT NULL
        {where_sql}
        """
        lead_row = con.execute(lead_time_query, params).fetchone()
        raw_hours = lead_row["avg_turnaround_hours"] if lead_row and lead_row["avg_turnaround_hours"] is not None else 0.0
        avg_turnaround_hours = max(0.0, round(raw_hours, 1))
        avg_turnaround_days = round(avg_turnaround_hours / 24.0, 1)

        # Processed vs. Backlog
        tot_q = f"SELECT COUNT(*) FROM families f WHERE 1=1 {where_sql}"
        tot_all = con.execute(tot_q, params).fetchone()[0]
        proc_q = f"SELECT COUNT(*) FROM families f WHERE f.status IN ('Booked', 'Unavailable', 'Cancelled') {where_sql}"
        proc_count = con.execute(proc_q, params).fetchone()[0]
        backlog_q = f"SELECT COUNT(*) FROM families f WHERE f.status IN ('Pending', 'In progress') {where_sql}"
        backlog_count = con.execute(backlog_q, params).fetchone()[0]
        processing_rate = round((proc_count / tot_all * 100.0), 1) if tot_all > 0 else 0.0

        # Booking outcomes breakdown
        outcomes_q = f"""
        SELECT f.status, COUNT(*) AS count
        FROM families f
        WHERE 1=1 {where_sql}
        GROUP BY f.status
        """
        outcome_rows = con.execute(outcomes_q, params).fetchall()
        outcomes: Dict[str, int] = {
            "Booked": 0,
            "Pending": 0,
            "In progress": 0,
            "Unavailable": 0,
            "Cancelled": 0,
        }
        for r in outcome_rows:
            st = r["status"]
            outcomes[st] = r["count"]

        completed_count = outcomes.get("Booked", 0)
        pending_count = outcomes.get("Pending", 0)
        in_prog_count = outcomes.get("In progress", 0)
        comp_vs_pend_ratio = (
            round(completed_count / (pending_count + in_prog_count), 2)
            if (pending_count + in_prog_count) > 0
            else float(completed_count)
        )

        return {
            "filter_label": filter_label,
            "daily_trends": daily_rows,
            "weekly_trends": weekly_rows,
            "monthly_trends": monthly_rows,
            "total_processed": proc_count,
            "total_backlog": backlog_count,
            "processing_completion_rate": processing_rate,
            "avg_turnaround_hours": avg_turnaround_hours,
            "avg_turnaround_days": avg_turnaround_days,
            "outcomes": outcomes,
            "completed_count": completed_count,
            "pending_count": pending_count,
            "in_progress_count": in_prog_count,
            "completed_vs_pending_ratio": comp_vs_pend_ratio,
        }


# -----------------------------------------------------------------------------
# MODULE 3: Queue Intelligence
# -----------------------------------------------------------------------------

def get_queue_intelligence(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Analyze sequential booking queue health: pending volume, oldest record,
    aging buckets (<24h, 1-3d, 4-7d, >7d), attention items, and status dwell times.
    """
    now = datetime.datetime.now()

    with get_connection(db_path) as con:
        # Total pending families
        pending_rows = con.execute("""
            SELECT
                f.id,
                f.family_code,
                f.family_name,
                f.contact_name,
                f.phone,
                f.priority,
                f.status,
                f.preferred_date,
                f.created_at,
                (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count
            FROM families f
            WHERE f.status = 'Pending'
            ORDER BY f.created_at ASC
        """).fetchall()

        total_pending = len(pending_rows)

        # Oldest pending record & Aging buckets
        aging_buckets = {
            "< 24 Hours": 0,
            "1 – 3 Days": 0,
            "4 – 7 Days": 0,
            "> 7 Days": 0,
        }
        oldest_pending = None
        max_age_days = -1.0

        for r in pending_rows:
            try:
                # Handle ISO timestamps or standard formatted strings
                c_str = r["created_at"][:19]
                dt = datetime.datetime.fromisoformat(c_str)
            except Exception:
                dt = now

            diff = (now - dt).total_seconds() / 86400.0
            if diff < 1.0:
                aging_buckets["< 24 Hours"] += 1
            elif diff < 4.0:
                aging_buckets["1 – 3 Days"] += 1
            elif diff < 8.0:
                aging_buckets["4 – 7 Days"] += 1
            else:
                aging_buckets["> 7 Days"] += 1

            if diff > max_age_days:
                max_age_days = diff
                oldest_pending = {
                    "family_code": r["family_code"],
                    "family_name": r["family_name"],
                    "priority": r["priority"],
                    "created_at": r["created_at"],
                    "days_in_queue": round(diff, 1),
                }

        # Average Dwell Time by Status from queue_history
        dwell_query = """
        SELECT
            h.new_status AS status,
            COUNT(*) AS event_count
        FROM queue_history h
        WHERE h.new_status IS NOT NULL
        GROUP BY h.new_status
        """
        history_events = {r["status"]: r["event_count"] for r in con.execute(dwell_query).fetchall()}

        # Attention Required Records
        # 1. Stalled in progress (> 24 hours)
        stalled_in_prog = con.execute("""
            SELECT f.family_code, f.family_name, f.phone, f.priority, f.created_at, 'Stalled In Progress (>24h)' AS reason
            FROM families f
            WHERE f.status = 'In progress' AND (julianday('now', 'localtime') - julianday(f.created_at)) >= 1.0
        """).fetchall()

        # 2. Urgent pending
        urgent_pending = con.execute("""
            SELECT f.family_code, f.family_name, f.phone, f.priority, f.created_at, 'Urgent Priority Pending' AS reason
            FROM families f
            WHERE f.status = 'Pending' AND f.priority = 'Urgent'
        """).fetchall()

        # 3. Imminent or Overdue Preferred Date (<= 3 days from now)
        imminent_date = con.execute("""
            SELECT f.family_code, f.family_name, f.phone, f.preferred_date, f.created_at, 'Preferred Date Imminent (<=3d)' AS reason
            FROM families f
            WHERE f.status IN ('Pending', 'In progress')
              AND f.preferred_date IS NOT NULL
              AND f.preferred_date != ''
              AND date(f.preferred_date) <= date('now', 'localtime', '+3 days')
        """).fetchall()

        # 4. Zero Pilgrims Attached
        zero_pilgrims = con.execute("""
            SELECT f.family_code, f.family_name, f.phone, f.priority, f.created_at, 'Incomplete: 0 Devotees' AS reason
            FROM families f
            WHERE (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) = 0
        """).fetchall()

        # 5. Stale pending queue (> 7 days)
        stale_pending = con.execute("""
            SELECT f.family_code, f.family_name, f.phone, f.priority, f.created_at, 'Stale Pending Queue (>7d)' AS reason
            FROM families f
            WHERE f.status = 'Pending' AND (julianday('now', 'localtime') - julianday(f.created_at)) >= 7.0
        """).fetchall()

        attention_map: Dict[str, Dict[str, Any]] = {}
        for group in (urgent_pending, imminent_date, stale_pending, stalled_in_prog, zero_pilgrims):
            for row in group:
                cd = row["family_code"]
                reason = row["reason"]
                if cd not in attention_map:
                    item = dict(row)
                    item["reasons_list"] = [reason]
                    item["reason"] = reason
                    attention_map[cd] = item
                else:
                    if reason not in attention_map[cd]["reasons_list"]:
                        attention_map[cd]["reasons_list"].append(reason)
                        attention_map[cd]["reason"] = " | ".join(attention_map[cd]["reasons_list"])

        attention_items = list(attention_map.values())

        # In-Progress Family Tracking
        in_prog_query = """
        SELECT
            f.id,
            f.family_code,
            f.family_name,
            f.contact_name,
            f.phone,
            f.priority,
            f.preferred_date,
            f.created_at,
            (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count,
            ROUND(MAX(0.0, (julianday('now', 'localtime') - julianday(COALESCE(
                (SELECT MAX(created_at) FROM queue_history WHERE family_id = f.id AND new_status = 'In progress'),
                f.created_at
            ))) * 24.0), 1) AS hours_in_progress
        FROM families f
        WHERE f.status = 'In progress'
        ORDER BY hours_in_progress DESC
        """
        in_progress_tracking = [dict(r) for r in con.execute(in_prog_query).fetchall()]
        in_prog_count = len(in_progress_tracking)

        bottleneck_notes = []
        if in_prog_count > 5:
            bottleneck_notes.append(f"High concurrency: {in_prog_count} families concurrently In Progress. Recommend focusing on single family completion.")
        if aging_buckets["> 7 Days"] > 0:
            bottleneck_notes.append(f"Queue staleness: {aging_buckets['> 7 Days']} family(ies) waiting > 7 days in pending state.")
        if not bottleneck_notes:
            bottleneck_notes.append("Queue flow is healthy: No excessive stagnation detected.")

        return {
            "total_pending": total_pending,
            "oldest_pending": oldest_pending,
            "aging_buckets": aging_buckets,
            "in_progress_count": in_prog_count,
            "in_progress_tracking": in_progress_tracking,
            "history_event_counts": history_events,
            "attention_required_count": len(attention_items),
            "attention_items": attention_items[:50],
            "bottleneck_insights": bottleneck_notes,
            "disclaimer": "Operational queue tracking relies strictly on local SQLite database records. The software does not predict or guarantee official TTD ticket availability.",
        }


# -----------------------------------------------------------------------------
# MODULE 4: Family Analytics
# -----------------------------------------------------------------------------

def get_family_analytics(
    db_path: Optional[Path] = None,
    search_term: str = "",
    status_filter: str = "All",
    ticket_filter: str = "All",
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Analyze family-wise devotee distribution, booking outcomes,
    and ticket association. Supports family-level search and filtering.
    """
    with get_connection(db_path) as con:
        # Pilgrim Count Distribution per family (1, 2, 3-4, 5-6, 7+)
        dist_query = """
        SELECT
            CASE
                WHEN p_count = 1 THEN '1 Devotee'
                WHEN p_count = 2 THEN '2 Devotees'
                WHEN p_count BETWEEN 3 AND 4 THEN '3–4 Devotees'
                WHEN p_count BETWEEN 5 AND 6 THEN '5–6 Devotees'
                ELSE '7+ Devotees'
            END AS bucket,
            COUNT(*) AS family_count
        FROM (
            SELECT f.id, COUNT(p.id) AS p_count
            FROM families f
            LEFT JOIN pilgrims p ON p.family_id = f.id
            GROUP BY f.id
        )
        GROUP BY bucket
        ORDER BY family_count DESC
        """
        dist_rows = {r["bucket"]: r["family_count"] for r in con.execute(dist_query).fetchall()}

        # Status summary across all families
        status_sum_q = "SELECT f.status, COUNT(*) AS count FROM families f GROUP BY f.status"
        status_sum = {r["status"]: r["count"] for r in con.execute(status_sum_q).fetchall()}

        # Ticket status summary
        ticket_sum_q = """
        SELECT
            CASE WHEN f.ticket_pdf_path IS NOT NULL AND f.ticket_pdf_path != '' THEN 'With Ticket' ELSE 'Missing Ticket' END AS ticket_status,
            COUNT(*) AS count
        FROM families f
        GROUP BY ticket_status
        """
        ticket_sum = {r["ticket_status"]: r["count"] for r in con.execute(ticket_sum_q).fetchall()}

        # Searchable and filterable Family Records Table
        clauses = []
        s_params: List[Any] = []
        if search_term.strip():
            pat = f"%{search_term.strip()}%"
            clauses.append("(f.family_name LIKE ? OR f.family_code LIKE ? OR f.phone LIKE ? OR f.contact_name LIKE ?)")
            s_params.extend([pat, pat, pat, pat])

        if status_filter and status_filter.lower() != "all":
            clauses.append("f.status = ?")
            s_params.append(status_filter)

        if ticket_filter and ticket_filter.lower() != "all":
            if ticket_filter.lower() in ("with ticket", "with_ticket", "has ticket", "attached"):
                clauses.append("f.ticket_pdf_path IS NOT NULL AND f.ticket_pdf_path != ''")
            elif ticket_filter.lower() in ("missing ticket", "missing", "no ticket", "without ticket"):
                clauses.append("(f.ticket_pdf_path IS NULL OR f.ticket_pdf_path = '')")

        s_filter = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        count_q = f"SELECT COUNT(*) FROM families f {s_filter}"
        total_found = con.execute(count_q, s_params).fetchone()[0]

        fam_query = f"""
        SELECT
            f.id,
            f.family_code,
            f.family_name,
            f.contact_name,
            f.phone,
            (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count,
            f.donation_amount,
            f.booking_type,
            f.preferred_date,
            f.status,
            f.payment_status,
            f.priority,
            f.booked_at,
            CASE WHEN f.ticket_pdf_path IS NOT NULL AND f.ticket_pdf_path != '' THEN 1 ELSE 0 END AS has_ticket,
            f.ticket_pdf_path,
            f.created_at
        FROM families f
        {s_filter}
        ORDER BY f.id DESC
        LIMIT ? OFFSET ?
        """
        query_params = list(s_params) + [limit, offset]
        fam_rows = [dict(r) for r in con.execute(fam_query, query_params).fetchall()]

        return {
            "pilgrim_distribution": dist_rows,
            "status_summary": status_sum,
            "ticket_summary": ticket_sum,
            "family_records": fam_rows,
            "total_found": total_found,
            "search_term": search_term,
            "status_filter": status_filter,
            "ticket_filter": ticket_filter,
        }


# -----------------------------------------------------------------------------
# MODULE 5: Payment Analytics
# -----------------------------------------------------------------------------

def get_payment_analytics(
    db_path: Optional[Path] = None,
    filter_type: str = "all",
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze payment records: total paid, pending, failed, refunded,
    reference capture rate, and date-wise collections.
    Strictly financial record tracking; never stores or exposes credentials.
    """
    start_d, end_d, filter_label = parse_date_filter(filter_type, custom_start, custom_end)
    where_sql, params = _build_date_where_clause(start_d, end_d, date_col="f.created_at")

    with get_connection(db_path) as con:
        # Aggregate totals by payment status
        q = f"""
        SELECT
            f.payment_status,
            COUNT(*) AS tx_count,
            COALESCE(SUM(f.donation_amount), 0.0) AS total_amount,
            COUNT(CASE WHEN f.payment_ref IS NOT NULL AND f.payment_ref != '' THEN 1 END) AS with_ref_count
        FROM families f
        WHERE 1=1 {where_sql}
        GROUP BY f.payment_status
        """
        rows = con.execute(q, params).fetchall()

        summary: Dict[str, Dict[str, Any]] = {
            "Paid": {"count": 0, "amount": 0.0, "with_ref": 0},
            "Pending": {"count": 0, "amount": 0.0, "with_ref": 0},
            "Not requested": {"count": 0, "amount": 0.0, "with_ref": 0},
            "Failed": {"count": 0, "amount": 0.0, "with_ref": 0},
            "Refunded": {"count": 0, "amount": 0.0, "with_ref": 0},
        }

        total_tx = 0
        total_revenue_collected = 0.0
        total_with_ref = 0

        for r in rows:
            st = r["payment_status"] or "Not requested"
            c = r["tx_count"]
            amt = r["total_amount"]
            wref = r["with_ref_count"]
            summary[st] = {"count": c, "amount": amt, "with_ref": wref}
            total_tx += c
            if st == "Paid":
                total_revenue_collected += amt
                total_with_ref += wref

        paid_cnt = summary["Paid"]["count"]
        ref_capture_rate = round((total_with_ref / paid_cnt * 100.0), 1) if paid_cnt > 0 else 0.0

        # Date-wise payment collection (for Paid records)
        date_q = f"""
        SELECT
            substr(COALESCE(f.booked_at, f.created_at), 1, 10) AS tx_date,
            COUNT(*) AS paid_count,
            COALESCE(SUM(f.donation_amount), 0.0) AS daily_amount
        FROM families f
        WHERE f.payment_status = 'Paid' {where_sql}
        GROUP BY tx_date
        ORDER BY tx_date DESC
        LIMIT 30
        """
        date_rows = [dict(r) for r in con.execute(date_q, params).fetchall()]

        return {
            "filter_label": filter_label,
            "payment_summary": summary,
            "total_transactions": total_tx,
            "total_revenue_collected": total_revenue_collected,
            "paid_transactions_count": paid_cnt,
            "payment_ref_capture_rate": ref_capture_rate,
            "date_wise_collections": date_rows,
        }


# -----------------------------------------------------------------------------
# MODULE 6: Document Analytics
# -----------------------------------------------------------------------------

def get_document_analytics(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Analyze document readiness and ticket PDF management:
    - Complete vs. incomplete pilgrim document records
    - Missing ticket attachments for Booked families
    - Duplicate ticket checksum detections
    Excludes full identity numbers; masks to last-4 only.
    """
    with get_connection(db_path) as con:
        # Complete vs Incomplete Documents
        # Incomplete = pilgrim with empty proof type OR empty last4 OR age is null
        incomplete_q = """
        SELECT
            f.id AS family_id,
            f.family_code,
            f.family_name,
            f.phone,
            COUNT(p.id) AS total_pilgrims,
            SUM(CASE WHEN p.id_proof_type IS NULL OR p.id_proof_type = '' OR p.id_proof_last4 IS NULL OR p.id_proof_last4 = '' THEN 1 ELSE 0 END) AS incomplete_pilgrims
        FROM families f
        JOIN pilgrims p ON p.family_id = f.id
        GROUP BY f.id
        HAVING incomplete_pilgrims > 0
        """
        incomplete_families = [dict(r) for r in con.execute(incomplete_q).fetchall()]

        tot_fam_with_p = con.execute("SELECT COUNT(DISTINCT family_id) FROM pilgrims").fetchone()[0]
        complete_count = max(0, tot_fam_with_p - len(incomplete_families))

        # Detail missing reasons for each incomplete family
        for inc in incomplete_families:
            fid = inc["family_id"]
            p_issues = con.execute("""
                SELECT
                    p.full_name,
                    p.id_proof_type,
                    p.id_proof_last4,
                    p.age
                FROM pilgrims p
                WHERE p.family_id = ?
                  AND (p.id_proof_type IS NULL OR p.id_proof_type = '' OR p.id_proof_last4 IS NULL OR p.id_proof_last4 = '' OR p.age IS NULL)
            """, (fid,)).fetchall()
            issues_desc = []
            for pi in p_issues:
                name = pi["full_name"] or "Devotee"
                missing = []
                if not pi["id_proof_type"]:
                    missing.append("missing ID proof type")
                if not pi["id_proof_last4"]:
                    missing.append("missing ID last-4")
                if pi["age"] is None:
                    missing.append("missing age")
                issues_desc.append(f"{name} ({', '.join(missing)})")
            inc["missing_details"] = "; ".join(issues_desc) if issues_desc else "Incomplete devotee details"

        # Families with zero registered pilgrims
        zero_p_q = """
        SELECT f.id, f.family_code, f.family_name, f.phone, f.created_at
        FROM families f
        WHERE (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) = 0
        """
        zero_pilgrims = [dict(r) for r in con.execute(zero_p_q).fetchall()]

        # Ticket PDF Availability for Booked Families
        booked_total = con.execute("SELECT COUNT(*) FROM families WHERE status = 'Booked'").fetchone()[0]
        booked_with_ticket = con.execute("""
            SELECT COUNT(*) FROM families
            WHERE status = 'Booked' AND ticket_pdf_path IS NOT NULL AND ticket_pdf_path != ''
        """).fetchone()[0]

        ticket_compliance_rate = round((booked_with_ticket / booked_total * 100.0), 1) if booked_total > 0 else 100.0

        # Missing Ticket Attachments (Booked but no ticket or file missing on disk)
        missing_tickets_q = """
        SELECT f.id, f.family_code, f.family_name, f.phone, f.booked_at, f.ticket_pdf_path
        FROM families f
        WHERE f.status = 'Booked'
          AND (f.ticket_pdf_path IS NULL OR f.ticket_pdf_path = '')
        ORDER BY f.id DESC
        LIMIT 50
        """
        missing_tickets = [dict(r) for r in con.execute(missing_tickets_q).fetchall()]

        # Duplicate Ticket Import Check (same checksum across multiple records)
        dup_checksum_q = """
        SELECT f.ticket_checksum, COUNT(*) as cnt, GROUP_CONCAT(f.family_code) as family_codes
        FROM families f
        WHERE f.ticket_checksum IS NOT NULL AND f.ticket_checksum != ''
        GROUP BY f.ticket_checksum
        HAVING cnt > 1
        """
        duplicate_checksums = [dict(r) for r in con.execute(dup_checksum_q).fetchall()]

        # Physical ticket PDF count
        stored_pdf_count = 0
        if TICKETS_DIR.exists():
            stored_pdf_count = len(list(TICKETS_DIR.glob("*.pdf")))

        return {
            "total_families_with_pilgrims": tot_fam_with_p,
            "complete_document_families": complete_count,
            "incomplete_document_families_count": len(incomplete_families),
            "incomplete_document_families": incomplete_families[:50],
            "zero_pilgrim_families_count": len(zero_pilgrims),
            "zero_pilgrim_families": zero_pilgrims[:50],
            "booked_families_total": booked_total,
            "booked_with_tickets": booked_with_ticket,
            "ticket_compliance_percentage": ticket_compliance_rate,
            "missing_tickets_count": len(missing_tickets),
            "missing_tickets": missing_tickets,
            "duplicate_ticket_warnings": duplicate_checksums,
            "physical_pdfs_stored": stored_pdf_count,
        }


# -----------------------------------------------------------------------------
# MODULE 7: Operational Intelligence & Rule-Based Prioritization
# -----------------------------------------------------------------------------

def get_operational_intelligence_config(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieve admin-configured alert thresholds and queue weights from app_settings."""
    from settings import get_setting
    try:
        return {
            "stale_pending_days": float(get_setting("alert_stale_pending_days", "7", db_path)),
            "stalled_in_prog_hours": float(get_setting("alert_stalled_in_progress_hours", "24", db_path)),
            "imminent_date_days": int(get_setting("alert_imminent_date_days", "3", db_path)),
            "weight_urgent": int(get_setting("queue_weight_urgent", "40", db_path)),
            "weight_high": int(get_setting("queue_weight_high", "25", db_path)),
            "weight_normal": int(get_setting("queue_weight_normal", "10", db_path)),
            "weight_low": int(get_setting("queue_weight_low", "0", db_path)),
            "weight_date_imminent": int(get_setting("queue_weight_date_imminent", "50", db_path)),
            "weight_aging_7d": int(get_setting("queue_weight_aging_7d", "25", db_path)),
            "weight_docs_ready": int(get_setting("queue_weight_docs_ready", "15", db_path)),
        }
    except Exception:
        return {
            "stale_pending_days": 7.0,
            "stalled_in_prog_hours": 24.0,
            "imminent_date_days": 3,
            "weight_urgent": 40,
            "weight_high": 25,
            "weight_normal": 10,
            "weight_low": 0,
            "weight_date_imminent": 50,
            "weight_aging_7d": 25,
            "weight_docs_ready": 15,
        }


def save_operational_intelligence_config(config: Dict[str, Any], db_path: Optional[Path] = None) -> bool:
    """Save admin-configured alert thresholds and queue weights into app_settings."""
    from settings import set_setting
    try:
        mapping = {
            "stale_pending_days": "alert_stale_pending_days",
            "stalled_in_prog_hours": "alert_stalled_in_progress_hours",
            "imminent_date_days": "alert_imminent_date_days",
            "weight_urgent": "queue_weight_urgent",
            "weight_high": "queue_weight_high",
            "weight_normal": "queue_weight_normal",
            "weight_low": "queue_weight_low",
            "weight_date_imminent": "queue_weight_date_imminent",
            "weight_aging_7d": "queue_weight_aging_7d",
            "weight_docs_ready": "queue_weight_docs_ready",
        }
        for k, setting_key in mapping.items():
            if k in config:
                set_setting(setting_key, str(config[k]), db_path)
        return True
    except Exception as e:
        logger.error(f"Error saving operational intelligence config: {e}")
        return False


def get_operational_intelligence(
    db_path: Optional[Path] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate actionable rule-based operational insights and queue prioritization recommendations.
    Applies explicit deterministic heuristics; zero AI hallucinations.
    Thresholds and scoring weights are fully configurable by the administrator.
    """
    now = datetime.datetime.now()
    cfg = config or get_operational_intelligence_config(db_path)

    stale_days = float(cfg.get("stale_pending_days", 7.0))
    stalled_hours = float(cfg.get("stalled_in_prog_hours", 24.0))
    imminent_days = int(cfg.get("imminent_date_days", 3))

    w_urgent = int(cfg.get("weight_urgent", 40))
    w_high = int(cfg.get("weight_high", 25))
    w_normal = int(cfg.get("weight_normal", 10))
    w_low = int(cfg.get("weight_low", 0))
    w_date = int(cfg.get("weight_date_imminent", 50))
    w_aging = int(cfg.get("weight_aging_7d", 25))
    w_docs = int(cfg.get("weight_docs_ready", 15))

    insights: List[Dict[str, Any]] = []

    with get_connection(db_path) as con:
        # Rule 1: Stagnant Pending Records (> configured days)
        old_pending = con.execute("""
            SELECT f.id, f.family_code, f.family_name, f.phone, f.priority, f.created_at,
                   CAST((julianday('now', 'localtime') - julianday(f.created_at)) AS INTEGER) AS days_waiting
            FROM families f
            WHERE f.status = 'Pending' AND (julianday('now', 'localtime') - julianday(f.created_at)) >= ?
            ORDER BY f.created_at ASC
        """, (stale_days,)).fetchall()

        if old_pending:
            insights.append({
                "severity": "HIGH",
                "category": "Queue Aging",
                "title": f"{len(old_pending)} Pending Family(ies) Waiting > {int(stale_days)} Days",
                "description": f"Oldest record '{old_pending[0]['family_name']}' ({old_pending[0]['family_code']}) has been waiting {old_pending[0]['days_waiting']} days. Process or update priority.",
                "action": "Review oldest pending queue",
                "count": len(old_pending),
            })

        # Rule 1B: Stalled In Progress (> configured hours)
        stalled_in_prog = con.execute("""
            SELECT f.id, f.family_code, f.family_name, f.phone, f.priority, f.created_at,
                   ROUND((julianday('now', 'localtime') - julianday(f.created_at)) * 24.0, 1) AS hours_waiting
            FROM families f
            WHERE f.status = 'In progress' AND ((julianday('now', 'localtime') - julianday(f.created_at)) * 24.0) >= ?
            ORDER BY f.created_at ASC
        """, (stalled_hours,)).fetchall()

        if stalled_in_prog:
            insights.append({
                "severity": "HIGH",
                "category": "Queue Stagnation",
                "title": f"{len(stalled_in_prog)} Family(ies) Stalled In Progress (>= {int(stalled_hours)}h)",
                "description": f"Family '{stalled_in_prog[0]['family_name']}' ({stalled_in_prog[0]['family_code']}) has been In Progress for {stalled_in_prog[0]['hours_waiting']} hours. Finalize booking or revert to pending.",
                "action": "Complete booking in workspace or revert status",
                "count": len(stalled_in_prog),
            })

        # Rule 1C: Imminent Target Darshan Date (<= configured days)
        imminent_records = con.execute("""
            SELECT f.id, f.family_code, f.family_name, f.phone, f.preferred_date, f.status
            FROM families f
            WHERE f.status IN ('Pending', 'In progress')
              AND f.preferred_date IS NOT NULL
              AND f.preferred_date != ''
              AND date(f.preferred_date) <= date('now', 'localtime', '+' || ? || ' days')
            ORDER BY f.preferred_date ASC
        """, (imminent_days,)).fetchall()

        if imminent_records:
            insights.append({
                "severity": "CRITICAL",
                "category": "Date Imminence",
                "title": f"{len(imminent_records)} Family(ies) With Imminent Preferred Date (<= {imminent_days} Days)",
                "description": f"Target darshan dates are imminent. Nearest date '{imminent_records[0]['preferred_date']}' for '{imminent_records[0]['family_name']}'.",
                "action": "Prioritize immediate booking on TTD portal",
                "count": len(imminent_records),
            })

        # Rule 2: Incomplete Family Profiles (Zero Devotees or Missing Contact Phone)
        incomplete_profiles = con.execute("""
            SELECT f.id, f.family_code, f.family_name, f.phone
            FROM families f
            WHERE (f.phone IS NULL OR length(trim(f.phone)) < 10)
               OR (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) = 0
        """).fetchall()

        if incomplete_profiles:
            insights.append({
                "severity": "MEDIUM",
                "category": "Data Quality",
                "title": f"{len(incomplete_profiles)} Family Record(s) Have Incomplete Information",
                "description": "Records are missing a valid 10-digit contact phone number or have zero devotees attached.",
                "action": "Complete pilgrim rosters before opening TTD portal",
                "count": len(incomplete_profiles),
            })

        # Rule 3: Payment Discrepancies
        # 3A: Booked but Payment is Not Requested / Pending
        unpaid_booked = con.execute("""
            SELECT f.id, f.family_code, f.family_name, f.donation_amount, f.payment_status
            FROM families f
            WHERE f.status = 'Booked' AND f.payment_status IN ('Not requested', 'Pending', 'Failed')
        """).fetchall()

        if unpaid_booked:
            tot_unpaid = sum(r["donation_amount"] for r in unpaid_booked)
            insights.append({
                "severity": "CRITICAL",
                "category": "Payment Reconciliation",
                "title": f"{len(unpaid_booked)} Booked Family(ies) Without Confirmed Payment (₹{tot_unpaid:,.2f})",
                "description": "Families are marked 'Booked' in TTD quota but payment status is unrecorded or pending. Update transaction reference.",
                "action": "Record payment transaction reference",
                "count": len(unpaid_booked),
            })

        # 3B: Cancelled / Unavailable but Payment is Paid (Potential Refund)
        paid_cancelled = con.execute("""
            SELECT f.id, f.family_code, f.family_name, f.donation_amount
            FROM families f
            WHERE f.status IN ('Cancelled', 'Unavailable') AND f.payment_status = 'Paid'
        """).fetchall()

        if paid_cancelled:
            tot_refund = sum(r["donation_amount"] for r in paid_cancelled)
            insights.append({
                "severity": "HIGH",
                "category": "Payment Reconciliation",
                "title": f"{len(paid_cancelled)} Cancelled/Unavailable Record(s) Marked as 'Paid' (₹{tot_refund:,.2f})",
                "description": "Donations were collected for bookings that did not materialize. Verify refund status.",
                "action": "Review and process refund status",
                "count": len(paid_cancelled),
            })

        # Rule 4: Missing Ticket PDFs for Booked Records
        missing_tickets = con.execute("""
            SELECT COUNT(*) FROM families
            WHERE status = 'Booked' AND (ticket_pdf_path IS NULL OR ticket_pdf_path = '')
        """).fetchone()[0]

        if missing_tickets > 0:
            insights.append({
                "severity": "MEDIUM",
                "category": "Ticket Management",
                "title": f"{missing_tickets} Completed Booking(s) Missing Ticket PDFs",
                "description": "Booked families do not have official TTD e-receipt ticket PDFs attached. Import downloaded PDFs.",
                "action": "Import ticket PDF via workspace",
                "count": missing_tickets,
            })

        # Rule 5: Dynamic Queue Prioritization Scoring
        # Deterministic formula based on admin-configurable rules:
        pending_candidates = con.execute("""
            SELECT
                f.id,
                f.family_code,
                f.family_name,
                f.contact_name,
                f.phone,
                f.priority,
                f.preferred_date,
                f.created_at,
                (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id) AS pilgrim_count,
                (SELECT COUNT(*) FROM pilgrims p WHERE p.family_id = f.id AND (p.id_proof_type IS NULL OR p.id_proof_type = '' OR p.id_proof_last4 IS NULL OR p.id_proof_last4 = '')) AS incomplete_pilgrim_count
            FROM families f
            WHERE f.status = 'Pending'
        """).fetchall()

        scored_queue = []
        for r in pending_candidates:
            score = 0
            tags = []

            # Priority Weight
            pr = (r["priority"] or "Normal").capitalize()
            if pr == "Urgent":
                score += w_urgent
                tags.append("Urgent Flag")
            elif pr == "High":
                score += w_high
                tags.append("High Priority")
            elif pr == "Normal":
                score += w_normal
            elif pr == "Low":
                score += w_low

            # Date Imminence Weight
            pref_d_str = r["preferred_date"]
            if pref_d_str:
                try:
                    pref_date = datetime.date.fromisoformat(pref_d_str[:10])
                    delta_days = (pref_date - datetime.date.today()).days
                    if delta_days <= 0:
                        score += w_date
                        tags.append("Date Imminent / Overdue")
                    elif delta_days <= 2:
                        score += int(w_date * 0.7)
                        tags.append("Date in <= 2 Days")
                    elif delta_days <= 5:
                        score += int(w_date * 0.4)
                        tags.append("Date in <= 5 Days")
                except Exception:
                    pass

            # Queue Aging Weight
            try:
                dt = datetime.datetime.fromisoformat(r["created_at"][:19])
                age_days = (now - dt).total_seconds() / 86400.0
                if age_days >= stale_days:
                    score += w_aging
                    tags.append("Waiting > 7 Days" if stale_days == 7 else f"Waiting > {int(stale_days)} Days")
                elif age_days >= 4.0:
                    score += int(w_aging * 0.6)
                    tags.append("Waiting 4–7 Days")
                elif age_days >= 1.0:
                    score += int(w_aging * 0.2)
            except Exception:
                pass

            # Document Readiness
            p_total = r["pilgrim_count"]
            p_incomp = r["incomplete_pilgrim_count"]
            if p_total > 0 and p_incomp == 0:
                score += w_docs
                tags.append("Docs 100% Ready")
            elif p_incomp > 0 or p_total == 0:
                score -= 10
                tags.append("Docs Incomplete")

            scored_queue.append({
                "id": r["id"],
                "family_code": r["family_code"],
                "family_name": r["family_name"],
                "contact_name": r["contact_name"],
                "phone": r["phone"],
                "priority": r["priority"],
                "preferred_date": r["preferred_date"],
                "pilgrim_count": p_total,
                "score": score,
                "reasons": tags,
            })

        # Sort recommendations by highest score first
        scored_queue.sort(key=lambda x: x["score"], reverse=True)

        return {
            "insights_count": len(insights),
            "insights": insights,
            "recommended_queue": scored_queue[:50],
            "config_used": cfg,
            "methodology": f"Configurable rule-based heuristic: Priority (max {w_urgent}) + Date imminence (max {w_date}) + Queue age (max {w_aging}) + Document readiness (max {w_docs}). Deterministic heuristic; zero generative hallucination.",
        }
