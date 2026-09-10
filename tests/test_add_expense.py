import pytest
import os
import tempfile
from app import app as flask_app
from database.db import init_db, get_db


@pytest.fixture
def app():
    # Use a temporary file for the database to ensure all connections
    # within the test see the same data.
    db_fd, db_path = tempfile.mkstemp()
    try:
        flask_app.config.update({
            'TESTING': True,
            'DATABASE': db_path,
            'SECRET_KEY': 'test-secret',
            'WTF_CSRF_ENABLED': False,
        })
        with flask_app.app_context():
            init_db()
            yield flask_app
    finally:
        os.close(db_fd)
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    # Register a user first since the DB is in-memory and empty
    client.post('/register', data={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'testpass',
        'confirm_password': 'testpass'
    })
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    return client

class TestAddExpense:
    def test_add_expense_get_unauthenticated_redirects_to_login(self, client):
        """GET /expenses/add should redirect unauthenticated users to login."""
        response = client.get('/expenses/add')
        assert response.status_code == 302
        assert response.location.endswith('/login')

    def test_add_expense_post_unauthenticated_redirects_to_login(self, client):
        """POST /expenses/add should redirect unauthenticated users to login."""
        response = client.post('/expenses/add', data={'amount': '100', 'category': 'Food', 'date': '2023-01-01'})
        assert response.status_code == 302
        assert response.location.endswith('/login')

    def test_add_expense_page_renders_for_auth_user(self, auth_client):
        """GET /expenses/add should render the form for authenticated users."""
        response = auth_client.get('/expenses/add')
        assert response.status_code == 200
        assert b'Add Expense' in response.data
        assert b'amount' in response.data
        assert b'category' in response.data
        assert b'date' in response.data

    def test_add_expense_success_redirects_and_saves(self, auth_client, app):
        """Valid expense submission should save to DB and redirect to profile."""
        expense_data = {
            'amount': '150.50',
            'category': 'Food',
            'date': '2023-10-27',
            'description': 'Dinner at a nice restaurant'
        }

        response = auth_client.post('/expenses/add', data=expense_data, follow_redirects=False)

        # Check redirect and flash message
        assert response.status_code == 302
        assert response.location.endswith('/profile')

        # Verify DB side effect
        with app.app_context():
            db = get_db()
            # We need to find the user_id from the session
            with auth_client.session_transaction() as sess:
                user_id = sess['user_id']

            expense = db.execute(
                "SELECT amount, category, date, description FROM expenses WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            assert expense is not None
            assert float(expense[0]) == 150.50
            assert expense[1] == 'Food'
            assert expense[2] == '2023-10-27'
            assert expense[3] == 'Dinner at a nice restaurant'

    @pytest.mark.parametrize("amount, category, date, description, expected_error", [
        # Missing fields
        ('', 'Food', '2023-10-27', 'Desc', 'Amount, category, and date are required.'),
        ('100', '', '2023-10-27', 'Desc', 'Amount, category, and date are required.'),
        ('100', 'Food', '', 'Desc', 'Amount, category, and date are required.'),

        # Invalid amount
        ('-10', 'Food', '2023-10-27', 'Desc', 'Please enter a valid positive amount.'),
        ('0', 'Food', '2023-10-27', 'Desc', 'Please enter a valid positive amount.'),
        ('abc', 'Food', '2023-10-27', 'Desc', 'Please enter a valid positive amount.'),

        # Invalid category
        ('100', 'Luxury', '2023-10-27', 'Desc', 'Invalid category selected.'),
        ('100', 'Unknown', '2023-10-27', 'Desc', 'Invalid category selected.'),

        # Invalid date
        ('100', 'Food', '27-10-2023', 'Desc', 'Please enter a valid date.'),
        ('100', 'Food', 'not-a-date', 'Desc', 'Please enter a valid date.'),

        # Description too long
        ('100', 'Food', '2023-10-27', 'a' * 201, 'Description must be 200 characters or less.'),
    ])
    def test_add_expense_invalid_input_shows_error(self, auth_client, amount, category, date, description, expected_error):
        """Various invalid inputs should re-render form and show error message."""
        data = {
            'amount': amount,
            'category': category,
            'date': date,
            'description': description
        }

        response = auth_client.post('/expenses/add', data=data)

        assert response.status_code == 200
        assert expected_error.encode() in response.data
        # Ensure we are still on the add_expense page
        assert b'Add Expense' in response.data
