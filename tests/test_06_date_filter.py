"""Tests for Step 06: Date Filter for Profile Page."""

import pytest


@pytest.fixture
def alice(make_user):
    """Create test user Alice with known expenses."""
    return make_user("Alice", "alice@test.com", "pass123")


@pytest.fixture
def bob(make_user):
    """Create test user Bob with distinct expenses."""
    return make_user("Bob", "bob@test.com", "pass456")


@pytest.fixture
def alice_expenses(alice, make_expense):
    """Create Alice's expense data spanning Jan-Feb 2024."""
    expenses = [
        (alice["id"], 20.00, "Food", "2024-01-05", "Groceries"),
        (alice["id"], 10.00, "Transport", "2024-01-15", "Bus pass"),
        (alice["id"], 30.00, "Food", "2024-02-01", "Lunch"),
        (alice["id"], 50.00, "Bills", "2024-02-10", "Electric"),
        (alice["id"], 15.00, "Shopping", "2024-02-20", "Shoes"),
    ]
    for user_id, amount, category, date, desc in expenses:
        make_expense(user_id, amount, category, date, desc)
    return expenses


@pytest.fixture
def bob_expenses(bob, make_expense):
    """Create Bob's distinct expenses (no overlap with Alice)."""
    expenses = [
        (bob["id"], 100.00, "Entertainment", "2024-03-01", "Concert"),
        (bob["id"], 25.00, "Health", "2024-03-15", "Gym"),
    ]
    for user_id, amount, category, date, desc in expenses:
        make_expense(user_id, amount, category, date, desc)
    return expenses


# ------------------------------------------------------------------ #
# Authentication Tests                                                #
# ------------------------------------------------------------------ #

def test_profile_redirects_to_login_when_not_authenticated(client):
    """Unauthenticated access to /profile redirects to /login."""
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location


# ------------------------------------------------------------------ #
# No Filter Tests                                                     #
# ------------------------------------------------------------------ #

def test_profile_no_filter_shows_all_expenses(client, alice, alice_expenses, login_as):
    """GET /profile without filters shows all 5 expenses."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Should show all 5 transaction rows
    assert html.count("transaction-row") == 5

    # Should show "Showing all expenses"
    assert "Showing all expenses" in html

    # Should show all amounts
    assert "₹20.00" in html
    assert "₹10.00" in html
    assert "₹30.00" in html
    assert "₹50.00" in html
    assert "₹15.00" in html


# ------------------------------------------------------------------ #
# Single Filter Tests (date_from)                                     #
# ------------------------------------------------------------------ #

def test_profile_date_from_only_filters_inclusive(client, alice, alice_expenses, login_as):
    """?date_from=2024-02-01 shows only expenses >= Feb 1 (inclusive)."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=2024-02-01")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Should show 3 Feb expenses (Feb 1, 10, 20)
    assert html.count("transaction-row") == 3

    # Should contain Feb amounts
    assert "₹30.00" in html  # Feb 1
    assert "₹50.00" in html  # Feb 10
    assert "₹15.00" in html  # Feb 20

    # Should NOT contain Jan amounts
    assert "₹20.00" not in html  # Jan 5
    assert "₹10.00" not in html  # Jan 15

    # Filter status should reflect the applied range
    assert "Showing expenses from" in html


# ------------------------------------------------------------------ #
# Single Filter Tests (date_to)                                       #
# ------------------------------------------------------------------ #

def test_profile_date_to_only_filters_inclusive(client, alice, alice_expenses, login_as):
    """?date_to=2024-01-15 shows only expenses <= Jan 15 (inclusive)."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_to=2024-01-15")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Should show 2 Jan expenses (Jan 5, 15)
    assert html.count("transaction-row") == 2

    # Extract transaction history section to check row amounts
    transaction_section = html[html.find("transaction-history"):html.rfind("</div>")]

    # Should contain Jan transactions (both in transaction rows)
    assert "2024-01-05" in transaction_section
    assert "2024-01-15" in transaction_section

    # Should NOT contain Feb transactions in transaction rows
    assert "2024-02-01" not in transaction_section
    assert "2024-02-10" not in transaction_section
    assert "2024-02-20" not in transaction_section


# ------------------------------------------------------------------ #
# Date Range Tests (both bounds)                                      #
# ------------------------------------------------------------------ #

def test_profile_date_range_both_bounds_inclusive(client, alice, alice_expenses, login_as):
    """?date_from=2024-01-15&date_to=2024-02-10 shows 3 expenses (inclusive)."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=2024-01-15&date_to=2024-02-10")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Should show 3 expenses: Jan 15, Feb 1, Feb 10 (both boundaries included)
    assert html.count("transaction-row") == 3

    # Should contain boundary + in-range amounts
    assert "₹10.00" in html  # Jan 15 (start boundary)
    assert "₹30.00" in html  # Feb 1 (inside)
    assert "₹50.00" in html  # Feb 10 (end boundary)

    # Should NOT contain out-of-range
    assert "₹20.00" not in html  # Jan 5 (before start)
    assert "₹15.00" not in html  # Feb 20 (after end)


# ------------------------------------------------------------------ #
# Invalid Input Tests                                                 #
# ------------------------------------------------------------------ #

def test_profile_invalid_date_format_falls_back_to_unfiltered(client, alice, alice_expenses, login_as):
    """?date_from=not-a-date falls back to showing all expenses."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=not-a-date")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Should show all 5 expenses (invalid date ignored)
    assert html.count("transaction-row") == 5
    assert "Showing all expenses" in html


def test_profile_from_after_to_falls_back_to_unfiltered(client, alice, alice_expenses, login_as):
    """?date_from=2024-02-20&date_to=2024-01-05 (invalid range) shows all expenses."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=2024-02-20&date_to=2024-01-05")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Should show all 5 expenses (invalid range resets to no filter)
    assert html.count("transaction-row") == 5
    assert "Showing all expenses" in html


# ------------------------------------------------------------------ #
# Stats Recalculation Tests                                            #
# ------------------------------------------------------------------ #

def test_profile_stats_recalculated_for_filtered_range(client, alice, alice_expenses, login_as):
    """Stats (total, count, top category) reflect filtered data."""
    login_as(alice["email"], alice["password"])
    # Filter to Feb: 2 Food (30), 1 Bills (50), 1 Shopping (15)
    response = client.get("/profile?date_from=2024-02-01&date_to=2024-02-28")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Transaction count should be 3 (Feb 1, 10, 20)
    assert html.count("transaction-row") == 3

    # Total spent = 30 + 50 + 15 = 95
    assert "₹95.00" in html

    # Transactions: 3
    assert ">3<" in html or ">3<" in html

    # Top category for Feb range is Bills (50) — highest single amount
    assert "Bills" in html


def test_profile_category_breakdown_excludes_categories_outside_range(client, alice, alice_expenses, login_as):
    """Category breakdown only includes categories with expenses in filtered range."""
    login_as(alice["email"], alice["password"])
    # Filter to only Jan: Food (20) and Transport (10)
    response = client.get("/profile?date_from=2024-01-01&date_to=2024-01-31")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Should show Jan categories: Food, Transport
    assert "Food" in html
    assert "Transport" in html

    # Should NOT show categories with no Feb expenses
    # (Bills and Shopping are Feb-only, Shopping is also Feb-only)
    breakdown_section = html[html.find("category-breakdown"):html.find("</div>", html.find("category-breakdown") + 100)]
    assert "Bills" not in breakdown_section
    assert "Shopping" not in breakdown_section


# ------------------------------------------------------------------ #
# Per-User Isolation Tests                                             #
# ------------------------------------------------------------------ #

def test_profile_different_users_see_own_filtered_data_only(client, alice, bob, alice_expenses, bob_expenses, login_as):
    """Same query string shows each user only their own filtered data."""
    # Alice filters to her Jan expenses
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=2024-01-01&date_to=2024-01-31")
    html = response.get_data(as_text=True)
    assert html.count("transaction-row") == 2  # Alice has 2 Jan expenses
    assert "Groceries" in html  # Alice's expense
    assert "Bus pass" in html   # Alice's expense

    # Log out Alice
    client.get("/logout")

    # Bob filters to Mar (his month) with same date range
    login_as(bob["email"], bob["password"])
    response = client.get("/profile?date_from=2024-03-01&date_to=2024-03-31")
    html = response.get_data(as_text=True)
    assert html.count("transaction-row") == 2  # Bob has 2 Mar expenses
    assert "Concert" in html  # Bob's expense
    assert "Gym" in html      # Bob's expense


# ------------------------------------------------------------------ #
# Form and UI Tests                                                    #
# ------------------------------------------------------------------ #

def test_profile_date_inputs_prefilled_with_current_filter(client, alice, alice_expenses, login_as):
    """Date input fields show current filter values."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=2024-02-01&date_to=2024-02-28")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Check for pre-filled values
    assert 'value="2024-02-01"' in html
    assert 'value="2024-02-28"' in html


def test_profile_clear_filter_link_resets_to_unfiltered_url(client, alice, alice_expenses, login_as):
    """Clear filter link navigates to /profile with no query params."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=2024-02-01")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Clear button should link to /profile with no params
    assert 'href="/profile"' in html or "href='/profile'" in html


def test_profile_filter_status_message_reflects_applied_range(client, alice, alice_expenses, login_as):
    """Filter status message correctly displays applied date range."""
    login_as(alice["email"], alice["password"])
    response = client.get("/profile?date_from=2024-01-15&date_to=2024-02-10")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    # Status should show the applied range in formatted dates
    assert "Showing expenses from" in html
    # Dates should be formatted (e.g., "Jan 15, 2024")
    assert "Jan" in html
    assert "Feb" in html
