# Implementation Plan: Date Filter for Profile Page

## Overview
Add date-range filtering to the `/profile` route and `profile.html` template, allowing users to view expenses within a selected time period without schema changes.

---

## Phase 1: Database Layer (`database/db.py`)

### Add 3 new filtered helper functions:

1. **`get_user_expenses_filtered(user_id, date_from=None, date_to=None)`**
   - Base query: `SELECT * FROM expenses WHERE user_id = ?`
   - Add optional `AND date >= ?` if `date_from` is provided
   - Add optional `AND date <= ?` if `date_to` is provided
   - Order by `date DESC`
   - Use parameterized placeholders for all values
   - Return filtered expenses list (or all if no filters)

2. **`get_expense_summary_filtered(user_id, date_from=None, date_to=None)`**
   - Base query: `SELECT SUM(amount), COUNT(*) FROM expenses WHERE user_id = ?`
   - Add same optional date clauses as above
   - Query top category: `SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? ... GROUP BY category ORDER BY total DESC LIMIT 1`
   - Return dict: `{"total_spent": ..., "transaction_count": ..., "top_category": ...}`

3. **`get_category_breakdown_filtered(user_id, date_from=None, date_to=None)`**
   - Base query: `SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? ... GROUP BY category`
   - Add optional date clauses
   - Return dict: `{category: total, ...}` (only non-zero categories)

### Implementation notes:
- All date comparisons use `>=` and `<=` (inclusive range)
- NULL filters are omitted from WHERE clause (handled with conditional logic)
- Keep existing unfiltered functions (`get_user_expenses()`, `get_expense_summary()`, `get_category_breakdown()`) unchanged

---

## Phase 2: Route Handler (`app.py`)

### Modify `/profile` route (lines 127–137):

1. **Extract and validate query parameters:**
   - `date_from = request.args.get("date_from")` 
   - `date_to = request.args.get("date_to")`
   - Validate format (YYYY-MM-DD) or set to None if invalid
   - Add error handling: if invalid format, show error message or fallback to unfiltered view

2. **Call filtered helpers:**
   - `get_user_expenses_filtered(user_id, date_from, date_to)`
   - `get_expense_summary_filtered(user_id, date_from, date_to)`
   - `get_category_breakdown_filtered(user_id, date_from, date_to)`

3. **Build template context:**
   - Add `date_from` and `date_to` to context
   - Add `filter_active` boolean (True if either date is provided and valid)
   - Add `filter_display` string for UI (e.g., "Showing expenses from Jan 1 to Dec 31, 2024")

4. **Error handling:**
   - If date_from > date_to (invalid range), show error and fall back to no filter
   - If date format is invalid, ignore and show no filter applied

---

## Phase 3: Template (`templates/profile.html`)

### Insert date filter form (between summary stats and transaction table):

1. **HTML structure (around line 48):**
   ```
   <form method="GET" class="date-filter-form">
     <div class="form-group form-inline">
       <label for="date_from">From Date:</label>
       <input type="date" name="date_from" id="date_from" value="{{ date_from or '' }}">
       
       <label for="date_to">To Date:</label>
       <input type="date" name="date_to" id="date_to" value="{{ date_to or '' }}">
       
       <button type="submit" class="btn-submit">Filter</button>
       <a href="{{ url_for('profile') }}" class="btn-clear">Clear Filter</a>
     </div>
   </form>
   ```

2. **Display filter status (below form):**
   - Show `{{ filter_display }}` if `filter_active` is True
   - Show "Showing all expenses" if no filter active

3. **No changes to:**
   - Summary stats section (values now calculated from filtered data)
   - Transaction history grid (now shows filtered transactions only)
   - Category breakdown (now shows filtered categories only)

### CSS considerations:
- Use existing `.form-group`, `.form-input`, `.btn-submit` classes
- For inline layout: add inline `style="display: flex; gap: 1rem; align-items: center;"` or create `.form-inline` class in style.css
- "Clear Filter" link should style like a secondary button

---

## Phase 4: Testing Checklist

- [ ] No filter: `/profile` shows all expenses
- [ ] Start date only: `/profile?date_from=2024-01-01` shows expenses >= that date
- [ ] End date only: `/profile?date_to=2024-12-31` shows expenses <= that date
- [ ] Both dates: `/profile?date_from=2024-01-01&date_to=2024-12-31` shows range
- [ ] Invalid dates: Gracefully fallback or show error
- [ ] Stats recalculate: Total, count, top category all update with filtered data
- [ ] Category breakdown updates: Shows only categories in filtered range
- [ ] Form pre-fills: Date inputs show current filter values
- [ ] Clear button works: Navigates to `/profile` with no parameters
- [ ] Different users: Test with different logged-in accounts

---

## Files to Modify

1. **database/db.py** — Add 3 new helper functions
2. **app.py** — Modify `/profile` route (lines 127–137)
3. **templates/profile.html** — Insert filter form and filter status display

## Files to Create

None.

---

## Order of Implementation

1. **database/db.py** — Write and test filtered helpers
2. **app.py** — Wire up route to call filtered helpers
3. **templates/profile.html** — Add filter form and display logic
4. **Manual testing** — Verify all checklist items work in the browser
