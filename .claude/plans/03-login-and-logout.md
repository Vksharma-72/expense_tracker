# Implementation Plan: Login and Logout (Step 03)

## Context

Registration (Step 02) only creates a `users` row — it never starts a session, and `/login` is currently a GET-only stub (`app.py:55-57`) that just renders `login.html` without handling the POST the form already submits to. `/logout` is a raw-string placeholder (`app.py:64-66`). Neither Flask sessions nor `app.secret_key` exist anywhere in the app yet. This step closes that gap: real credential verification, a signed session cookie, a working logout, and a nav that reflects logged-in state — the foundation every later gated route (`/profile`, `/expenses/*`) will depend on. Per the spec (`.claude/specs/03-login-and-logout.md`), those gated routes stay stubs; this step only touches auth plumbing.

## Current state (confirmed by reading the files)

- `app.py:7` already imports `get_user_by_email`, `create_user` from `database.db`; `generate_password_hash` from werkzeug — but not `check_password_hash`.
- `database/db.py` has `get_db()` (with `PRAGMA foreign_keys = ON`, `database/db.py:15`), `get_user_by_email(email)`, `create_user(...)` — parameterized, following existing pattern. **No `get_user_by_id`.**
- `templates/login.html` already has a full `POST` form to `url_for('login')` with email/password fields, an `{% if error %}` block, and an `{% if request.args.get('registered') %}` success banner — no template changes needed.
- `templates/base.html:21-24` nav is static: always shows "Sign in" / "Get started" links, no session awareness.
- `static/css/style.css` already defines `.auth-error`/`.auth-success` using `--danger`/`--accent` CSS variables — reusable as-is, no new CSS.
- No `tests/` directory exists in the project — verification will be manual (dev server + browser/curl), no pytest suite to run.

## Implementation steps

### 1. `database/db.py` — add `get_user_by_id`
Add a helper next to `get_user_by_email`, same pattern (parameterized query, connection opened/closed inline):
```python
def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user
```
This is used by a context processor (step 3) so `base.html` can show the logged-in user's name without every route fetching it manually.

### 2. `app.py` — secret key, login POST handling, logout
- Import additions: `session` from `flask`; `check_password_hash` from `werkzeug.security`; `get_user_by_id` from `database.db`.
- Right after `app = Flask(__name__)`, set `app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")` — stable across restarts (per DoD) unless `SECRET_KEY` env var is set for production.
- Change `/login` to `methods=["GET", "POST"]`:
  - `GET` → unchanged, renders `login.html`.
  - `POST` → read `email`/`password` from `request.form`, call `get_user_by_email(email)`. If no user, or `check_password_hash(user["password_hash"], password)` fails, re-render `login.html` with `error="Invalid email or password."` (same generic message for both cases, per spec, so failed attempts don't reveal which emails are registered). On success, set `session["user_id"] = user["id"]` and `redirect(url_for("landing"))`.
- Replace the `/logout` stub body: `session.pop("user_id", None)` then `redirect(url_for("landing"))`. Works even if there's no session (no error).

### 3. `app.py` — session-aware nav via context processor
Add a `@app.context_processor` function (near the top, after routes or right after `app` is created) that loads the current user once per request and exposes it to every template — avoids repeating a DB lookup in every route:
```python
@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": get_user_by_id(user_id) if user_id else None}
```

### 4. `templates/base.html` — session-aware nav
Replace the static `nav-links` block (`templates/base.html:21-24`) with a conditional:
- If `current_user` is set: show the user's name (e.g. `current_user["name"]`) and a "Log out" link (`url_for('logout')`), reusing existing nav link markup/classes — no new CSS.
- Else: keep the existing "Sign in" / "Get started" links unchanged.

### Files touched
- `database/db.py` — add `get_user_by_id`
- `app.py` — secret key, imports, `/login` POST logic, `/logout` logic, context processor
- `templates/base.html` — nav conditional

No new templates, no new CSS, no new dependencies, no DB schema changes — matches the spec exactly.

## Verification

Since there's no `tests/` directory yet, verify by running the dev server and exercising the flow directly (start with `python app.py`, app on `http://127.0.0.1:5001`):
1. `GET /login`, submit `demo@spendly.com` / `demo123` (seeded demo account) → redirected to `/`, nav now shows the user's name + "Log out" instead of "Sign in"/"Get started".
2. Submit `demo@spendly.com` with a wrong password → re-renders `login.html` with "Invalid email or password.", no session cookie set.
3. Submit a nonexistent email → same generic error, no session set.
4. After logging in, refresh `/` → still logged in (session persists, not just the redirect).
5. Visit `/logout` → session cleared, redirected to `/`, nav reverts to logged-out state.
6. Visit `/logout` while already logged out → no error, redirects to `/`.
7. View page source on `/logout`'s response (or `curl -i`) → confirms no raw string is returned, only a redirect.
