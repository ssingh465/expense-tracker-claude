import pytest

from app import app as flask_app
from database.db import get_db, init_db
from database.queries import get_category_breakdown, get_recent_transactions, get_summary_stats


@pytest.fixture
def app():
    flask_app.config.update(
        {
            "TESTING": True,
            "DATABASE": ":memory:",  # isolated in-memory DB per test
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with flask_app.app_context():
        init_db()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpass",
            "confirm_password": "testpass",
        },
    )
    client.post("/login", data={"email": "test@example.com", "password": "testpass"})
    return client


@pytest.fixture
def seeded_expenses(auth_client):
    """Seeds expenses across different dates for filtering tests."""
    conn = get_db()
    # Get the user id
    user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
    user_id = user["id"]

    expenses = [
        # 2026-01-01 to 2026-01-10
        (10.0, "Food", "2026-01-01", "Early Jan", user_id),
        (20.0, "Food", "2026-01-05", "Mid Jan", user_id),
        (30.0, "Transport", "2026-01-10", "Late Jan", user_id),
        # 2026-02-01 to 2026-02-10
        (40.0, "Bills", "2026-02-01", "Early Feb", user_id),
        (50.0, "Bills", "2026-02-05", "Mid Feb", user_id),
        (60.0, "Health", "2026-02-10", "Late Feb", user_id),
    ]
    conn.executemany(
        "INSERT INTO expenses (amount, category, date, description, user_id) \
            VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    return user_id


class TestDateRangeFilter:
    def test_profile_auth_guard(self, client):
        """Unauthenticated users should be redirected to login."""
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_profile_no_filter_shows_all(self, auth_client, seeded_expenses):
        """Accessing /profile without params shows all data."""
        response = auth_client.get("/profile")
        assert response.status_code == 200
        # Total: 10+20+30+40+50+60 = 210
        assert "₹210.00" in response.get_data(as_text=True)
        assert "6" in response.get_data(as_text=True)  # Transaction count

    def test_profile_custom_range_filters_data(self, auth_client, seeded_expenses):
        """Custom valid range filters all three sections."""
        # Filter for January only
        response = auth_client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert response.status_code == 200
        # Total Jan: 10+20+30 = 60
        assert "₹60.00" in response.get_data(as_text=True)
        assert "3" in response.get_data(as_text=True)  # Transaction count
        # Categories: Food (30), Transport (30)
        assert "Food" in response.get_data(as_text=True)
        assert "Transport" in response.get_data(as_text=True)
        assert "Bills" not in response.get_data(as_text=True)

    def test_profile_boundary_inclusivity(self, auth_client, seeded_expenses):
        """Expenses on the exact boundary dates should be included."""
        # Range from 2026-01-01 to 2026-01-01
        response = auth_client.get("/profile?date_from=2026-01-01&date_to=2026-01-01")
        assert "₹10.00" in response.get_data(as_text=True)
        assert "1" in response.get_data(as_text=True)

    def test_profile_malformed_date_fallback(self, auth_client, seeded_expenses):
        """Malformed dates should fallback to unfiltered view."""
        response = auth_client.get("/profile?date_from=not-a-date&date_to=2026-01-01")
        assert response.status_code == 200
        # Should show total for all (210.00)
        assert "₹210.00" in response.get_data(as_text=True)

    def test_profile_start_after_end_error(self, auth_client, seeded_expenses):
        """Start date > end date should flash error and show unfiltered view."""
        response = auth_client.get("/profile?date_from=2026-02-01&date_to=2026-01-01")
        assert response.status_code == 200
        assert "Start date must be before end date." in response.get_data(as_text=True)
        # Fallback to unfiltered
        assert "₹210.00" in response.get_data(as_text=True)

    def test_profile_no_data_in_range(self, auth_client, seeded_expenses):
        """Range with no expenses should show zeros."""
        response = auth_client.get("/profile?date_from=2025-01-01&date_to=2025-01-31")
        assert response.status_code == 200
        assert "₹0.00" in response.get_data(as_text=True)
        assert "0" in response.get_data(as_text=True)
        # Category breakdown should be empty (no category names from 
        # seed should appear in breakdown)
        assert "Food" not in response.get_data(as_text=True)

    def test_profile_html_landmarks(self, auth_client):
        """Verify presence of filter UI elements."""
        response = auth_client.get("/profile")
        assert 'type="date"' in response.get_data(as_text=True)
        assert "This Month" in response.get_data(as_text=True)
        assert "Last 3 Months" in response.get_data(as_text=True)
        assert "Last 6 Months" in response.get_data(as_text=True)
        assert "All Time" in response.get_data(as_text=True)
        assert 'name="date_from"' in response.get_data(as_text=True)
        assert 'name="date_to"' in response.get_data(as_text=True)


class TestDBDateQueries:
    """Directly tests the database query helpers to isolate SQL logic."""

    def test_get_summary_stats_filtering(self, app):
        # Setup user and data
        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("T", "t@t.com", "p")
        )
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.executemany(
            "INSERT INTO expenses (amount, category, date, user_id) VALUES (?, ?, ?, ?)",
            [
                (100.0, "A", "2026-01-01", uid),
                (200.0, "B", "2026-02-01", uid),
            ],
        )
        conn.commit()

        # Test unfiltered
        stats = get_summary_stats(uid)
        assert stats["total_spent"] == 300.0
        assert stats["transaction_count"] == 2

        # Test filtered
        stats = get_summary_stats(uid, "2026-01-01", "2026-01-15")
        assert stats["total_spent"] == 100.0
        assert stats["transaction_count"] == 1
        assert stats["top_category"] == "A"

    def test_get_recent_transactions_filtering(self, app):
        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("T", "t@t.com", "p")
        )
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.executemany(
            "INSERT INTO expenses (amount, category, date, user_id) VALUES (?, ?, ?, ?)",
            [
                (10.0, "A", "2026-01-01", uid),
                (20.0, "B", "2026-02-01", uid),
            ],
        )
        conn.commit()

        txs = get_recent_transactions(uid, date_from="2026-02-01", date_to="2026-02-28")
        assert len(txs) == 1
        assert txs[0]["amount"] == 20.0

    def test_get_category_breakdown_filtering(self, app):
        conn = get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", ("T", "t@t.com", "p")
        )
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.executemany(
            "INSERT INTO expenses (amount, category, date, user_id) VALUES (?, ?, ?, ?)",
            [
                (100.0, "Food", "2026-01-01", uid),
                (100.0, "Food", "2026-02-01", uid),
                (50.0, "Bills", "2026-02-01", uid),
            ],
        )
        conn.commit()

        # Filter for February
        breakdown = get_category_breakdown(uid, "2026-02-01", "2026-02-28")
        # Should have Food (100) and Bills (50)
        assert len(breakdown) == 2
        food_entry = next(i for i in breakdown if i["name"] == "Food")
        assert food_entry["amount"] == 100.0
        assert food_entry["pct"] == 67  # (100/150)*100 = 66.66...
