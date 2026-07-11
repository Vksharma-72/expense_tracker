"""
Tests for Step 6: Date Filter for Profile Page.

Spec: .claude/specs/06-date-filter-profile.md

`GET /profile` accepts optional `date_from` / `date_to` query params
(YYYY-MM-DD) and filters the transaction history, summary stats (total
spent, transaction count, top category), and category breakdown to that
range (inclusive on both ends). No filter -> all expenses. Only `date_from`
-> `date >= date_from`. Only `date_to` -> `date <= date_to`. Invalid dates or
`date_from > date_to` must be handled gracefully (no crash): either fall
back to the unfiltered view or show a visible error.

Note on DB isolation: `database/db.py:get_db()` always connects to a fixed
on-disk SQLite file (no `app.config['DATABASE']` override), and `init_db()` /
`seed_db()` already run once at `app.py` import time. Because of this, we
cannot swap in a fresh in-memory DB per test. Instead, an autouse fixture
wipes the `expenses` and `users` tables before and after every test, and
each test inserts its own known fixture rows via parameterized SQL.
"""

from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db

import pytest


# --------------------------------------------------------------------------- #
# DB isolation + fixture helpers
# --------------------------------------------------------------------------- #

def _wipe_tables():
    conn = get_db()
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe expenses/users before and after every test for isolation."""
    _wipe_tables()
    yield
    _wipe_tables()


@pytest.fixture
def app():
    flask_app.config.update({"TESTING": True})
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def _create_user(name, email, password):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def _add_expense(user_id, amount, category, date_str, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_str, description),
    )
    conn.commit()
    conn.close()


# Alice's fixture expenses, chosen so every filter combination below has a
# single, unambiguous top category (no ties) and known totals.
ALICE_EXPENSES = [
    # amount,  category,     date,          description
    (20.00, "Food", "2024-01-05", "Groceries Jan"),
    (15.00, "Transport", "2024-02-10", "Bus Feb"),
    (40.00, "Food", "2024-03-15", "Dinner Mar"),
    (50.00, "Bills", "2024-04-20", "Electric Apr"),
]
# All-time:                total=125.00 count=4 top=Food   (Food 60, Bills 50, Transport 15)
# date_from=2024-02-01:    total=105.00 count=3 top=Bills  (Bills 50, Food 40, Transport 15)
# date_to=2024-02-28:      total=35.00  count=2 top=Food   (Food 20, Transport 15)
# 2024-02-01..2024-03-31:  total=55.00  count=2 top=Food   (Food 40, Transport 15)
# breakdown 2024-01-01..2024-02-28: {Food: 20.0, Transport: 15.0} -- no Bills

BOB_EXPENSES = [
    (100.00, "Entertainment", "2024-01-10", "Concert"),
]


@pytest.fixture
def alice(client):
    user_id = _create_user("Alice", "alice@example.com", "password123")
    for amount, category, date_str, desc in ALICE_EXPENSES:
        _add_expense(user_id, amount, category, date_str, desc)
    return user_id


@pytest.fixture
def bob(client):
    user_id = _create_user("Bob", "bob@example.com", "password123")
    for amount, category, date_str, desc in BOB_EXPENSES:
        _add_expense(user_id, amount, category, date_str, desc)
    return user_id


@pytest.fixture
def alice_client(client, alice):
    resp = client.post(
        "/login", data={"email": "alice@example.com", "password": "password123"}
    )
    assert resp.status_code in (200, 302), "Alice login setup failed"
    return client


@pytest.fixture
def bob_client(app, bob):
    c = app.test_client()  # separate cookie jar from alice_client
    resp = c.post(
        "/login", data={"email": "bob@example.com", "password": "password123"}
    )
    assert resp.status_code in (200, 302), "Bob login setup failed"
    return c


# --------------------------------------------------------------------------- #
# 1. No filter (default behavior)
# --------------------------------------------------------------------------- #

class TestNoFilter:
    def test_no_filter_shows_all_transactions(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200, "Profile page should load without a filter"
        for desc in ("Groceries Jan", "Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc.encode() in resp.data, f"Expected unfiltered transaction '{desc}' to be shown"

    def test_no_filter_stats_reflect_all_expenses(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        assert b'<div class="stat-value">\xe2\x82\xb9125.00</div>' in resp.data, \
            "Total spent stat should be the sum of all 4 expenses (₹125.00)"
        assert b'<div class="stat-value">4</div>' in resp.data, \
            "Transaction count stat should be 4 when unfiltered"
        assert b'<div class="stat-value">Food</div>' in resp.data, \
            "Top category stat should be Food (highest total, 60.00) when unfiltered"

    def test_no_filter_shows_no_filter_indicator(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        body = resp.data.lower()
        assert b"all expenses" in body or b"no filter" in body, \
            "Page should indicate that all expenses are shown when no filter is applied"


# --------------------------------------------------------------------------- #
# 2. Single filter: date_from
# --------------------------------------------------------------------------- #

class TestDateFromFilter:
    def test_date_from_excludes_earlier_expenses(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-01")
        assert resp.status_code == 200
        assert b"Groceries Jan" not in resp.data, "Expense before date_from must be excluded"
        for desc in ("Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc.encode() in resp.data, f"Expense on/after date_from should include '{desc}'"

    def test_date_from_stats_recalculated(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-01")
        assert resp.status_code == 200
        assert b'<div class="stat-value">\xe2\x82\xb9105.00</div>' in resp.data, \
            "Total spent stat should be recalculated to ₹105.00 for date_from filter"
        assert b'<div class="stat-value">3</div>' in resp.data, \
            "Transaction count stat should be 3 for date_from filter"
        assert b'<div class="stat-value">Bills</div>' in resp.data, \
            "Top category stat should be Bills (50.00) for this filtered range"


# --------------------------------------------------------------------------- #
# 3. Single filter: date_to
# --------------------------------------------------------------------------- #

class TestDateToFilter:
    def test_date_to_excludes_later_expenses(self, alice_client):
        resp = alice_client.get("/profile?date_to=2024-02-28")
        assert resp.status_code == 200
        for desc in ("Dinner Mar", "Electric Apr"):
            assert desc.encode() not in resp.data, f"Expense after date_to should be excluded: '{desc}'"
        for desc in ("Groceries Jan", "Bus Feb"):
            assert desc.encode() in resp.data, f"Expense on/before date_to should include '{desc}'"

    def test_date_to_stats_recalculated(self, alice_client):
        resp = alice_client.get("/profile?date_to=2024-02-28")
        assert resp.status_code == 200
        assert b'<div class="stat-value">\xe2\x82\xb935.00</div>' in resp.data, \
            "Total spent stat should be recalculated to ₹35.00 for date_to filter"
        assert b'<div class="stat-value">2</div>' in resp.data, \
            "Transaction count stat should be 2 for date_to filter"
        assert b'<div class="stat-value">Food</div>' in resp.data, \
            "Top category stat should be Food (20.00 vs Transport 15.00) for this filtered range"


# --------------------------------------------------------------------------- #
# 4. Date range filter (both date_from and date_to)
# --------------------------------------------------------------------------- #

class TestDateRangeFilter:
    def test_range_filter_shows_only_expenses_in_range(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-01&date_to=2024-03-31")
        assert resp.status_code == 200
        assert b"Groceries Jan" not in resp.data, "Expense before range must be excluded"
        assert b"Electric Apr" not in resp.data, "Expense after range must be excluded"
        assert b"Bus Feb" in resp.data, "Expense inside range should be shown"
        assert b"Dinner Mar" in resp.data, "Expense inside range should be shown"

    def test_range_filter_stats_recalculated(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-01&date_to=2024-03-31")
        assert resp.status_code == 200
        assert b'<div class="stat-value">\xe2\x82\xb955.00</div>' in resp.data, \
            "Total spent stat should be ₹55.00 for the Feb-Mar range"
        assert b'<div class="stat-value">2</div>' in resp.data, \
            "Transaction count stat should be 2 for the Feb-Mar range"
        assert b'<div class="stat-value">Food</div>' in resp.data, \
            "Top category stat should be Food (40.00 vs Transport 15.00) for the Feb-Mar range"

    def test_range_boundaries_are_inclusive(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-01-05&date_to=2024-01-05")
        assert resp.status_code == 200
        assert b"Groceries Jan" in resp.data, "Expense exactly on date_from == date_to should be included"
        for desc in ("Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc.encode() not in resp.data, f"'{desc}' should be outside the single-day range"


# --------------------------------------------------------------------------- #
# 5. Invalid dates
# --------------------------------------------------------------------------- #

class TestInvalidDates:
    def test_invalid_date_format_does_not_crash(self, alice_client):
        resp = alice_client.get("/profile?date_from=not-a-date")
        assert resp.status_code in (200, 400), \
            "Invalid date format must not cause a server error (500)"
        if resp.status_code == 200:
            body = resp.data.lower()
            fell_back_to_all = b"groceries jan" in body and b"electric apr" in body
            showed_error = b"invalid" in body or b"error" in body
            assert fell_back_to_all or showed_error, \
                "Invalid date should either fall back to the unfiltered view or show an error"

    def test_date_from_after_date_to_handled_gracefully(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-04-20&date_to=2024-01-05")
        assert resp.status_code in (200, 400), \
            "date_from > date_to must not cause a server error (500)"
        if resp.status_code == 200:
            body = resp.data.lower()
            fell_back_to_all = b"groceries jan" in body and b"electric apr" in body
            showed_error = b"invalid" in body or b"error" in body
            assert fell_back_to_all or showed_error, \
                "date_from > date_to should either be ignored (show all) or show an error"

    def test_filter_with_no_matching_expenses_renders_without_error(self, alice_client):
        resp = alice_client.get("/profile?date_from=2030-01-01")
        assert resp.status_code == 200, \
            "A filter that matches zero expenses should still render the page (200), not error"
        for desc in ("Groceries Jan", "Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc.encode() not in resp.data, f"'{desc}' should not appear for a future-only filter"
        assert b'<div class="stat-value">\xe2\x82\xb90.00</div>' in resp.data, \
            "Total spent stat should be ₹0.00 when no expenses match the filter"
        assert b'<div class="stat-value">0</div>' in resp.data, \
            "Transaction count stat should be 0 when no expenses match the filter"


# --------------------------------------------------------------------------- #
# 6. Authentication
# --------------------------------------------------------------------------- #

class TestAuthentication:
    def test_profile_redirects_to_login_when_unauthenticated(self, client):
        resp = client.get("/profile", follow_redirects=False)
        assert resp.status_code == 302, "Unauthenticated /profile access should redirect"
        assert "/login" in resp.headers.get("Location", ""), \
            "Unauthenticated /profile access should redirect to /login"

    def test_profile_with_filter_redirects_to_login_when_unauthenticated(self, client):
        resp = client.get("/profile?date_from=2024-01-01&date_to=2024-12-31", follow_redirects=False)
        assert resp.status_code == 302, "Unauthenticated filtered /profile access should redirect"
        assert "/login" in resp.headers.get("Location", ""), \
            "Unauthenticated filtered /profile access should redirect to /login"

    def test_different_users_see_different_filtered_data(self, alice_client, bob_client):
        alice_resp = alice_client.get("/profile")
        bob_resp = bob_client.get("/profile")

        assert alice_resp.status_code == 200
        assert bob_resp.status_code == 200

        assert b"Groceries Jan" in alice_resp.data, "Alice should see her own expenses"
        assert b"Concert" not in alice_resp.data, "Alice must not see Bob's expenses"

        assert b"Concert" in bob_resp.data, "Bob should see his own expenses"
        assert b"Groceries Jan" not in bob_resp.data, "Bob must not see Alice's expenses"
        assert b'<div class="stat-value">\xe2\x82\xb9100.00</div>' in bob_resp.data, \
            "Bob's total spent stat should reflect only his own expense (₹100.00)"

    def test_different_users_see_different_filtered_data_with_query_params(self, alice_client, bob_client):
        alice_resp = alice_client.get("/profile?date_from=2024-01-01&date_to=2024-01-31")
        bob_resp = bob_client.get("/profile?date_from=2024-01-01&date_to=2024-01-31")

        assert alice_resp.status_code == 200
        assert bob_resp.status_code == 200
        assert b"Groceries Jan" in alice_resp.data, "Alice's January expense should appear in her filtered view"
        assert b"Concert" not in alice_resp.data, "Bob's data must not leak into Alice's filtered view"
        assert b"Concert" in bob_resp.data, "Bob's January expense should appear in his filtered view"
        assert b"Groceries Jan" not in bob_resp.data, "Alice's data must not leak into Bob's filtered view"


# --------------------------------------------------------------------------- #
# 7. Category breakdown
# --------------------------------------------------------------------------- #

class TestCategoryBreakdown:
    def test_breakdown_includes_all_categories_when_unfiltered(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        for category in ("Food", "Transport", "Bills"):
            assert category.encode() in resp.data, f"Category '{category}' should appear in unfiltered breakdown"

    def test_breakdown_excludes_categories_with_no_expenses_in_range(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-01-01&date_to=2024-02-28")
        assert resp.status_code == 200
        assert b"Food" in resp.data, "Food had an expense in Jan and should appear in the breakdown"
        assert b"Transport" in resp.data, "Transport had an expense in Feb and should appear in the breakdown"
        assert b"Bills" not in resp.data, \
            "Bills has zero expenses in Jan-Feb range and must be excluded from the breakdown"


# --------------------------------------------------------------------------- #
# 8. Form and UI
# --------------------------------------------------------------------------- #

class TestFormAndUI:
    def test_date_inputs_have_correct_name_attributes(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        assert b'name="date_from"' in resp.data, "date_from input must have name='date_from' for query binding"
        assert b'name="date_to"' in resp.data, "date_to input must have name='date_to' for query binding"

    def test_date_inputs_prefilled_with_current_filter_values(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-01&date_to=2024-03-31")
        assert resp.status_code == 200
        assert b'value="2024-02-01"' in resp.data, "date_from input should be pre-filled with the applied value"
        assert b'value="2024-03-31"' in resp.data, "date_to input should be pre-filled with the applied value"

    def test_date_inputs_not_prefilled_when_no_filter(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        assert b'value="2024-02-01"' not in resp.data, "date_from input should not have a stale/leftover value"
        assert b'value="2024-03-31"' not in resp.data, "date_to input should not have a stale/leftover value"

    def test_clear_filter_link_resets_to_no_parameters(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-01&date_to=2024-03-31")
        assert resp.status_code == 200
        body_lower = resp.data.lower()
        assert b"clear" in body_lower, "A 'Clear' filter control should be present on the filtered page"
        assert b'href="/profile"' in resp.data, \
            "Clear filter link should point back to /profile with no query parameters"

    def test_filter_query_params_are_bookmarkable(self, alice_client):
        """The same filtered URL should return the same filtered result on repeat visits."""
        url = "/profile?date_from=2024-02-01&date_to=2024-03-31"
        first = alice_client.get(url)
        second = alice_client.get(url)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.data == second.data, "Revisiting the same filtered URL should yield the same result"
