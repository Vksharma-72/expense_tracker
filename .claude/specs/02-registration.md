# Spec: Registration

## Overview
This feature implements the account-creation flow for Spendly. Step 1 built the `users` table and the password-hashing pattern used by `seed_db()`; Step 2 wires the existing `register.html` form up to a real `POST /register` route so a visitor can create a persistent account. It does not introduce login sessions — after a successful registration the user is redirected to the login page, where session handling will be added in a later step.

## Depends on
Step 1 — Database setup. Requires the `users` table (`id`, `name`, `email` UNIQUE, `password_hash`, `created_at`) and the `get_db()` / `PRAGMA foreign_keys = ON` connection helper already delivered by that step.

## Routes
- `POST /register` -- validate submitted name/email/password, hash the password, insert a new user, and redirect to login on success (re-render the form with an error on failure) -- public

`GET /register` already exists and needs no route-level changes; the `/register` view function becomes multi-method (`GET`, `POST`) rather than a new route.

## Database changes
No schema changes. The `users` table from Step 1 already has every column registration needs (`name`, `email` UNIQUE NOT NULL, `password_hash` NOT NULL, `created_at` default).

`database/db.py` needs two new functions (not schema changes):
- `get_user_by_email(email)` — parameterized `SELECT` used to check for duplicate emails before insert
- `create_user(name, email, password_hash)` — parameterized `INSERT` into `users`

## Templates
- Creates: none
- Modify:
  - `templates/register.html` — replace hardcoded `action="/register"` with `{{ url_for('register') }}`; confirm the existing `{% if error %}` block renders the error string passed by the route
  - `templates/login.html` — replace hardcoded `action="/login"` with `{{ url_for('login') }}`; add a success message block that displays when the redirect includes `?registered=1`

## Files to change
- `app.py` — import `generate_password_hash` from `werkzeug.security`; change the `/register` view to accept `["GET", "POST"]`; on `POST`, validate input, check for a duplicate email, call the new `db.py` helpers, and either re-render `register.html` with an `error` or redirect to `url_for('login', registered=1)`
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/register.html` — fix hardcoded form action, verify error rendering
- `templates/login.html` — fix hardcoded form action, add post-registration success message

## Files to create
No new files needed.

## New dependencies
No new dependencies — `werkzeug` is already in `requirements.txt` and already used for hashing in `seed_db()`.

## Rule for Implementation
- No SQLAlchemy or ORMs
- Parameterized queries only
- Passwords hashed with werkzeug (`generate_password_hash`), matching the pattern already used in `seed_db()`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB access (`get_user_by_email`, `create_user`) lives in `database/db.py` — the route only parses the form, calls the helpers, and renders/redirects
- Every internal link and form `action` uses `url_for()` — no hardcoded paths, including the existing hardcoded `/register` and `/login` actions
- Do not add session/login-state handling in this step — registration only creates the account; logging the user in is a later step
- Invalid input or a duplicate email re-renders `register.html` with an `error` message — do not use `abort()` for these user-facing validation cases

## Definition of Done
- [ ] `GET /register` still renders the registration form with no errors
- [ ] Submitting valid name/email/password on `/register` inserts a new row into `users` with a hashed (not plaintext) `password_hash`
- [ ] Submitting an email that already exists re-renders `register.html` with an error message and does not insert a duplicate row
- [ ] Submitting with a blank name, email, or password re-renders `register.html` with an error message and does not insert a row
- [ ] A successful registration redirects to `GET /login` and the login page shows a "registration successful" message
- [ ] Form actions in `register.html` and `login.html` use `url_for()`, not hardcoded paths
- [ ] `requirements.txt` is unchanged
- [ ] The app still starts and serves on port 5001 with no errors
