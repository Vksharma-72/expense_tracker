import sqlite3
from datetime import date, timedelta
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def create_user(name, email, password_hash):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()


def get_user_expenses(user_id):
    # Subagent 1: Transaction history
    conn = get_db()
    expenses = conn.execute("SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC", (user_id,)).fetchall()
    conn.close()
    return expenses


def get_expense_summary(user_id):
    # Subagent 2: Summary stats
    conn = get_db()

    # Query 1: Get total spent and transaction count
    result = conn.execute("SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)).fetchone()
    total_spent = result[0] if result[0] is not None else 0.0
    transaction_count = result[1]

    # Query 2: Get top category
    top_row = conn.execute("SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC LIMIT 1", (user_id,)).fetchone()
    top_category = top_row["category"] if top_row else None

    conn.close()
    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "top_category": top_category,
    }


def get_category_breakdown(user_id):
    # Subagent 3: Category breakdown
    conn = get_db()
    rows = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category",
        (user_id,)
    ).fetchall()
    conn.close()
    return {row["category"]: row["total"] for row in rows}


def get_user_expenses_filtered(user_id, date_from=None, date_to=None):
    conn = get_db()
    query = "SELECT * FROM expenses WHERE user_id = ?"
    params = [user_id]

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " ORDER BY date DESC"
    expenses = conn.execute(query, params).fetchall()
    conn.close()
    return expenses


def get_expense_summary_filtered(user_id, date_from=None, date_to=None):
    conn = get_db()
    query = "SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?"
    params = [user_id]

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    result = conn.execute(query, params).fetchone()
    total_spent = result[0] if result[0] is not None else 0.0
    transaction_count = result[1]

    query_category = "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?"
    params_category = [user_id]

    if date_from:
        query_category += " AND date >= ?"
        params_category.append(date_from)
    if date_to:
        query_category += " AND date <= ?"
        params_category.append(date_to)

    query_category += " GROUP BY category ORDER BY total DESC LIMIT 1"
    top_row = conn.execute(query_category, params_category).fetchone()
    top_category = top_row["category"] if top_row else None

    conn.close()
    return {
        "total_spent": total_spent,
        "transaction_count": transaction_count,
        "top_category": top_category,
    }


def get_category_breakdown_filtered(user_id, date_from=None, date_to=None):
    conn = get_db()
    query = "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?"
    params = [user_id]

    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)

    query += " GROUP BY category"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {row["category"]: row["total"] for row in rows}


def seed_db():
    conn = get_db()
    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    password_hash = generate_password_hash("demo123")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cursor.lastrowid

    today = date.today()
    sample_expenses = [
        (45.50, "Food", 1, "Groceries"),
        (12.00, "Transport", 3, "Bus pass"),
        (89.99, "Bills", 5, "Electricity bill"),
        (25.00, "Health", 7, "Pharmacy"),
        (60.00, "Entertainment", 9, "Movie night"),
        (150.00, "Shopping", 11, "New shoes"),
        (15.75, "Other", 13, "Misc"),
        (32.40, "Food", 15, "Restaurant"),
    ]
    for amount, category, days_ago, description in sample_expenses:
        expense_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )

    conn.commit()
    conn.close()
