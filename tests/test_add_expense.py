import re

from database.db import get_db


def _snippet_after_label(text, label, window=200):
    match = re.search(re.escape(label), text, re.IGNORECASE)
    if not match:
        return None
    return text[match.end(): match.end() + window]


def test_add_expense_requires_login(client):
    resp = client.get("/expenses/add", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers.get("Location", "")


def test_add_expense_creates_row_and_updates_profile(client, make_user, login_as):
    user = make_user("Test User", "test@example.com", "password123")
    login_as(user["email"], user["password"])

    resp = client.post(
        "/expenses/add",
        data={
            "amount": "123.45",
            "category": "Food",
            "date": "2024-02-10",
            "description": "Coffee",
            "next": "/profile",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Expense added successfully." in resp.data
    assert b"Coffee" in resp.data
    assert b"123.45" in resp.data

    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as c, SUM(amount) as s FROM expenses WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    conn.close()
    assert row["c"] == 1
    assert float(row["s"]) == 123.45

    body = resp.get_data(as_text=True)
    snippet = _snippet_after_label(body, "Transaction Count")
    assert snippet is not None
    assert "1" in snippet

    snippet = _snippet_after_label(body, "Top Category")
    assert snippet is not None
    assert "Food" in snippet

