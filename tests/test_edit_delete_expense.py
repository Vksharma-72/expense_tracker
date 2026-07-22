import re

from database.db import get_db


def _snippet_after_label(text, label, window=220):
    match = re.search(re.escape(label), text, re.IGNORECASE)
    if not match:
        return None
    return text[match.end(): match.end() + window]


def test_edit_expense_updates_row_and_profile(client, make_user, make_expense, login_as):
    user = make_user("Edit User", "edit@example.com", "password123")
    login_as(user["email"], user["password"])

    expense_id = make_expense(user["id"], 10.00, "Food", "2024-02-10", "Old desc")

    resp = client.get(f"/expenses/{expense_id}/edit?next=/profile")
    assert resp.status_code == 200
    assert b"Old desc" in resp.data

    resp = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": "99.99",
            "category": "Bills",
            "date": "2024-02-11",
            "description": "New desc",
            "next": "/profile",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Expense updated successfully." in resp.data
    assert b"New desc" in resp.data

    conn = get_db()
    row = conn.execute("SELECT amount, category, date, description FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is not None
    assert float(row["amount"]) == 99.99
    assert row["category"] == "Bills"
    assert row["date"] == "2024-02-11"
    assert row["description"] == "New desc"

    body = resp.get_data(as_text=True)
    total_snippet = _snippet_after_label(body, "Total Spent")
    assert total_snippet is not None
    assert "99.99" in total_snippet

    top_snippet = _snippet_after_label(body, "Top Category")
    assert top_snippet is not None
    assert "Bills" in top_snippet


def test_delete_expense_removes_row_and_profile(client, make_user, make_expense, login_as):
    user = make_user("Delete User", "delete@example.com", "password123")
    login_as(user["email"], user["password"])

    expense_id = make_expense(user["id"], 12.34, "Food", "2024-02-10", "To delete")

    resp = client.post(
        f"/expenses/{expense_id}/delete",
        data={"next": "/profile"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Expense deleted successfully." in resp.data
    assert b"To delete" not in resp.data

    conn = get_db()
    row = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is None

