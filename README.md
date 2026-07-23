# Spendly — Expense Tracker Application

A lightweight, secure personal finance tracking app built with Flask and SQLite. Track your daily expenses across categories like Food, Transport, Bills, Health, Entertainment, Shopping, and More — all backed by a simple, reliable database.

---

## Features Implemented

### Authentication & Account Management
- **User Registration** (`/register`) — create accounts with name, email, password
- **Login System** (`/login`) — session-based authentication with CSRF protection
- **Logout** (`/logout`) — secure session cleanup and redirection

### Profile & Dashboard
- **Personalized User Profile** (`/profile`) — displays user info, total spent, transaction count, top category, member since date
- **Date Range Filtering** — filter expenses by a custom date range with real-time recalculation of summary stats
- **Transaction History Table** — chronological list of all expenses with inline Edit/Delete actions

### Expense Management
- **Add Expense** (`/expenses/add`) — create new expense entries with amount, category, date, and description (with validation for empty/non-positive values)
- **Edit Expense** (`/expenses/<id>/edit`) — update any field of an existing expense; safe navigation to prevent cross-user edits; redirects back to the filtered profile view
- **Delete Expense** (`/expenses/<id>/delete`) — hard-delete row while verifying ownership, redirecting back with filter state preserved

### Export & Reporting
- **CSV Export** (`/expenses/export`) — downloads all user expenses (or date-filtered subset) as a CSV file with columns: `date`, `amount`, `category`, `description` — filename includes the filtered period

### Security Hardening
- **Cookie Flags**: `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE="Lax"`, `SESSION_COOKIE_SECURE` (configurable via env)
- **CSRF Protection** — every POST/PUT/PATCH/DELETE request requires a valid CSRF token, enforced by before-request middleware; 400 error on token mismatch
- **Strict Clickjacking**: `X-Frame-Options: DENY`, **NoSQL Injection Prevention**: parameterized queries only (no f-strings in SQL), **Referer policy**: blocked for cross-origin referrers, **Content-type sniffing disabled**, **User-Agent spoofing detection**, **Cookie SameSite/Lax**, **XSS Header** injected
- **Redirect Loophole Fix**: URL scheme/netloc validation before redirecting after expense operations

### Settings & Administration
- **Change Password** (`/settings`) — current-pw required; length ≥ 8; confirmation match enforced; auto-reloads profile on update success with `password_updated=1`
- **Delete Account** (`POST /settings/delete-account`) — full account wipe (user + expenses) with confirmatory form and password check

### Legal Pages
- **Terms & Conditions** (`/terms`), **Privacy Policy** (`/privacy`) — renders from templates, links via `url_for()`

### Landing Page
- Hero section with stats preview, feature cards grid, dark CTA band

---

## Tech Stack

| Layer             | Technology                        | Note                                       |
|-------------------|-----------------------------------|--------------------------------------------|
| Framework         | Flask 3.1.3                      | Single-file app.py, no blueprints          |
| Database          | SQLite (via `sqlite3`)           | All queries in `database/db.py`           |
| Frontend          | Vanilla JavaScript               | Zero JS frameworks; inline `main.js` only |
| Styling           | CSS custom properties            | Fintech theme: warm paper, dark accents   |
| Testing           | pytest + pytest-flask (3.12)     | conftest.py auto-registers test fixtures   |

### Database Schema

#### `users`
| Column              | Type    | Constraints                         |
|---------------------|---------|--------------------------------------|
| id                  | INTEGER | PK AUTOINCREMENT                    |
| name                | TEXT    | NOT NULL                             |
| email               | TEXT    | UNIQUE, NOT NULL                     |
| password_hash       | TEXT    | NOT NULL (bcrypt via werkzeug)      |
| created_at          | TEXT    | DEFAULT datetime('now')             |

#### `expenses`
| Column              | Type     | Constraints                            |
|---------------------|----------|----------------------------------------|
| id                  | INTEGER  | PK AUTOINCREMENT                       |
| user_id             | INTEGER  | NOT NULL, FK → users(id)               |
| amount              | REAL     | NOT NULL                               |
| category            | TEXT     | NOT NULL (Food, Transport … Other)    |
| date                | TEXT     | YYYY-MM-DD, NOT NULL                  |
| description         | TEXT     | optional                               |
| created_at          | TEXT     | DEFAULT datetime('now')               |

### Deployment Notes
- **Default port**: 5001 (override: `python app.py --port <n>` or env var `PORT`)
- **Configurable session lifetime**: `SESSION_LIFETIME_MINUTES=10080` (default = 7 days)
- **Secure cookies opt-in**: set env `FLASK_SECURE_COOKIES=1` at runtime

---

## Running Locally

```bash
# Setup virtualenv & install dependencies
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt -q
# Activate the running Flask server (port 5001) python src/app.py
# Activate the running Flask server (port 5001) python app.py

# Run all tests
pytest
```

## Test Fixtures Setup (`conftest.py`)
- `client` — pre-login demo superuser (`demo@spendly.com`)
- `login_as(email, password)` — login helper
- `make_user(name, email, password)` — creates isolated user in DB
- `sample_expenses(amount, date_delta, category, description="Groceries")` — adds N sample rows (1..N) to a test user

## Project Structure

```
spendly/
├── app.py                       # Flask routes: all handlers live here
├── database/
│   ├── db.py                    # DB layer: schema, queries, helpers
│   └── __init__.py             # empty module init
├── templates/
│   ├── base.html                # Shared layout + navbar/footer via Jinja
│   ├── landing.html, profile.html, add_expense.html, edit_expense.html, register.html, login.html
│   └── settings.html, 400.html, terms.html, privacy.html
├── static/
│   ├── css/
│   │   ├── style.css            # Global styles + features + auth + hero + CTA sections
│   │   └── profile.css          # Dashboard & user-info styling (+ stat-value:4rem etc.)
│   ╗── js/main.js (vanilla JS)

# Conftest.py for test setup
.venv/
pytest cache directories

