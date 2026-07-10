# Implementation Plan: Profile Page Design (Step 4)

## Context
This step delivers the **profile page UI** for Spendly — the first user-facing dashboard after login. The spec mandates four sections with **hardcoded static data**: user info card, summary stats row, transaction history table, and category breakdown. No database queries yet; all data is mocked in `app.py`. This lets the team validate the design before wiring real backend logic in Step 5.

The implementation is **design-first**, not functionality-first. Focus: clean HTML structure, CSS variables for all colors, responsive layout, and authentication guard on the route.

---

## Files to Create / Modify

### 1. **`static/css/profile.css`** (new file)
**Purpose:** Page-specific styles for the profile page layout and components.

**Sections to implement:**
- `.profile-container` — outer wrapper, centered layout with max-width
- `.user-info-card` — avatar circle with initials, name, email, member-since date
- `.summary-stats` — three stat boxes (total spent, transaction count, top category)
- `.transaction-history` — table styling (header, rows, category badges)
- `.category-breakdown` — list or progress-bar rows for per-category totals

**Key rules:**
- **No hardcoded hex values** — all colors use CSS variables (e.g., `var(--color-primary)`, `var(--color-accent)`)
- Reference the same CSS variable palette used in `static/css/style.css` (global styles)
- No inline `<style>` tags in the template
- Use flexbox for layout (responsive design)
- Category badges should have distinct background colors via CSS classes (e.g., `.badge-food`, `.badge-transport`)

---

### 2. **`templates/profile.html`** (new file)
**Purpose:** The profile page template extending `base.html` with four sections of hardcoded data.

**Structure:**
```html
{% extends "base.html" %}

{% block content %}
<div class="profile-container">
  <!-- Section 1: User Info Card -->
  <div class="user-info-card">
    <!-- Avatar with initials, name, email, member-since -->
  </div>

  <!-- Section 2: Summary Stats Row -->
  <div class="summary-stats">
    <!-- Three stat boxes: total spent, transaction count, top category -->
  </div>

  <!-- Section 3: Transaction History Table -->
  <div class="transaction-history">
    <!-- Table with date, description, category badge, amount -->
    <!-- At least 3 hardcoded rows -->
  </div>

  <!-- Section 4: Category Breakdown -->
  <div class="category-breakdown">
    <!-- Per-category totals as rows or progress bars -->
    <!-- At least 3 categories -->
  </div>
</div>
{% endblock %}
```

**Data to render (all passed from `app.py`):**
- `current_user.name`, `current_user.email` (from session context)
- `member_since` (hardcoded date string, e.g., "July 2026")
- `total_spent`, `transaction_count`, `top_category` (hardcoded stats)
- `transactions` (list of dicts: `id`, `date`, `description`, `category`, `amount`)
- `categories` (dict mapping category name → total)

**Template rules:**
- Extend `base.html` only
- Use `url_for()` for all internal links (e.g., `/expenses`, `/logout`)
- No inline styles
- Use CSS classes for all category badge colors
- Display category badges with appropriate class (e.g., `<span class="badge badge-food">Food</span>`)

---

### 3. **`app.py`** — Replace `/profile` stub route

**Current stub (line 94-96):**
```python
@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"
```

**New implementation:**
```python
@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    
    # Hardcoded context for Step 4 (no DB queries yet)
    ctx = {
        "member_since": "July 2026",
        "total_spent": 430.64,
        "transaction_count": 8,
        "top_category": "Shopping",
        "transactions": [
            {"id": 1, "date": "2026-07-09", "description": "Movie night", "category": "Entertainment", "amount": 60.00},
            {"id": 2, "date": "2026-07-07", "description": "New shoes", "category": "Shopping", "amount": 150.00},
            {"id": 3, "date": "2026-06-29", "description": "Pharmacy", "category": "Health", "amount": 25.00},
            {"id": 4, "date": "2026-06-27", "description": "Electricity bill", "category": "Bills", "amount": 89.99},
            {"id": 5, "date": "2026-06-25", "description": "Bus pass", "category": "Transport", "amount": 12.00},
            {"id": 6, "date": "2026-06-23", "description": "Groceries", "category": "Food", "amount": 45.50},
        ],
        "categories": {
            "Food": 45.50,
            "Transport": 12.00,
            "Bills": 89.99,
            "Health": 25.00,
            "Entertainment": 60.00,
            "Shopping": 150.00,
            "Other": 15.75,
        },
    }
    return render_template("profile.html", **ctx)
```

**Notes:**
- Check `session.get("user_id")` first; if absent, redirect to login
- `current_user` is injected automatically by `inject_current_user()` context processor
- All transaction and category data are **hardcoded dicts/lists** — no database queries
- Pass context via `**ctx` to make all data available in the template

---

## Implementation Order

1. **Create `static/css/profile.css`**
   - Define CSS variables for colors (reference `style.css` palette)
   - Style `.profile-container`, `.user-info-card`, `.summary-stats`, `.transaction-history`, `.category-breakdown`
   - Create badge color classes (`.badge-food`, `.badge-transport`, etc.)

2. **Create `templates/profile.html`**
   - Extend `base.html`
   - Build four-section layout with hardcoded data placeholders
   - Link stylesheet: `<link rel="stylesheet" href="{{ url_for('static', filename='css/profile.css') }}">`
   - Use `{{ variable }}` to render context passed from `app.py`

3. **Update `app.py`** — Replace `/profile` stub
   - Add auth guard: redirect if `session.get("user_id")` is None
   - Build hardcoded context dict
   - Call `render_template("profile.html", **ctx)`

4. **Test in browser**
   - Run: `python app.py`
   - Visit `http://localhost:5001/login`, log in with seed user: `demo@spendly.com` / `demo123`
   - Navigate to `/profile` — verify all four sections render without errors
   - Check no hardcoded hex values in CSS or inline styles
   - Verify unauthenticated access redirects to `/login`

---

## Definition of Done

- [ ] `static/css/profile.css` exists with no hardcoded hex colors — only CSS variables
- [ ] `templates/profile.html` exists and extends `base.html`
- [ ] Profile page displays user info card with name, email, and member-since date
- [ ] Profile page displays summary stats row (total spent, transaction count, top category)
- [ ] Profile page displays transaction history table with ≥3 hardcoded rows
- [ ] Profile page displays category breakdown with ≥3 categories
- [ ] Navbar reflects logged-in state (username + logout link visible via `current_user`)
- [ ] Visiting `/profile` while logged in returns HTTP 200 and renders the page
- [ ] Unauthenticated access to `/profile` redirects to `/login`
- [ ] No inline `<style>` tags in the template
- [ ] All internal links use `url_for()`
- [ ] All category badges use CSS classes, not inline colors

---

## Key Constraints (from CLAUDE.md)

- **Flask only** — no other frameworks
- **Vanilla JS only** — no React, no npm packages
- **SQLite only** — raw queries only (not used in this step)
- **No new pip packages** — work within existing `requirements.txt`
- **CSS variables only** — never hardcode hex values
- **All templates extend `base.html`** — maintain consistent layout
- **Parameterized queries only** (not relevant yet, but remember for Step 5)
- **FK enforcement manual** — PRAGMA foreign_keys = ON (not relevant yet)
