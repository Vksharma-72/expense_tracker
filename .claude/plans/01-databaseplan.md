# Plan: Step 1 — Database Setup

## Context

`database/db.py` is currently just a comment stub — no code. This step implements the SQLite data layer (`get_db()`, `init_db()`, `seed_db()`) that every future feature (auth, profile, expense CRUD) depends on, per `.claude/spec/01-database-setup.md`. `app.py` needs to call `init_db()`/`seed_db()` on startup so the schema and demo data exist before any route runs.

Subagent research confirmed:
- `requirements.txt` already has `flask==3.1.3`, `werkzeug==3.1.6`, `pytest==8.3.5`, `pytest-flask==1.3.0` — no new packages needed.
- `database/__init__.py` already exists (empty) — `database` is already an importable package.
- `.gitignore` ignores `expense_tracker.db` specifically (not a glob) — no existing db file anywhere in the repo. **Decision: name the DB file `expense_tracker.db`** so it lines up with the existing `.gitignore` entry without needing to touch `.gitignore`.
- No `tests/` directory exists yet — verification for this step will be manual (see below), not a new automated test suite, since the spec's "Files to Create: None" and doesn't ask for tests.
- `register.html`/`login.html` already use form fields `name`, `email`, `password` — consistent with the `users` schema (not used in this step, just confirms schema field names are sane for later).
- `app.py` import convention: stdlib imports, blank line, third-party imports, blank line, `app = Flask(...)`.

## Implementation

### 1. `database/db.py`

Implemented with:

```python
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
```

Notes:
- `days_ago` offsets keep all 8 dates within the current month regardless of which day `seed_db()` runs, while staying spread out.
- `CATEGORIES` list is exported for reuse by later steps (e.g. the add/edit expense forms) — matches the spec's fixed list, kept here since it's DB-adjacent constant data, not duplicated in `app.py`.
- All queries use `?` placeholders — no f-strings in SQL, per `CLAUDE.md`.

### 2. `app.py`

Added the import (grouped with existing third-party imports) and a startup block right after `app = Flask(__name__)`:

```python
from flask import Flask, render_template

from database.db import get_db, init_db, seed_db

app = Flask(__name__)

with app.app_context():
    init_db()
    seed_db()
```

- `get_db` is imported now (per spec §6) even though no route uses it yet — future steps (auth, expenses) will.
- No changes to any of the existing route bodies or stub routes.

## Verification

1. Run `python app.py` from the project root — confirm it starts without errors and `expense_tracker.db` is created in the project root.
2. Inspect the schema and seed data:
   ```
   python -c "
   from app import app
   from database.db import get_db
   with app.app_context():
       conn = get_db()
       print(conn.execute('SELECT * FROM users').fetchall())
       print(len(conn.execute('SELECT * FROM expenses').fetchall()))
   "
   ```
   Expect 1 user (demo@spendly.com, hashed password) and 8 expenses.
3. Restart the app (or call `init_db()`/`seed_db()` again) and re-run the query above — row counts must stay at 1 user / 8 expenses (no duplicates).
4. Confirm constraints:
   - Inserting a second user with `email='demo@spendly.com'` raises `sqlite3.IntegrityError` (unique constraint).
   - Inserting an expense with a non-existent `user_id` raises `sqlite3.IntegrityError` (FK constraint) — only works because `get_db()` sets `PRAGMA foreign_keys = ON`.
5. Per `CLAUDE.md` subagent policy, dispatch a subagent to independently run steps 1–4 and confirm results before marking this step done.

## Status

Implemented and verified in a prior session:
- `database/db.py` and `app.py` updated as above.
- A verification subagent confirmed: DB created on startup, correct seed counts (1 user / 8 expenses), password properly hashed, idempotent re-seeding, unique-email and foreign-key constraints both correctly enforced.
- The app was also manually launched on port 5001 and smoke-tested (`/`, `/login`, `/register` returned 200; stub routes unaffected).
