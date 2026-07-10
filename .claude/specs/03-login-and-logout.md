# Spec: Login and Logout

## Overview
This step implements user authentication, allowing users to sign in with their email and password, and sign out to end their session. Login uses Flask sessions and password verification via werkzeug. This builds on the registration step to complete the authentication flow, enabling access control for expense tracking features in later steps.

## Depends on
- Step 02: User registration (users table with password_hash)

## Routes
- `POST /login` — authenticate user with email and password, set session, redirect to profile — public
- `GET /logout` — clear session and redirect to landing — logged-in users

## Database changes
No new tables or columns. Add one helper function to `database/db.py`:
- `get_user_by_id(user_id)` — fetch user by id

## Templates
- **Modify:** `base.html` — add `{% if session.get('user_id') %}` conditional to show logout link in nav when logged in, hide "Sign in" and "Get started" links
- **Modify:** `login.html` — handle error messages (already has structure)
- **Create:** None

## Files to change
- `app.py` — implement POST /login and GET /logout routes, configure Flask sessions
- `database/db.py` — add `get_user_by_id()` helper
- `templates/base.html` — update navbar to show/hide links based on session state

## Files to create
None.

## New dependencies
No new dependencies needed. werkzeug (for password verification) and Flask sessions are already available.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL only
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Password verification with `werkzeug.security.check_password_hash`
- Set app.secret_key from environment or a secure default
- Session cookie should not be HttpOnly for this step (allow JS access if needed later)
- Use Flask's `session` object for user tracking
- Redirect (not render) after successful login — no GET /login rendering with user already logged in
- All templates must extend `base.html`

## Definition of done
- [ ] User can POST email and password to `/login`
- [ ] Invalid email shows error message without redirecting
- [ ] Invalid password shows error message without redirecting
- [ ] Valid credentials set `session['user_id']` and redirect to `/profile` (step 4 stub is ok for now)
- [ ] GET `/logout` clears the session and redirects to `/`
- [ ] Navbar shows "Sign out" link when logged in, hides "Sign in" and "Get started"
- [ ] Navbar shows "Sign in" and "Get started" when logged out
- [ ] Logout link in navbar redirects to `/logout` and clears session
