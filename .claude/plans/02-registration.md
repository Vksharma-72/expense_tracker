# Implementation Plan: Step 02 — Registration

Based on `.claude/spec/02-registration.md`. No code included — description only.

## 1. `database/db.py` — add two helper functions

Place both new functions after `get_db()` and before `init_db()` (keeps connection-related helpers grouped at the top, schema/seed functions below).

**`get_user_by_email(email)`**
- Opens a connection via `get_db()`.
- Runs a parameterized `SELECT * FROM users WHERE email = ?` with `email` as the single bound parameter (never string-interpolated).
- Fetches one row (`.fetchone()`), closes the connection, and returns the row (or `None` if no match).
- Purpose: lets the route check for a duplicate email before inserting.

**`create_user(name, email, password_hash)`**
- Opens a connection via `get_db()`.
- Runs a parameterized `INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)` with all three values bound as parameters — mirrors the exact pattern already used in `seed_db()` (line 54-57), just generalized to arbitrary input instead of the hardcoded demo user.
- Commits, captures `cursor.lastrowid` if the caller might need the new user's id (not required by this spec, but harmless to return), closes the connection.
- Does **not** catch `sqlite3.IntegrityError` from the UNIQUE constraint on `email` — the route is responsible for calling `get_user_by_email()` first and rejecting duplicates before ever calling `create_user()`, so the constraint should never actually fire in normal flow. This keeps error handling in one place (the route) rather than split between layers.

No changes to `init_db()`, `seed_db()`, `get_db()`, or the `expenses` table logic.

## 2. `app.py` — turn `/register` into a real handler

**Import change (top of file, near line 4-6):**
- Add `generate_password_hash` from `werkzeug.security` to the import block.
- Extend the `flask` import to also pull in `request` and `redirect`/`url_for` (currently only `Flask, render_template` are imported).
- Extend the `database.db` import to also pull in `get_user_by_email` and `create_user`.

**Route change (currently lines 33-35):**
- Change the decorator from `@app.route("/register")` to `@app.route("/register", methods=["GET", "POST"])`.
- Keep the function name `register` (templates already reference `url_for('register')`, so the endpoint name must not change).

**Handler logic, in order:**
1. If `request.method == "GET"`: unchanged behavior — `render_template("register.html")` with no `error`.
2. If `POST`: read `name`, `email`, `password` from `request.form`, each `.strip()`'d.
3. Validate all three are non-empty. If any is blank → `render_template("register.html", error=...)` with a message like "All fields are required." Do not touch the database.
4. Call `get_user_by_email(email)`. If a row comes back → re-render `register.html` with an error like "An account with that email already exists." Do not insert.
5. If both checks pass: hash the password with `generate_password_hash(password)`, call `create_user(name, email, password_hash)`.
6. On success: `redirect(url_for("login", registered=1))`.
7. No `abort()` calls anywhere in this flow — validation failures are user-facing, not HTTP errors, per CLAUDE.md's rule and the spec's explicit instruction.
8. No session/`flask.session` usage introduced — this route only creates the row and redirects; it does not log the user in.

Leave every other route (`/login`, `/logout`, `/profile`, `/expenses/*`) untouched — they're out of scope for this step.

## 3. `templates/register.html`

- Line 20: change `<form method="POST" action="/register">` to use `action="{{ url_for('register') }}"`.
- No other structural change needed — the `{% if error %}` block (lines 16-18) already exists and already renders whatever `error` string the route passes in; it's currently just unused because nothing sets `error` yet.

## 4. `templates/login.html`

- Line 20: change `<form method="POST" action="/login">` to use `action="{{ url_for('login') }}"`.
- Add a new conditional block near the existing `{% if error %}` block that checks for a `registered` query parameter (e.g. `{% if request.args.get('registered') %}`) and displays a success message such as "Account created — please sign in." Reuse the existing `.auth-error`-style CSS class or a similarly-scoped class already defined via CSS variables in `style.css`; do not introduce a new hardcoded color.
- No change to the `/login` route itself — it stays a GET-only stub, this step doesn't implement login.

## 5. Manual verification pass (maps directly to the spec's Definition of Done)

Run the app on port 5001 and, without writing any test code, walk through:
1. Load `/register` — form renders, no errors.
2. Submit a new name/email/password — expect redirect to `/login?registered=1`, success message visible, and a new row present in the `users` table with a bcrypt/werkzeug hash (not the plaintext password) in `password_hash`.
3. Submit the same email again — expect to land back on `/register` with the duplicate-email error, and no second row inserted.
4. Submit with one field blank — expect to land back on `/register` with the required-field error, no row inserted.
5. Inspect rendered HTML source of `/register` and `/login` — confirm both `<form>` tags now contain the Jinja-generated URL rather than a literal `/register` or `/login` string.
6. Confirm `requirements.txt` has no diff.

## Notes / things intentionally out of scope
- Session creation, "remember me," or auto-login after registration — deferred to whatever step adds `flask.session` / login handling.
- Password strength rules beyond "non-empty" — the spec doesn't ask for them, and register.html's placeholder text ("Min. 8 characters") is cosmetic only; adding real length enforcement would be a scope addition, so it's flagged rather than added silently.
- The hardcoded `/terms` and `/privacy` links in `base.html` — same hardcoded-URL smell, but outside this spec's file list.
