"""Database query helpers for Spendly.

Provides clean, reusable functions for retrieving user and expense data
without exposing SQLite internals to the route handlers.
"""

from database.db import get_db
from datetime import datetime


def get_user_by_id(user_id):
    """Fetch user identity data by ID.

    Returns a dict with name, email, and formatted member_since date,
    or None if the user is not found.
    """
    conn = get_db()
    try:
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
    finally:
        conn.close()


def get_category_breakdown(user_id):
    """Get total spending per category for a user.

    Returns a list of dicts with name, amount, and pct,
    ordered by amount descending.
    """
    conn = get_db()
    try:
        # Fetch sums per category
        rows = conn.execute(
            "SELECT category as name, SUM(amount) as amount FROM expenses WHERE user_id = ? GROUP BY category ORDER BY amount DESC",
            (user_id,),
        ).fetchall()

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
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    """Fetch the most recent transactions for a user.

    Returns a list of dicts with date, description, category, and amount,
    ordered by date newest-first.
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT date, description, category, amount
               FROM expenses
               WHERE user_id = ?
               ORDER BY date DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_summary_stats(user_id):
    """Retrieve summary statistics for a user's expenses.

    Returns a dict with total_spent, transaction_count, and top_category.
    """
    conn = get_db()
    try:
        # Get total spent and transaction count
        totals = conn.execute(
            "SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        total_spent = totals[0] if totals[0] is not None else 0.0
        transaction_count = totals[1] if totals[1] is not None else 0

        # Get top category
        top_cat_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()

        top_category = top_cat_row["category"] if top_cat_row else "—"

        return {
            "total_spent": total_spent,
            "transaction_count": transaction_count,
            "top_category": top_category,
        }
    finally:
        conn.close()
