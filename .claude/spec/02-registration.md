# Spec: Registration

## Overview
Step 2 implements user registration, allowing new users to create an account by providing their name, email, and password. The registration form validates input, hashes passwords securely using werkzeug, and stores the user in the SQLite database. Successful registration redirects to the login page. This step establishes the user authentication foundation that enables all subsequent features requiring user sessions and data persistence.

## Depends on
- Step 1: Landing pages (foundation in place, routes exist)
- Database schema: `users` table already created in `db.py`

## Routes
- `GET /register` — Display registration form — public
- `POST /register` — Handle form submission, create user, redirect to login — public

## Database changes
No database changes. The `users` table already exists with:
- `id` (primary key)
- `name` (text, not null)
- `email` (text, unique, not null)
- `password_hash` (text, not null)
- `created_at` (timestamp, default now)

## Templates
**Creates:**
- `templates/register.html` — Registration form with name, email, password fields

**Modify:**
- `templates/base.html` — Add link to /register in header/nav (if not already present)

## Files to change
- `app.py` — Add POST /register route to handle form submission and user creation
- `templates/base.html` — Add navigation link to registration (if needed)

## Files to create
- `templates/register.html` — New registration form template

## New dependencies
No new dependencies. Werkzeug is already installed (used for password hashing).

## Rules for implementation
- Use parameterized queries (`?` placeholders) for all SQL — never f-strings
- Hash passwords with `werkzeug.security.generate_password_hash()`
- Never store plain-text passwords
- All templates must extend `base.html`
- Use `url_for()` for all internal links — never hardcode URLs
- Use `abort(400)` or `abort(409)` for validation errors, not bare string returns
- Handle email uniqueness constraint: catch `sqlite3.IntegrityError` if email already exists
- One responsibility per route: `GET /register` renders form, `POST /register` processes submission
- No SQLAlchemy or ORMs — raw SQL via `get_db()` only
- Use CSS variables for colors — never hardcode hex values
- Form should include CSRF protection (if Flask-WTF available) or basic validation
- Clear, user-friendly error messages for duplicate email and validation failures

## Definition of Done
- [ ] `GET /register` displays a form with name, email, password, and confirm-password fields
- [ ] Form validation: name and email are required, password is at least 8 characters
- [ ] `POST /register` creates a new user with hashed password in the database
- [ ] Duplicate email is rejected with a 409 or 400 error message
- [ ] Successful registration redirects to `/login`
- [ ] Register form extends `base.html` and uses consistent styling (CSS variables, not hardcoded colors)
- [ ] All routes use parameterized SQL queries
- [ ] Password is hashed with `werkzeug.security.generate_password_hash()`
- [ ] Navigation links work: can navigate from landing → register → login
- [ ] All internal links use `url_for()`, not hardcoded URLs
