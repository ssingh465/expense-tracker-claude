import os

import pytest

from app import app as flask_app
from database.db import get_db, init_db


@pytest.fixture
def app():
    # Use a temporary file instead of :memory: to ensure the DB
    # persists across different connections within the same test.
    db_file = "test_spendly.db"
    flask_app.config.update(
        {
            "TESTING": True,
            "DATABASE": db_file,
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with flask_app.app_context():
        init_db()
        yield flask_app

    # Cleanup test database after each test
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    # Registration
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpass",
            "confirm_password": "testpass",
        },
    )
    # Login
    client.post("/login", data={"email": "test@example.com", "password": "testpass"})
    return client


class TestDeleteExpense:
    def test_delete_expense_success(self, auth_client):
        """Happy path: Logged-in user deletes their own expense."""
        # 1. Setup: Create an expense for the logged-in user
        with flask_app.app_context():
            db = get_db()
            # Assuming auth_client is logged in as the first created user
            user = db.execute("SELECT id FROM users LIMIT 1").fetchone()
            user_id = user["id"]

            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (user_id, 50.0, "Food", "2023-10-01", "Lunch"),
            )
            expense_id = cursor.lastrowid
            db.commit()

        # 2. Action: Delete the expense
        response = auth_client.post(
            f"/expenses/{expense_id}/delete", follow_redirects=False
        )

        # 3. Assertions
        assert response.status_code == 302, "Should redirect after successful deletion"
        assert response.headers["Location"] == "/profile", (
            "Should redirect to profile page"
        )

        # 4. DB Side Effect: Verify expense is gone
        with flask_app.app_context():
            db = get_db()
            expense = db.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            assert expense is None, "Expense should be removed from the database"

    def test_delete_expense_unauthenticated(self, client):
        """Auth guard: Unauthenticated user is redirected to login."""
        # Setup: Create a dummy expense
        with flask_app.app_context():
            db = get_db()
            # Create a user first to satisfy FK
            cursor = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Other", "other@ex.com", "hash"),
            )
            uid = cursor.lastrowid
            cursor = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (uid, 10.0, "Other", "2023-10-01"),
            )
            eid = cursor.lastrowid
            db.commit()

        response = client.post(f"/expenses/{eid}/delete", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_delete_expense_ownership_guard(self, auth_client):
        """Ownership guard: User cannot delete another user's expense."""
        with flask_app.app_context():
            db = get_db()
            # User A (already created by auth_client)
            user_a = db.execute("SELECT id FROM users LIMIT 1").fetchone()

            # User B
            cursor_b = db.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("User B", "b@ex.com", "hash"),
            )
            user_b_id = cursor_b.lastrowid

            # Expense belonging to User B
            cursor_exp = db.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (user_b_id, 100.0, "Shopping", "2023-10-01"),
            )
            expense_id_b = cursor_exp.lastrowid
            db.commit()

        # User A attempts to delete User B's expense
        response = auth_client.post(f"/expenses/{expense_id_b}/delete")

        assert response.status_code == 404, (
            "Should return 404 if user doesn't own the expense"
        )

        # Verify expense still exists
        with flask_app.app_context():
            db = get_db()
            expense = db.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id_b,)
            ).fetchone()
            assert expense is not None, "Expense should NOT have been deleted"

    def test_delete_expense_invalid_id(self, auth_client):
        """Invalid ID: Attempting to delete non-existent ID returns 404."""
        response = auth_client.post("/expenses/99999/delete")
        assert response.status_code == 404

    def test_delete_expense_method_guard(self, auth_client):
        """Method guard: GET request to delete endpoint returns 405."""
        response = auth_client.get("/expenses/1/delete")
        assert response.status_code == 405, "GET requests should be disallowed"
