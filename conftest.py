import pytest
import tempfile
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

@pytest.fixture(scope="session")
def app():
    """Create Flask app for testing against a temporary database."""
    # Create a temporary directory for the test DB
    temp_dir = tempfile.mkdtemp()
    temp_db = Path(temp_dir) / "test.db"

    # Monkeypatch database.db.DB_PATH before importing app
    import database.db as db_module
    db_module.DB_PATH = temp_db
    db_module.init_db()

    # Now import the app (triggers init_db() and seed_db() against temp DB)
    import app as app_module

    # Configure for testing
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret-key"

    yield app_module.app

    # Cleanup happens automatically when temp_dir is garbage collected


@pytest.fixture(scope="function")
def client(app):
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def reset_db(app):
    """Reset database before each test (clear all data except Demo User)."""
    with app.app_context():
        from database.db import get_db
        conn = get_db()
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
        conn.commit()
        conn.close()
    yield


@pytest.fixture(scope="function")
def make_user(app):
    """Factory fixture to create test users."""
    from database.db import create_user, get_db

    def _make_user(name, email, password):
        password_hash = generate_password_hash(password)
        user_id = create_user(name, email, password_hash)
        return {"id": user_id, "name": name, "email": email, "password": password}

    return _make_user


@pytest.fixture(scope="function")
def make_expense(app):
    """Factory fixture to create test expenses."""
    from database.db import get_db

    def _make_expense(user_id, amount, category, date_str, description):
        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date_str, description)
        )
        expense_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return expense_id

    return _make_expense


@pytest.fixture(scope="function")
def login_as(client):
    """Factory fixture to log in a user."""
    def _login(email, password):
        response = client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=False)
        assert response.status_code == 302, f"Login failed: {response.status_code}"
        return response

    return _login
