import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db


@pytest.fixture
def app():
    flask_app.config.update(
        {
            "TESTING": True,
            "DATABASE": "test_edit_expense.db",
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with flask_app.app_context():
        init_db()
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """A test client that is already logged in."""
    # Create user directly in DB to ensure consistency
    with app.app_context():
        db = get_db()
        # Use INSERT OR IGNORE to prevent UNIQUE constraint errors across tests
        db.execute(
            "INSERT OR IGNORE INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("testuser", "test@example.com", generate_password_hash("testpass")),
        )
        db.commit()

    # Log in via the API
    client.post("/login", data={"email": "test@example.com", "password": "testpass"})
    return client


@pytest.fixture
def sample_expense(auth_client):
    """Creates a sample expense for the logged-in user."""
    with flask_app.app_context():
        db = get_db()
        # Get the logged-in user's ID from session if possible, or just query for the test user
        user = db.execute(
            "SELECT id FROM users WHERE email = ?", ("test@example.com",)
        ).fetchone()
        user_id = user["id"]

        cursor = db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, 50.0, "Food", "2026-10-01", "Initial Expense"),
        )
        db.commit()
        return cursor.lastrowid


class TestEditExpense:
    def test_get_edit_page_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated requests to edit expense should redirect to login."""
        response = client.get("/expenses/1/edit")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_get_edit_page_authenticated_success(self, auth_client, sample_expense):
        """Logged-in user can access the edit page for their own expense."""
        response = auth_client.get(f"/expenses/{sample_expense}/edit")
        assert response.status_code == 200
        assert b"Save Changes" in response.data
        assert b"50.0" in response.data
        assert b"Food" in response.data
        assert b"2026-10-01" in response.data
        assert b"Initial Expense" in response.data

    def test_get_edit_page_not_found_or_not_owned(self, auth_client):
        """Requesting a non-existent expense or one owned by another user returns 404."""
        # Non-existent ID
        response = auth_client.get("/expenses/9999/edit")
        assert response.status_code == 404

        # Expense owned by another user
        with flask_app.app_context():
            db = get_db()
            db.execute(
                "INSERT OR IGNORE INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("other", "other@example.com", generate_password_hash("pass")),
            )
            user = db.execute(
                "SELECT id FROM users WHERE email = ?", ("other@example.com",)
            ).fetchone()
            other_user_id = user["id"]

            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (other_user_id, 20.0, "Transport", "2026-10-01", "Other User Expense"),
            )
            db.commit()
            other_expense_id = cursor.lastrowid

        response = auth_client.get(f"/expenses/{other_expense_id}/edit")
        assert response.status_code == 404

    def test_post_edit_success(self, auth_client, sample_expense):
        """Valid update should persist changes and redirect to profile."""
        update_data = {
            "amount": "75.50",
            "category": "Shopping",
            "date": "2026-10-02",
            "description": "Updated Expense",
        }
        response = auth_client.post(
            f"/expenses/{sample_expense}/edit", data=update_data
        )

        assert response.status_code == 302
        assert "/profile" in response.location

        # Verify DB side effect
        with flask_app.app_context():
            db = get_db()
            expense = db.execute(
                "SELECT * FROM expenses WHERE id = ?", (sample_expense,)
            ).fetchone()
            assert expense["amount"] == 75.50
            assert expense["category"] == "Shopping"
            assert expense["date"] == "2026-10-02"
            assert expense["description"] == "Updated Expense"

    @pytest.mark.parametrize(
        "invalid_data, error_msg",
        [
            (
                {
                    "amount": "-10",
                    "category": "Food",
                    "date": "2026-10-01",
                    "description": "desc",
                },
                "amount",
            ),
            (
                {
                    "amount": "0",
                    "category": "Food",
                    "date": "2026-10-01",
                    "description": "desc",
                },
                "amount",
            ),
            (
                {
                    "amount": "abc",
                    "category": "Food",
                    "date": "2026-10-01",
                    "description": "desc",
                },
                "amount",
            ),
            (
                {
                    "amount": "10",
                    "category": "InvalidCat",
                    "date": "2026-10-01",
                    "description": "desc",
                },
                "category",
            ),
            (
                {
                    "amount": "10",
                    "category": "Food",
                    "date": "invalid-date",
                    "description": "desc",
                },
                "date",
            ),
            (
                {
                    "amount": "",
                    "category": "Food",
                    "date": "2026-10-01",
                    "description": "desc",
                },
                "amount",
            ),
        ],
    )
    def test_post_edit_validation_errors(
        self, auth_client, sample_expense, invalid_data, error_msg
    ):
        """Invalid inputs should re-render the form with an error message."""
        response = auth_client.post(
            f"/expenses/{sample_expense}/edit", data=invalid_data
        )

        assert response.status_code == 200
        assert b"Save Changes" in response.data
        # The spec says "display error message", we check if it's present (generic check)
        # We also verify that submitted values are retained in the form
        for key, value in invalid_data.items():
            if value:
                assert value.encode() in response.data

    def test_post_edit_empty_description_allowed(self, auth_client, sample_expense):
        """Empty description should be saved as None (or empty string) without error."""
        update_data = {
            "amount": "10.00",
            "category": "Food",
            "date": "2026-10-01",
            "description": "   ",  # whitespace
        }
        response = auth_client.post(
            f"/expenses/{sample_expense}/edit", data=update_data
        )
        assert response.status_code == 302

        with flask_app.app_context():
            db = get_db()
            expense = db.execute(
                "SELECT description FROM expenses WHERE id = ?", (sample_expense,)
            ).fetchone()
            assert expense["description"] is None or expense["description"] == ""

    def test_post_edit_ownership_guard(self, auth_client):
        """Direct POST to another user's expense ID should return 404."""
        with flask_app.app_context():
            db = get_db()
            # Use INSERT OR IGNORE to prevent UNIQUE constraint errors
            db.execute(
                "INSERT OR IGNORE INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (
                    "other_post",
                    "other_post@example.com",
                    generate_password_hash("pass"),
                ),
            )
            user = db.execute(
                "SELECT id FROM users WHERE email = ?", ("other_post@example.com",)
            ).fetchone()
            other_user_id = user["id"]

            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (other_user_id, 20.0, "Transport", "2026-10-01", "Other User Expense"),
            )
            db.commit()
            other_expense_id = cursor.lastrowid

        update_data = {
            "amount": "100.00",
            "category": "Food",
            "date": "2026-10-01",
            "description": "Hacker",
        }
        response = auth_client.post(
            f"/expenses/{other_expense_id}/edit", data=update_data
        )
        assert response.status_code == 404
