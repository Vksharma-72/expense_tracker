"""
Tests for Step 6: Date Filter for Profile Page.

Spec: .claude/specs/06-date-filter-profile.md

These tests are derived ONLY from the spec's "Definition of done" section.
`GET /profile` must accept optional `date_from` / `date_to` query parameters
(YYYY-MM-DD) and filter the transaction history, summary stats (total spent,
transaction count, top category), and category breakdown to that date range
(inclusive on both ends):
    - no filter               -> all expenses
    - only `date_from`        -> `date >= date_from`
    - only `date_to`          -> `date <= date_to`
    - both                    -> `date >= date_from AND date <= date_to`
Invalid dates must not crash the server (either fall back to unfiltered or
show a visible error). The applied filter must be shown, a "Clear Filter"
control must remove all filter params, filters must be bookmarkable via the
query string, and different users must only ever see their own data.

Note on DB isolation: `database/db.py:get_db()` connects to a fixed on-disk
SQLite file (no per-test override), and `init_db()` / `seed_db()` already run
once at `app.py` import time. Because of this, an autouse fixture wipes the
`expenses` and `users` tables before and after every test, and each test
creates its own users/expenses via the app's real `/register` route plus
parameterized SQL inserts for expense fixture data (there is no
`/expenses/add` route yet -- it is still a stub per CLAUDE.md).

Assertions intentionally avoid depending on exact CSS classes, currency
symbols, or label wording beyond what the spec itself names ("Total Spent",
"Transaction Count", "Top Category", "Clear Filter"), so these tests remain a
behavioral contract rather than a mirror of one particular implementation.
"""

import re
from datetime import datetime

import pytest

from app import app as flask_app
from database.db import get_db, get_user_by_email


# --------------------------------------------------------------------------- #
# DB isolation
# --------------------------------------------------------------------------- #

def _wipe_tables():
    conn = get_db()
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM users")
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def clean_db():
    """Every test starts and ends with empty users/expenses tables."""
    _wipe_tables()
    yield
    _wipe_tables()


# --------------------------------------------------------------------------- #
# App / client fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def app():
    flask_app.config.update({"TESTING": True})
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# --------------------------------------------------------------------------- #
# Fixture data helpers
# --------------------------------------------------------------------------- #

def _register(test_client, name, email, password):
    resp = test_client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=True,
    )
    assert resp.status_code == 200, f"Registration for {email} should succeed"
    user = get_user_by_email(email)
    assert user is not None, f"Registration for {email} should create a user record"
    return user["id"]


def _login(test_client, email, password):
    resp = test_client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=False
    )
    assert resp.status_code == 302, f"Login for {email} should redirect on success"
    return resp


def _insert_expense(user_id, amount, category, date_str, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_str, description),
    )
    conn.commit()
    conn.close()


# Fixed, deterministic dates chosen so every filter combination below has an
# unambiguous (no-tie) top category and a known total/count.
#
# All-time:                    total=125.00 count=4 top=Food (Food 60, Bills 50, Transport 15)
# date_from=2024-02-10:        total=105.00 count=3 top=Bills (Bills 50, Food 40, Transport 15)
# date_to=2024-02-10:          total=35.00  count=2 top=Food (Food 20, Transport 15)
# 2024-02-10..2024-03-15:      total=55.00  count=2 top=Food (Food 40, Transport 15)
# single day 2024-01-05:       total=20.00  count=1 top=Food
# breakdown 2024-01-01..2024-02-10: Food + Transport present, Bills absent
ALICE_EXPENSES = [
    # amount,   category,      date,          description
    (20.00, "Food", "2024-01-05", "Groceries Jan"),
    (15.00, "Transport", "2024-02-10", "Bus Feb"),
    (40.00, "Food", "2024-03-15", "Dinner Mar"),
    (50.00, "Bills", "2024-04-20", "Electric Apr"),
]

BOB_EXPENSES = [
    (100.00, "Entertainment", "2024-01-10", "Concert"),
]


@pytest.fixture
def alice_client(client):
    user_id = _register(client, "Alice", "alice@example.com", "password123")
    for amount, category, date_str, desc in ALICE_EXPENSES:
        _insert_expense(user_id, amount, category, date_str, desc)
    _login(client, "alice@example.com", "password123")
    return client


@pytest.fixture
def bob_client(app):
    c = app.test_client()  # separate cookie jar from alice_client
    user_id = _register(c, "Bob", "bob@example.com", "password123")
    for amount, category, date_str, desc in BOB_EXPENSES:
        _insert_expense(user_id, amount, category, date_str, desc)
    _login(c, "bob@example.com", "password123")
    return c


# --------------------------------------------------------------------------- #
# Assertion helpers (implementation-agnostic)
# --------------------------------------------------------------------------- #

def _body(resp):
    return resp.get_data(as_text=True)


def _snippet_after_label(text, label, window=150):
    """Return the text immediately following `label` (case-insensitive),
    so numeric assertions can be scoped to a specific stat rather than
    matching any number that happens to appear anywhere on the page."""
    match = re.search(re.escape(label), text, re.IGNORECASE)
    if not match:
        return None
    return text[match.end(): match.end() + window]


def _amount_variants(value):
    """Reasonable textual renderings of a currency amount, independent of
    currency symbol or decimal-place formatting choices."""
    variants = {f"{value:.2f}", str(value)}
    if float(value) == int(value):
        variants.add(str(int(value)))
        variants.add(f"{value:.1f}")
    return variants


def _date_display_variants(date_str):
    """Reasonable human-readable renderings of an ISO date string."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return {
        date_str,
        dt.strftime("%b %d, %Y"),
        dt.strftime("%B %d, %Y"),
        dt.strftime("%b %d %Y"),
        dt.strftime("%B %d %Y"),
        dt.strftime("%m/%d/%Y"),
        dt.strftime("%d/%m/%Y"),
    }


def _assert_stat(body_text, label, expected_value, msg):
    snippet = _snippet_after_label(body_text, label)
    assert snippet is not None, f"Expected a '{label}' stat label on the profile page"
    variants = _amount_variants(expected_value) if isinstance(expected_value, float) else {str(expected_value)}
    assert any(v in snippet for v in variants), msg


# --------------------------------------------------------------------------- #
# DoD 1: No filter -> all expenses
# --------------------------------------------------------------------------- #

class TestNoFilterShowsAllExpenses:
    def test_all_transactions_shown(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        body = _body(resp)
        for desc in ("Groceries Jan", "Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc in body, f"Unfiltered profile should show '{desc}'"

    def test_stats_reflect_all_expenses(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        body = _body(resp)
        _assert_stat(body, "Total Spent", 125.00, "Total spent should sum all 4 expenses (125.00)")
        _assert_stat(body, "Transaction Count", 4, "Transaction count should be 4 when unfiltered")
        _assert_stat(body, "Top Category", "Food", "Top category should be Food (60.00) when unfiltered")


# --------------------------------------------------------------------------- #
# DoD 2: date_from only -> on/after that date
# --------------------------------------------------------------------------- #

class TestDateFromOnlyFilter:
    def test_excludes_earlier_expenses_includes_later(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-10")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Groceries Jan" not in body, "Expense before date_from must be excluded"
        for desc in ("Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc in body, f"Expense on/after date_from should include '{desc}'"

    def test_stats_recalculated_for_date_from(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-10")
        assert resp.status_code == 200
        body = _body(resp)
        _assert_stat(body, "Total Spent", 105.00, "Total spent should recalculate to 105.00")
        _assert_stat(body, "Transaction Count", 3, "Transaction count should recalculate to 3")
        _assert_stat(body, "Top Category", "Bills", "Top category should recalculate to Bills (50.00)")


# --------------------------------------------------------------------------- #
# DoD 3: date_to only -> on/before that date
# --------------------------------------------------------------------------- #

class TestDateToOnlyFilter:
    def test_excludes_later_expenses_includes_earlier(self, alice_client):
        resp = alice_client.get("/profile?date_to=2024-02-10")
        assert resp.status_code == 200
        body = _body(resp)
        for desc in ("Dinner Mar", "Electric Apr"):
            assert desc not in body, f"Expense after date_to should be excluded: '{desc}'"
        for desc in ("Groceries Jan", "Bus Feb"):
            assert desc in body, f"Expense on/before date_to should include '{desc}'"

    def test_stats_recalculated_for_date_to(self, alice_client):
        resp = alice_client.get("/profile?date_to=2024-02-10")
        assert resp.status_code == 200
        body = _body(resp)
        _assert_stat(body, "Total Spent", 35.00, "Total spent should recalculate to 35.00")
        _assert_stat(body, "Transaction Count", 2, "Transaction count should recalculate to 2")
        _assert_stat(body, "Top Category", "Food", "Top category should recalculate to Food (20.00 vs 15.00)")


# --------------------------------------------------------------------------- #
# DoD 4: both date_from and date_to -> inclusive range
# --------------------------------------------------------------------------- #

class TestDateRangeFilter:
    def test_only_expenses_within_range_shown(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-10&date_to=2024-03-15")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Groceries Jan" not in body, "Expense before range must be excluded"
        assert "Electric Apr" not in body, "Expense after range must be excluded"
        assert "Bus Feb" in body, "Expense at start boundary of range should be included"
        assert "Dinner Mar" in body, "Expense at end boundary of range should be included"

    def test_stats_recalculated_for_range(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-10&date_to=2024-03-15")
        assert resp.status_code == 200
        body = _body(resp)
        _assert_stat(body, "Total Spent", 55.00, "Total spent should be 55.00 for this range")
        _assert_stat(body, "Transaction Count", 2, "Transaction count should be 2 for this range")
        _assert_stat(body, "Top Category", "Food", "Top category should be Food (40.00 vs 15.00) for this range")

    def test_boundaries_are_inclusive_on_both_ends(self, alice_client):
        # date_from == date_to == an expense's exact date must include that expense.
        resp = alice_client.get("/profile?date_from=2024-01-05&date_to=2024-01-05")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Groceries Jan" in body, "Expense exactly on date_from == date_to must be included"
        for desc in ("Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc not in body, f"'{desc}' must be excluded from a single-day range that doesn't contain it"


# --------------------------------------------------------------------------- #
# DoD 5: currently applied filter is displayed
# --------------------------------------------------------------------------- #

class TestAppliedFilterIsDisplayed:
    def test_unfiltered_view_indicates_all_expenses_or_no_filter(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        body = _body(resp).lower()
        assert "all expenses" in body or "no filter" in body, (
            "Page should indicate all expenses are shown / no filter applied "
            "when date_from and date_to are absent"
        )

    def test_applied_filter_dates_are_shown_on_page(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-10&date_to=2024-03-15")
        assert resp.status_code == 200
        body = _body(resp)
        from_variants = _date_display_variants("2024-02-10")
        to_variants = _date_display_variants("2024-03-15")
        assert any(v in body for v in from_variants), "Applied date_from should be shown somewhere on the page"
        assert any(v in body for v in to_variants), "Applied date_to should be shown somewhere on the page"


# --------------------------------------------------------------------------- #
# DoD 6: Clear Filter removes all filter parameters
# --------------------------------------------------------------------------- #

class TestClearFilter:
    def test_clear_filter_control_present_when_filtered(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-10&date_to=2024-03-15")
        assert resp.status_code == 200
        body = _body(resp).lower()
        assert "clear" in body, "A 'Clear Filter' control should be present when a filter is applied"

    def test_clear_filter_link_points_back_to_unfiltered_profile(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-02-10&date_to=2024-03-15")
        assert resp.status_code == 200
        assert 'href="/profile"' in resp.get_data(as_text=True), (
            "Clear Filter control should link back to /profile with no query parameters"
        )

    def test_visiting_plain_profile_after_filter_shows_all_again(self, alice_client):
        filtered = alice_client.get("/profile?date_from=2024-02-10&date_to=2024-03-15")
        assert filtered.status_code == 200
        cleared = alice_client.get("/profile")
        assert cleared.status_code == 200
        body = _body(cleared)
        for desc in ("Groceries Jan", "Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc in body, f"After clearing the filter, '{desc}' should be visible again"


# --------------------------------------------------------------------------- #
# DoD 7, 8, 9: stats recalculated for filtered data only
# (dedicated regression tests beyond the per-filter classes above)
# --------------------------------------------------------------------------- #

class TestStatsUseFilteredDataOnly:
    def test_total_spent_changes_between_filters(self, alice_client):
        unfiltered = _body(alice_client.get("/profile"))
        filtered = _body(alice_client.get("/profile?date_from=2024-02-10"))
        _assert_stat(unfiltered, "Total Spent", 125.00, "Unfiltered total should be 125.00")
        _assert_stat(filtered, "Total Spent", 105.00, "Filtered total should drop to 105.00")

    def test_transaction_count_changes_between_filters(self, alice_client):
        unfiltered = _body(alice_client.get("/profile"))
        filtered = _body(alice_client.get("/profile?date_to=2024-02-10"))
        _assert_stat(unfiltered, "Transaction Count", 4, "Unfiltered count should be 4")
        _assert_stat(filtered, "Transaction Count", 2, "Filtered count should drop to 2")

    def test_top_category_changes_between_filters(self, alice_client):
        unfiltered = _body(alice_client.get("/profile"))
        filtered = _body(alice_client.get("/profile?date_from=2024-02-10"))
        _assert_stat(unfiltered, "Top Category", "Food", "Unfiltered top category should be Food")
        _assert_stat(filtered, "Top Category", "Bills", "Filtered top category should change to Bills")

    def test_zero_matching_expenses_yields_zero_stats(self, alice_client):
        resp = alice_client.get("/profile?date_from=2030-01-01")
        assert resp.status_code == 200
        body = _body(resp)
        for desc in ("Groceries Jan", "Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc not in body, f"'{desc}' should not appear for a filter matching zero expenses"
        _assert_stat(body, "Total Spent", 0.00, "Total spent should be 0.00 when nothing matches the filter")
        _assert_stat(body, "Transaction Count", 0, "Transaction count should be 0 when nothing matches the filter")


# --------------------------------------------------------------------------- #
# DoD 10: category breakdown only shows categories with expenses in range
# --------------------------------------------------------------------------- #

class TestCategoryBreakdown:
    def test_all_categories_present_when_unfiltered(self, alice_client):
        resp = alice_client.get("/profile")
        assert resp.status_code == 200
        body = _body(resp)
        for category in ("Food", "Transport", "Bills"):
            assert category in body, f"Category '{category}' should appear in unfiltered breakdown"

    def test_categories_without_expenses_in_range_are_excluded(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-01-01&date_to=2024-02-10")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Food" in body, "Food had an expense in Jan and should appear in the breakdown"
        assert "Transport" in body, "Transport had an expense on Feb 10 and should appear in the breakdown"
        assert "Bills" not in body, "Bills has zero expenses in Jan 1 - Feb 10 and must be excluded"


# --------------------------------------------------------------------------- #
# DoD 11: transaction history shows only expenses in filtered range
# --------------------------------------------------------------------------- #

class TestTransactionHistoryFiltering:
    def test_only_expenses_in_range_are_listed(self, alice_client):
        resp = alice_client.get("/profile?date_from=2024-03-01")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Dinner Mar" in body
        assert "Electric Apr" in body
        assert "Groceries Jan" not in body
        assert "Bus Feb" not in body

    def test_expense_outside_range_never_appears(self, alice_client):
        resp = alice_client.get("/profile?date_to=2024-01-31")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Groceries Jan" in body
        for desc in ("Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc not in body


# --------------------------------------------------------------------------- #
# DoD 12: invalid date format is handled gracefully
# --------------------------------------------------------------------------- #

class TestInvalidDateHandling:
    def _fallback_or_error(self, resp):
        assert resp.status_code in (200, 400), "Invalid date input must never cause a server error (500)"
        if resp.status_code == 200:
            body = _body(resp).lower()
            fell_back_to_all = "groceries jan" in body and "electric apr" in body
            showed_error = "invalid" in body or "error" in body
            assert fell_back_to_all or showed_error, (
                "Invalid date input should either fall back to the unfiltered view "
                "or show a visible error"
            )

    def test_non_date_string_in_date_from(self, alice_client):
        self._fallback_or_error(alice_client.get("/profile?date_from=not-a-date"))

    def test_non_date_string_in_date_to(self, alice_client):
        self._fallback_or_error(alice_client.get("/profile?date_to=also-not-a-date"))

    def test_malformed_date_with_wrong_separators(self, alice_client):
        self._fallback_or_error(alice_client.get("/profile?date_from=2024/02/10"))

    def test_date_from_after_date_to(self, alice_client):
        self._fallback_or_error(alice_client.get("/profile?date_from=2024-04-20&date_to=2024-01-05"))


# --------------------------------------------------------------------------- #
# DoD 13: date filter parameters are persistent / bookmarkable
# --------------------------------------------------------------------------- #

class TestFilterIsBookmarkable:
    def test_revisiting_same_filtered_url_gives_identical_result(self, alice_client):
        url = "/profile?date_from=2024-02-10&date_to=2024-03-15"
        first = alice_client.get(url)
        second = alice_client.get(url)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.data == second.data, "Revisiting the same filtered URL should yield the same result"

    def test_filtered_url_works_as_a_fresh_direct_request(self, app):
        """Simulates a bookmarked/shared URL being opened directly rather than
        navigated to via the filter form."""
        c = app.test_client()
        user_id = _register(c, "Carol", "carol@example.com", "password123")
        for amount, category, date_str, desc in ALICE_EXPENSES:
            _insert_expense(user_id, amount, category, date_str, desc)
        _login(c, "carol@example.com", "password123")

        resp = c.get("/profile?date_from=2024-02-10")
        assert resp.status_code == 200
        body = _body(resp)
        assert "Groceries Jan" not in body
        assert "Bus Feb" in body


# --------------------------------------------------------------------------- #
# DoD 14: different users see different filtered data
# --------------------------------------------------------------------------- #

class TestMultiUserIsolation:
    def test_unfiltered_profiles_show_only_own_expenses(self, alice_client, bob_client):
        alice_resp = alice_client.get("/profile")
        bob_resp = bob_client.get("/profile")
        assert alice_resp.status_code == 200
        assert bob_resp.status_code == 200

        assert "Groceries Jan" in _body(alice_resp), "Alice should see her own expenses"
        assert "Concert" not in _body(alice_resp), "Alice must not see Bob's expenses"

        assert "Concert" in _body(bob_resp), "Bob should see his own expenses"
        assert "Groceries Jan" not in _body(bob_resp), "Bob must not see Alice's expenses"

    def test_same_filter_yields_different_data_per_user(self, alice_client, bob_client):
        alice_resp = alice_client.get("/profile?date_from=2024-01-01&date_to=2024-01-31")
        bob_resp = bob_client.get("/profile?date_from=2024-01-01&date_to=2024-01-31")
        assert alice_resp.status_code == 200
        assert bob_resp.status_code == 200

        assert "Groceries Jan" in _body(alice_resp), "Alice's January expense should appear in her filtered view"
        assert "Concert" not in _body(alice_resp), "Bob's data must not leak into Alice's filtered view"

        assert "Concert" in _body(bob_resp), "Bob's January expense should appear in his filtered view"
        assert "Groceries Jan" not in _body(bob_resp), "Alice's data must not leak into Bob's filtered view"

    def test_bob_stats_reflect_only_his_own_expense(self, bob_client):
        resp = bob_client.get("/profile")
        assert resp.status_code == 200
        body = _body(resp)
        _assert_stat(body, "Total Spent", 100.00, "Bob's total spent should be 100.00 (only his expense)")
        _assert_stat(body, "Transaction Count", 1, "Bob's transaction count should be 1")
        _assert_stat(body, "Top Category", "Entertainment", "Bob's top category should be Entertainment")


# --------------------------------------------------------------------------- #
# DoD 15: all SQL queries use parameterized placeholders (black-box proof)
# --------------------------------------------------------------------------- #

class TestParameterizedQuerySafety:
    """We cannot read app.py/database/db.py to check for `?` placeholders
    directly (per task rules), so we verify the *externally observable*
    guarantee that parameterized queries provide: malicious input in the
    date filter is treated as inert data, never as SQL, so it can't corrupt
    the database or leak data across users."""

    def test_sql_injection_attempt_in_date_from_does_not_leak_other_users_data(
        self, alice_client, bob_client
    ):
        payload = "2024-01-01' OR '1'='1"
        resp = alice_client.get(f"/profile?date_from={payload}")
        assert resp.status_code in (200, 400), "Malicious date_from input must not cause a server error"
        if resp.status_code == 200:
            assert "Concert" not in _body(resp), "Malicious input must never expose another user's data"

    def test_sql_injection_attempt_in_date_to_does_not_leak_other_users_data(
        self, alice_client, bob_client
    ):
        payload = "2024-12-31' OR '1'='1"
        resp = alice_client.get(f"/profile?date_to={payload}")
        assert resp.status_code in (200, 400), "Malicious date_to input must not cause a server error"
        if resp.status_code == 200:
            assert "Concert" not in _body(resp), "Malicious input must never expose another user's data"

    def test_sql_injection_attempt_does_not_corrupt_or_drop_data(self, alice_client):
        malicious = "2024-01-01'; DROP TABLE expenses; --"
        resp = alice_client.get(f"/profile?date_from={malicious}")
        assert resp.status_code in (200, 400), "Malicious input must not cause a server error"

        # The expenses table (and Alice's rows) must remain fully intact,
        # proving the input was never concatenated into executable SQL.
        follow_up = alice_client.get("/profile")
        assert follow_up.status_code == 200
        body = _body(follow_up)
        for desc in ("Groceries Jan", "Bus Feb", "Dinner Mar", "Electric Apr"):
            assert desc in body, (
                f"'{desc}' must still be present after an injection attempt -- "
                "the expenses table must not have been altered"
            )


# --------------------------------------------------------------------------- #
# Bonus: auth guard on the (modified) /profile route
# --------------------------------------------------------------------------- #

class TestAuthGuard:
    def test_unauthenticated_profile_redirects_to_login(self, client):
        resp = client.get("/profile", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")

    def test_unauthenticated_filtered_profile_redirects_to_login(self, client):
        resp = client.get(
            "/profile?date_from=2024-01-01&date_to=2024-12-31", follow_redirects=False
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")
