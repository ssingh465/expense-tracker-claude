import pytest

from app import app
from database.db import get_db, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as client:
        with app.app_context():
            conn = get_db()
            conn.execute("DROP TABLE IF EXISTS expenses")
            conn.execute("DROP TABLE IF EXISTS users")
            conn.commit()
            init_db()
            seed_db()
        yield client


@pytest.fixture
def db_conn():
    with app.app_context():
        conn = get_db()
        conn.execute("DROP TABLE IF EXISTS expenses")
        conn.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        init_db()
        seed_db()
        yield conn
        conn.close()


# ------------------------------------------------------------------ #
# Unit Tests                                                           #
# ------------------------------------------------------------------ #


def test_get_user_by_id_valid(db_conn):
    with app.app_context():
        # Demo user is seeded
        user = get_user_by_id(1)
        assert user is not None
        assert user["name"] == "Demo User"
        assert user["email"] == "demo@spendly.com"
        assert "member_since" in user


def test_get_user_by_id_invalid():
    with app.app_context():
        assert get_user_by_id(999) is None


def test_get_summary_stats_with_expenses():
    with app.app_context():
        # Demo user (id 1) has 8 expenses summing to 297.74
        stats = get_summary_stats(1)
        assert stats["total_spent"] == 297.74
        assert stats["transaction_count"] == 8
        assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(db_conn):
    with app.app_context():
        # Create user with no expenses
        cursor = db_conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("No Spend 1", "none1@example.com", "hash"),
        )
        user_id = cursor.lastrowid
        db_conn.commit()

        stats = get_summary_stats(user_id)
        assert stats["total_spent"] == 0.0
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"


def test_get_recent_transactions_with_expenses():
    with app.app_context():
        txs = get_recent_transactions(1)
        assert len(txs) > 0
        assert "date" in txs[0]
        assert "amount" in txs[0]
        # Verify ordering (newest first)
        assert txs[0]["date"] >= txs[-1]["date"]


def test_get_recent_transactions_no_expenses(db_conn):
    with app.app_context():
        cursor = db_conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("No Spend 2", "none2@example.com", "hash"),
        )
        user_id = cursor.lastrowid
        db_conn.commit()
        assert get_recent_transactions(user_id) == []


def test_get_category_breakdown_with_expenses():
    with app.app_context():
        breakdown = get_category_breakdown(1)
        assert len(breakdown) == 7  # 7 distinct categories in seed

        # Check percentages sum to 100
        total_pct = sum(item["pct"] for item in breakdown)
        assert total_pct == 100

        # Order by amount desc
        for i in range(len(breakdown) - 1):
            assert breakdown[i]["amount"] >= breakdown[i + 1]["amount"]


def test_get_category_breakdown_no_expenses(db_conn):
    with app.app_context():
        cursor = db_conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("No Spend 3", "none3@example.com", "hash"),
        )
        user_id = cursor.lastrowid
        db_conn.commit()
        assert get_category_breakdown(user_id) == []


# ------------------------------------------------------------------ #
# Route Tests                                                          #
# ------------------------------------------------------------------ #


def test_profile_unauthenticated(client):
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/login"


def test_profile_authenticated_seed_user(client):
    # Log in as demo user
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})

    response = client.get("/profile")
    assert response.status_code == 200

    content = response.get_data(as_text=True)
    assert "Demo User" in content
    assert "demo@spendly.com" in content
    assert "₹" in content
    assert "297.74" in content
    assert "8" in content
    assert "Bills" in content
