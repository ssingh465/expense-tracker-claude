"""Database query helpers for Spendly.

Provides clean, reusable functions for retrieving user and expense data
without exposing SQLite internals to the route handlers.
"""

from database.db import get_db
from datetime import datetime
import sqlite3


def create_expense(user_id, amount, category, date, description):
    """Insert a new expense into the database.

    Returns True on success, False on failure.
    """
    conn = get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, date, description),
            )
        return True
    except sqlite3.Error:
        return False


def get_expense_by_id(expense_id, user_id):
    """Fetch a single expense by ID, ensuring it belongs to the given user.

    Returns a dict with the expense data, or None if not found or not owned.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    ).fetchone()
    return dict(row) if row else None


def update_expense(expense_id, user_id, amount, category, date, description):
    """Update an existing expense, ensuring ownership.

    Returns True on success, False on failure.
    """
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?",
                (amount, category, date, description, expense_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


def _apply_date_filter(query, params, date_from, date_to):
    """Helper to append a date range filter to a SQL query."""
    if date_from and date_to:
        query += " AND date BETWEEN ? AND ?"
        params.extend([date_from, date_to])
    return query, params


def get_user_by_id(user_id):
    """Fetch user identity data by ID.

    Returns a dict with name, email, and formatted member_since date,
    or None if the user is not found.
    """
    conn = get_db()
    user = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if user:
        # Format created_at (YYYY-MM-DD HH:MM:SS) to "Month YYYY"
        dt = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        return {
            "name": user["name"],
            "email": user["email"],
            "member_since": dt.strftime("%B %Y"),
        }
    return None


def get_category_breakdown(user_id, date_from=None, date_to=None):
    """Get total spending per category for a user.

    Returns a list of dicts with name, amount, and pct,
    ordered by amount descending.
    """
    conn = get_db()
    # Base query
    query = "SELECT category as name, SUM(amount) as amount FROM expenses WHERE user_id = ?"
    params = [user_id]

    query, params = _apply_date_filter(query, params, date_from, date_to)

    query += " GROUP BY category ORDER BY amount DESC"
    rows = conn.execute(query, params).fetchall()

    if not rows:
        return []

    total_spending = sum(row["amount"] for row in rows)
    if total_spending == 0:
        return [{"name": row["name"], "amount": row["amount"], "pct": 0} for row in rows]

    # Calculate percentages
    breakdown = []
    for row in rows:
        pct = round((row["amount"] / total_spending) * 100)
        breakdown.append({
            "name": row["name"],
            "amount": row["amount"],
            "pct": pct
        })

    # Adjust for rounding errors
    current_sum = sum(item["pct"] for item in breakdown)
    diff = 100 - current_sum
    if diff != 0:
        # Adjust the largest category (first one since we ordered by amount DESC)
        breakdown[0]["pct"] += diff

    return breakdown


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """Fetch the most recent transactions for a user.

    Returns a list of dicts with id, date, description, category, and amount,
    ordered by date newest-first.
    """
    conn = get_db()
    query = """SELECT id, date, description, category, amount
               FROM expenses
               WHERE user_id = ?"""
    params = [user_id]

    query, params = _apply_date_filter(query, params, date_from, date_to)

    query += " ORDER BY date DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def get_summary_stats(user_id, date_from=None, date_to=None):
    """Retrieve summary statistics for a user's expenses.

    Returns a dict with total_spent, transaction_count, and top_category.
    """
    conn = get_db()
    # Get total spent and transaction count
    query_totals = "SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?"
    params_totals = [user_id]

    query_totals, params_totals = _apply_date_filter(query_totals, params_totals, date_from, date_to)

    totals = conn.execute(query_totals, params_totals).fetchone()

    total_spent = totals[0] if totals[0] is not None else 0.0
    transaction_count = totals[1] if totals[1] is not None else 0

    # Get top category
    query_top = "SELECT category FROM expenses WHERE user_id = ?"
    params_top = [user_id]

    query_top, params_top = _apply_date_filter(query_top, params_top, date_from, date_to)
    query_top += " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1"

    top_cat_row = conn.execute(query_top, params_top).fetchone()

    top_category = top_cat_row["category"] if top_cat_row else "—"

    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "top_category": top_category,
    }
