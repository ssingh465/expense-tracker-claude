"""SQLite layer for the Spendly expense tracker.

Provides connection management and schema initialization
for two tables: ``users`` and ``expenses``.
"""

import os
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash


# Resolve the DB file to the project root (one level above this package)
# so it lives alongside ``app.py`` regardless of the working directory.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "spendly.db")


def get_db():
    """Return a SQLite connection with Row factory and foreign keys enabled.

    Caches the connection in flask.g to support in-memory databases.
    """
    if 'db' not in g:
        # Use the database path from the Flask config if available, otherwise fallback to DB_PATH.
        db_path = current_app.config.get('DATABASE', DB_PATH) if current_app else DB_PATH
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        # SQLite disables FK enforcement by default; enable it per-connection.
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def init_db():
    """Create the ``users`` and ``expenses`` tables if they do not exist."""
    ddl_users = """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """

    ddl_expenses = """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """

    conn = get_db()
    with conn:
        conn.execute(ddl_users)
        conn.execute(ddl_expenses)


def seed_db():
    """Insert the demo user and 8 sample expenses.

    Safe to call multiple times: short-circuits if ``users`` already has data.
    """
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        return

    with conn:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (
                "Demo User",
                "demo@spendly.com",
                generate_password_hash("demo123"),
            ),
        )
        user_id = cursor.lastrowid

        # 8 expenses covering all 7 fixed categories, with one repeat so
        # every category appears at least once.
        expenses = [
            (45.50,  "Food",          "2026-08-02", "Weekly groceries",                user_id),
            (12.00,  "Transport",     "2026-08-03", "Bus pass",                        user_id),
            (89.99,  "Bills",         "2026-08-05", "Electricity bill",                user_id),
            (32.75,  "Health",        "2026-08-07", "Pharmacy",                        user_id),
            (60.00,  "Entertainment", "2026-08-10", "Cinema with friends",             user_id),
            (24.30,  "Shopping",      "2026-08-12", "New t-shirt",                     user_id),
            (15.00,  "Other",         "2026-08-14", "Misc household supplies",         user_id),
            (18.20,  "Food",          "2026-08-16", "Lunch out",                       user_id),
        ]
        conn.executemany(
            """INSERT INTO expenses (amount, category, date, description, user_id)
               VALUES (?, ?, ?, ?, ?)""",
            expenses,
        )


def create_user(name, email, password_hash):
    """Insert a new user into the database.

    Returns True on success, False if the email already exists.
    """
    conn = get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_by_email(email):


    """Look up a user by email.

    Returns a sqlite3.Row on success, or None if not found.
    """
    conn = get_db()
    return conn.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()

