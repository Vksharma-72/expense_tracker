# Spec: Profile Page Design

## Overview 
The profile page is the first user-facing dashboard after login. It shows a greeting with the current user's name, their email address, and links to core actions (expenses list, logout). This step focuses on **design only** — layout, styling, markup — no backend logic yet. The route will remain a stub that redirects to landing until Step 8 adds real rendering; for now we render `profile.html` directly as the spec is about the template and CSS.

## Depends on
- Step 1: Registration (user table exists)
- Step 2: Login & Logout (session-based auth already in place)
- Step 3: Landing page (base layout conventions established)

# Routes 
| METHOD | Path | Description | Access |
|---|---|---|---|
| GET | /profile | Renders the profile page template | logged-in only |

The route is defined in `app.py` but remains a stub until Step 8. The spec here covers the template and CSS that will be rendered once that route is wired up.

# Database changes 
No database changes. The profile page reads user data from the existing `users` table via the `current_user` context variable already injected by `inject_current_user()` in `app.py`.

## Templates 
- **Creates**:
  - `templates/profile.html` — extends `base.html`, renders the profile view with greeting, email display, and action links.
- **Modify**: None at this stage.

# Files to change 
| File | Change |
|---|---|
| `app.py` (Step 8) | Wire `/profile` route to render template — not done in this step; stub remains. |

# Files to create 
| File | Purpose |
|---|---|
| `templates/profile.html` | Profile page markup extending base layout. |
| `static/css/profile.css` | Page-specific styles (CSS variables only). |

# New dependencies 
No new dependencies.

## Rule for Implementation 
- No SQLAlchemy or ORMs — SQLite raw queries only.
- Passwords hashed with werkzeug (`generate_password_hash`).
- Use CSS variables — never hardcoded hex values.
- All templates extend `base.html`.
- Every internal link uses `url_for()`.
- Parameterised queries only (no f-strings in SQL).
- The profile route must redirect to `/login` if the user is not authenticated; this logic lives in `app.py`, not the template.

# Definition of Done 
- [ ] `templates/profile.html` exists and extends `base.html`.
- [ ] `static/css/profile.css` exists with CSS variables for all colors, no hardcoded hex values.
- [ ] The profile page shows: user's name (from session/user context), email address, a "My Expenses" link pointing to `/expenses`, and a "Logout" link pointing to `/logout`.
- [ ] The page renders without errors when accessed with a valid authenticated session.
- [ ] The route returns 401 or redirects to login when `current_user` is None (handled in Step 8).
