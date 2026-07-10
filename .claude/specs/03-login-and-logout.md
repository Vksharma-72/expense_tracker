# Spec: Login and Logout

## Overview
This step gives Spendly its first authenticated session. Registration (Step 2) only creates an account — it never logs the user in. This step wires `/login` to actually verify credentials and start a session, and implements `/logout` to end it. It also updates the shared nav in `base.html` so it reflects whether a visitor is signed in. This is the foundation every later "logged-in only" route (`/profile`, `/expenses/*`) depends on.

## Depends on
- Step 01 — Database Setup (`users` table, `get_db()` with FK pragma)
- Step 02 — Registration (`get_user_by_email()`, `create_user()`, existing `register.html` pattern, `login.html` already has a POST form wired to `/login`)

## Routes
- `GET /login` — render login form — public (already implemented, no change to the GET path)
- `POST /login` — verify email/password, start session on success, re-render form with error on failure — public
- `GET /logout` — clear session, redirect to landing page — logged-in (safe to call when logged out too; just redirects)

## Database changes
No database changes. `users` table (from Step 01) already has `email` and `password_hash` columns, which is all login needs. `get_user_by_email()` already exists in `database/db.py` and is reused as-is.

## Templates
- Creates: none — logout has no page, it redirects immediately after clearing the session
- Modify:
  - `templates/login.html` — no structural change needed; already posts to `/login` and already has an `{% if error %}` block for displaying failures
  - `templates/base.html` — nav must become session-aware: show "Sign in" / "Get started" when logged out (current behavior), and show the user's name plus a "Log out" link (`url_for('logout')`) when `session.get('user_id')` is set

## Files to change
- `app.py` — set `app.secret_key` (from an env var, e.g. `os.environ.get("SECRET_KEY", "dev-secret-key")`); change `/login` to `methods=["GET", "POST"]` and implement POST handling; replace the `/logout` stub with real session-clearing logic
- `database/db.py` — add `get_user_by_id(user_id)` helper (parameterized SELECT by `id`), needed so later steps (`/profile`) can load the logged-in user from `session["user_id"]`
- `templates/base.html` — add session-aware nav conditional

## Files to create
None.

## New dependencies
No new dependencies. Sessions use Flask's built-in `session` object (signed cookies via `secret_key`) — no `flask-login` or similar package.

## Rule for Implementation
- No SQLAlchemy or ORMs
- Parameterized queries only
- Passwords hashed with werkzeug — verify with `werkzeug.security.check_password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values (reuse existing `--danger`/`--danger-light` classes already used by `.auth-error` for login failures — no new CSS needed)
- All templates extend `base.html`
- Store only `session["user_id"]` in the session — never store the password hash or full user row in the session
- `/logout` must not use a raw string return — it must clear the session and issue a redirect (not render a stub string)
- Do not implement `/profile` or any `/expenses/*` route in this step even though they will consume `session["user_id"]` — those remain stubs per CLAUDE.md until their own steps

## Definition of Done
- [ ] Visiting `/login` and submitting the seeded demo account (`demo@spendly.com` / `demo123`) redirects successfully and the nav now shows a logged-in state instead of "Sign in"/"Get started"
- [ ] Submitting `/login` with a wrong password re-renders `login.html` with an error message and does not create a session
- [ ] Submitting `/login` with an email that doesn't exist re-renders `login.html` with an error message (same generic message as wrong password, to avoid leaking which emails are registered)
- [ ] After logging in, visiting `/logout` clears the session and redirects to `/`, and the nav reverts to the logged-out state
- [ ] Visiting `/logout` while already logged out does not error — it just redirects to `/`
- [ ] Refreshing the page after login keeps the user logged in (session persists across requests, not just the redirect)
- [ ] `app.secret_key` is set and sessions survive a server restart only if the key is stable (not regenerated randomly on each run)
- [ ] No raw string is returned from `/logout` — confirmed by viewing page source after hitting the route
