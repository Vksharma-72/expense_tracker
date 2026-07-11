# Spec: Profile Backend Integration

## Overview
This feature replaces the hardcoded mock data in the `/profile` route with live queries from the database. The profile page UI layout (built in Step 4) remains unchanged, but now displays the authenticated user's actual expenses, real transaction history, calculated totals, and genuine category breakdowns. This step bridges the gap between the static design and a functional expense tracker.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables exist)
- Step 2: Registration (user accounts exist in DB)
- Step 3: Login + Logout (session authentication works)
- Step 4: Profile page design (UI layout and templates complete)

## Routes
No new routes. Modify existing route:
- `GET /profile` — fetch authenticated user's data from DB and render profile page — logged-in only

## Database changes
No schema changes. The existing `users` and `expenses` tables are sufficient. Add helper functions to `database/db.py`:
- `get_user_expenses(user_id)` — returns list of all expenses for a user, ordered by date DESC
- `get_expense_summary(user_id)` — returns dict with total_spent, transaction_count, top_category

## Templates
No template changes. Reuse `profile.html` from Step 4.

## Files to change
- `app.py` — replace `/profile` route function:
  - Query the authenticated user's full record from DB
  - Call `get_user_expenses(user_id)` to fetch real transaction list
  - Call `get_expense_summary(user_id)` to compute stats (total spent, count, top category)
  - Fetch the user's `created_at` date for "member since"
  - Pass real data to `profile.html` context
- `database/db.py` — add two new helper functions with parameterized queries

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- All DB calls must close the connection after use
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- Preserve all HTML structure from Step 4 — do not modify `profile.html`
- Foreign key enforcement must be enabled (`PRAGMA foreign_keys = ON` is already in `get_db()`)
- Do not modify CSS files — profile layout should look identical to Step 4
- Top category logic: find the category with the highest total amount; if tie, return any one

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The profile page displays the logged-in user's actual name and email
- [ ] The "Member since" date shows the user's actual account creation date
- [ ] The "Total Spent" value is calculated from all expenses in the DB for that user
- [ ] The "Transaction Count" shows the actual number of expenses for that user
- [ ] The "Top Category" shows the category with the highest total spending (or one of them if tied)
- [ ] The transaction history table shows all real expenses for the logged-in user
- [ ] The category breakdown shows actual totals per category (only non-zero categories)
- [ ] Expenses are sorted by date (most recent first) in the transaction table
- [ ] A different user's profile shows different data (verify with test user "Vishnu")
- [ ] No hardcoded mock data remains in `app.py` (all is queried from DB)
- [ ] All SQL queries use parameterized placeholders (`?`), never f-strings
