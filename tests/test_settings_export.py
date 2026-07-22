import csv
import io


def test_export_requires_login(client):
    resp = client.get("/expenses/export")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_export_csv_contains_only_current_user_expenses(client, make_user, make_expense, login_as):
    user_a = make_user("User A", "a@example.com", "password123")
    user_b = make_user("User B", "b@example.com", "password123")

    make_expense(user_a["id"], 10.0, "Food", "2026-07-01", "A1")
    make_expense(user_a["id"], 20.5, "Bills", "2026-07-02", "A2")
    make_expense(user_b["id"], 999.0, "Other", "2026-07-03", "B1")

    login_as(user_a["email"], user_a["password"])

    resp = client.get("/expenses/export")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"

    reader = csv.DictReader(io.StringIO(resp.get_data(as_text=True)))
    rows = list(reader)
    assert [r["description"] for r in rows] == ["A2", "A1"]


def test_change_password_logs_user_out(client, make_user, login_as):
    user = make_user("User", "u@example.com", "oldpassword")
    login_as(user["email"], user["password"])

    resp = client.post(
        "/settings",
        data={
            "current_password": "oldpassword",
            "new_password": "newpassword",
            "confirm_password": "newpassword",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    assert "password_updated=1" in resp.headers["Location"]

    resp = client.post("/login", data={"email": user["email"], "password": "oldpassword"}, follow_redirects=False)
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data

    resp = client.post("/login", data={"email": user["email"], "password": "newpassword"}, follow_redirects=False)
    assert resp.status_code == 302


def test_delete_account_deletes_user_and_expenses(client, make_user, make_expense, login_as, app):
    user = make_user("User", "del@example.com", "password123")
    expense_id = make_expense(user["id"], 12.0, "Food", "2026-07-04", "To be deleted")

    login_as(user["email"], user["password"])

    resp = client.post("/settings/delete-account", data={"password": "wrong"}, follow_redirects=False)
    assert resp.status_code == 302
    assert "/settings" in resp.headers["Location"]
    assert "delete_error=1" in resp.headers["Location"]

    resp = client.post("/settings/delete-account", data={"password": "password123"}, follow_redirects=False)
    assert resp.status_code == 302
    assert "/?" in resp.headers["Location"]
    assert "account_deleted=1" in resp.headers["Location"]

    with app.app_context():
        from database.db import get_user_by_id, get_expense_by_id

        assert get_user_by_id(user["id"]) is None
        assert get_expense_by_id(expense_id) is None

