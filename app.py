import argparse
import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db, get_user_by_email, get_user_by_id, create_user, get_user_expenses, get_expense_summary, get_category_breakdown, get_user_expenses_filtered, get_expense_summary_filtered, get_category_breakdown_filtered

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if get_user_by_email(email):
        return render_template("register.html", error="An account with that email already exists.")

    password_hash = generate_password_hash(password)
    create_user(name, email, password_hash)

    return redirect(url_for("login", registered=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": get_user_by_id(user_id) if user_id else None}


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("landing"))


def get_transaction_history_context(user_id):
    # Subagent 1: Transaction history routes
    transactions = get_user_expenses(user_id)
    return {"transactions": transactions}


def get_summary_stats_context(user_id):
    # Subagent 2: Summary stats routes
    user = get_user_by_id(user_id)
    summary = get_expense_summary(user_id)

    # Format member_since
    if user and user["created_at"]:
        created = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        member_since = created.strftime("%B %Y")
    else:
        member_since = "Unknown"

    return {
        "member_since": member_since,
        "total_spent": summary["total_spent"],
        "transaction_count": summary["transaction_count"],
        "top_category": summary["top_category"],
    }


def get_category_breakdown_context(user_id):
    # Subagent 3: Category breakdown routes
    breakdown = get_category_breakdown(user_id)
    return {"categories": breakdown}


def validate_date(date_str):
    if not date_str:
        return None
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        return None


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    date_from = validate_date(date_from) if date_from else None
    date_to = validate_date(date_to) if date_to else None

    if date_from and date_to and date_from > date_to:
        date_from = None
        date_to = None

    transactions = get_user_expenses_filtered(user_id, date_from, date_to)
    summary = get_expense_summary_filtered(user_id, date_from, date_to)
    categories = get_category_breakdown_filtered(user_id, date_from, date_to)

    user = get_user_by_id(user_id)
    if user and user["created_at"]:
        created = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        member_since = created.strftime("%B %Y")
    else:
        member_since = "Unknown"

    filter_active = date_from is not None or date_to is not None
    if filter_active:
        from_str = datetime.strptime(date_from, "%Y-%m-%d").strftime("%b %d, %Y") if date_from else "start"
        to_str = datetime.strptime(date_to, "%Y-%m-%d").strftime("%b %d, %Y") if date_to else "end"
        filter_display = f"Showing expenses from {from_str} to {to_str}"
    else:
        filter_display = "Showing all expenses"

    ctx = {
        "transactions": transactions,
        "total_spent": summary["total_spent"],
        "transaction_count": summary["transaction_count"],
        "top_category": summary["top_category"],
        "categories": categories,
        "member_since": member_since,
        "date_from": date_from,
        "date_to": date_to,
        "filter_active": filter_active,
        "filter_display": filter_display,
    }
    return render_template("profile.html", **ctx)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5001")))
    args = parser.parse_args()

    app.run(debug=True, host=args.host, port=args.port)
