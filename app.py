import argparse
import csv
import io
import os
import secrets
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlparse, parse_qs

from flask import Flask, render_template, request, redirect, url_for, session, Response, abort
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    get_user_by_id,
    create_user,
    get_user_expenses,
    get_expense_summary,
    get_category_breakdown,
    get_user_expenses_filtered,
    get_expense_summary_filtered,
    get_category_breakdown_filtered,
    create_expense,
    get_categories,
    get_expense_by_id,
    update_expense,
    delete_expense,
    update_user_password,
    delete_user,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_SECURE_COOKIES", "").strip() == "1"
session_lifetime_minutes = int(os.environ.get("SESSION_LIFETIME_MINUTES", "10080"))
app.permanent_session_lifetime = timedelta(minutes=session_lifetime_minutes)

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
    if get_current_user_from_session():
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
    if get_current_user_from_session():
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
    return {"current_user": get_current_user_from_session(), "csrf_token": get_csrf_token()}


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.before_request
def security_middleware():
    get_csrf_token()

    if session.get("user_id"):
        session.permanent = True

    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not app.testing:
        sent_token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not sent_token or sent_token != session.get("csrf_token"):
            abort(400)


@app.after_request
def add_security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    return resp


@app.errorhandler(400)
def bad_request(err):
    return render_template("400.html"), 400


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout", methods=["GET", "POST"])
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


def get_current_user_from_session():
    user_id = session.get("user_id")
    if not user_id:
        return None

    user = get_user_by_id(user_id)
    if not user:
        session.pop("user_id", None)
        return None

    return user


def is_safe_next_url(next_url):
    if not next_url:
        return False
    parsed = urlparse(next_url)
    if parsed.scheme or parsed.netloc:
        return False
    return next_url.startswith("/")


@app.route("/profile")
def profile():
    user = get_current_user_from_session()
    if not user:
        return redirect(url_for("login"))

    user_id = user["id"]
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
        "top_category": summary["top_category"] or "—",
        "categories": categories,
        "member_since": member_since,
        "date_from": date_from,
        "date_to": date_to,
        "filter_active": filter_active,
        "filter_display": filter_display,
        "expense_added": request.args.get("added") == "1",
        "expense_updated": request.args.get("updated") == "1",
        "expense_deleted": request.args.get("deleted") == "1",
        "filter_hidden": request.args.get("filter_hidden") == "1",
    }
    return render_template("profile.html", **ctx)


@app.route("/expenses/export")
def export_expenses():
    user = get_current_user_from_session()
    if not user:
        return redirect(url_for("login"))

    user_id = user["id"]
    date_from = validate_date(request.args.get("date_from", "").strip()) if request.args.get("date_from") else None
    date_to = validate_date(request.args.get("date_to", "").strip()) if request.args.get("date_to") else None
    if date_from and date_to and date_from > date_to:
        date_from = None
        date_to = None

    expenses = get_user_expenses_filtered(user_id, date_from, date_to)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "amount", "category", "description"])
    for row in expenses:
        writer.writerow([row["date"], f'{row["amount"]:.2f}', row["category"], row["description"] or ""])

    if date_from or date_to:
        safe_from = date_from or "start"
        safe_to = date_to or "end"
        filename = f"spendly-expenses-{safe_from}-to-{safe_to}.csv"
    else:
        filename = "spendly-expenses-all.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    user = get_current_user_from_session()
    if not user:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "settings.html",
            password_updated=request.args.get("updated") == "1",
            delete_error=request.args.get("delete_error") == "1",
        )

    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not current_password or not new_password or not confirm_password:
        return render_template("settings.html", error="All fields are required.")

    if not check_password_hash(user["password_hash"], current_password):
        return render_template("settings.html", error="Current password is incorrect.")

    if len(new_password) < 8:
        return render_template("settings.html", error="New password must be at least 8 characters.")

    if new_password != confirm_password:
        return render_template("settings.html", error="New password and confirmation do not match.")

    password_hash = generate_password_hash(new_password)
    update_user_password(user["id"], password_hash)

    session.pop("user_id", None)
    return redirect(url_for("login", password_updated=1))


@app.route("/settings/delete-account", methods=["POST"])
def delete_account():
    user = get_current_user_from_session()
    if not user:
        return redirect(url_for("login"))

    password = request.form.get("password", "").strip()
    if not password or not check_password_hash(user["password_hash"], password):
        return redirect(url_for("settings", delete_error=1))

    delete_user(user["id"])
    session.pop("user_id", None)
    return redirect(url_for("landing", account_deleted=1))


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user = get_current_user_from_session()
    if not user:
        return redirect(url_for("login"))

    user_id = user["id"]
    next_url = request.args.get("next", "").strip() if request.method == "GET" else request.form.get("next", "").strip()
    if next_url.endswith("?"):
        next_url = next_url[:-1]
    default_next = url_for("profile")
    next_url = next_url if is_safe_next_url(next_url) else default_next

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=get_categories(),
            next_url=next_url,
            form={"amount": "", "category": "", "date": datetime.today().strftime("%Y-%m-%d"), "description": ""},
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_str = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw)
    except ValueError:
        amount = None

    if amount is None or amount <= 0:
        return render_template(
            "add_expense.html",
            categories=get_categories(),
            next_url=next_url,
            error="Amount must be a number greater than 0.",
            form={"amount": amount_raw, "category": category, "date": date_str, "description": description},
        )

    valid_categories = set(get_categories())
    if category not in valid_categories:
        return render_template(
            "add_expense.html",
            categories=get_categories(),
            next_url=next_url,
            error="Please choose a valid category.",
            form={"amount": amount_raw, "category": category, "date": date_str, "description": description},
        )

    date_str = validate_date(date_str)
    if not date_str:
        return render_template(
            "add_expense.html",
            categories=get_categories(),
            next_url=next_url,
            error="Please provide a valid date (YYYY-MM-DD).",
            form={"amount": amount_raw, "category": category, "date": request.form.get("date", "").strip(), "description": description},
        )

    create_expense(user_id, amount, category, date_str, description)

    filter_hidden = False
    parsed_next = urlparse(next_url)
    if parsed_next.path == url_for("profile"):
        qs = parse_qs(parsed_next.query)
        next_from = validate_date((qs.get("date_from") or [""])[0].strip()) if qs.get("date_from") else None
        next_to = validate_date((qs.get("date_to") or [""])[0].strip()) if qs.get("date_to") else None
        if next_from and date_str < next_from:
            filter_hidden = True
        if next_to and date_str > next_to:
            filter_hidden = True

    if next_url == default_next:
        return redirect(url_for("profile", added=1))
    separator = "&" if "?" in next_url else "?"
    extra = "&filter_hidden=1" if filter_hidden else ""
    return redirect(f"{next_url}{separator}added=1{extra}")


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user = get_current_user_from_session()
    if not user:
        return redirect(url_for("login"))

    user_id = user["id"]
    expense = get_expense_by_id(id)
    if not expense or expense["user_id"] != user_id:
        return redirect(url_for("profile"))

    next_url = request.args.get("next", "").strip() if request.method == "GET" else request.form.get("next", "").strip()
    if next_url.endswith("?"):
        next_url = next_url[:-1]
    default_next = url_for("profile")
    next_url = next_url if is_safe_next_url(next_url) else default_next

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            categories=get_categories(),
            next_url=next_url,
            expense_id=expense["id"],
            form={
                "amount": f'{expense["amount"]:.2f}',
                "category": expense["category"],
                "date": expense["date"],
                "description": expense["description"] or "",
            },
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_str = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw)
    except ValueError:
        amount = None

    if amount is None or amount <= 0:
        return render_template(
            "edit_expense.html",
            categories=get_categories(),
            next_url=next_url,
            expense_id=expense["id"],
            error="Amount must be a number greater than 0.",
            form={"amount": amount_raw, "category": category, "date": date_str, "description": description},
        )

    valid_categories = set(get_categories())
    if category not in valid_categories:
        return render_template(
            "edit_expense.html",
            categories=get_categories(),
            next_url=next_url,
            expense_id=expense["id"],
            error="Please choose a valid category.",
            form={"amount": amount_raw, "category": category, "date": date_str, "description": description},
        )

    date_str = validate_date(date_str)
    if not date_str:
        return render_template(
            "edit_expense.html",
            categories=get_categories(),
            next_url=next_url,
            expense_id=expense["id"],
            error="Please provide a valid date (YYYY-MM-DD).",
            form={"amount": amount_raw, "category": category, "date": request.form.get("date", "").strip(), "description": description},
        )

    update_expense(expense["id"], user_id, amount, category, date_str, description)

    if next_url == default_next:
        return redirect(url_for("profile", updated=1))
    separator = "&" if "?" in next_url else "?"
    return redirect(f"{next_url}{separator}updated=1")


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense_route(id):
    user = get_current_user_from_session()
    if not user:
        return redirect(url_for("login"))

    user_id = user["id"]
    next_url = request.form.get("next", "").strip()
    if next_url.endswith("?"):
        next_url = next_url[:-1]
    default_next = url_for("profile")
    next_url = next_url if is_safe_next_url(next_url) else default_next

    delete_expense(id, user_id)

    if next_url == default_next:
        return redirect(url_for("profile", deleted=1))
    separator = "&" if "?" in next_url else "?"
    return redirect(f"{next_url}{separator}deleted=1")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5001")))
    args = parser.parse_args()

    app.run(debug=True, host=args.host, port=args.port)
