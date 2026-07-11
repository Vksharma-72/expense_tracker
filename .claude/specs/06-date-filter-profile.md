# Spec: Date Filter for Profile Page

## Overview
This feature adds date-range filtering to the profile page, allowing authenticated users to view their expenses within a selected time period. The filter operates on the existing transaction history, summary stats (total spent, transaction count, top category), and category breakdown—without changing the database schema or adding new routes. Users select start and end dates via HTML input fields, and the page dynamically recalculates all statistics and displays only matching expenses.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables exist)
- Step 2: Registration (user accounts exist in DB)
- Step 3: Login + Logout (session authentication works)
- Step 4: Profile page design (UI layout and templates complete)
- Step 5: Profile backend integration (live data queries from DB)

## Routes
No new routes. Modify existing route:
- `GET /profile` — Accept optional `?date_from=YYYY-MM-DD` and `?date_to=YYYY-MM-DD` query parameters; filter all data (transactions, stats, breakdown) to the given date range; default to showing all expenses if no filter is provided

## Database changes
No schema changes. The `expenses` table's existing `date` column (TEXT, YYYY-MM-DD format) is sufficient. Add helper function to `database/db.py`:
- `get_user_expenses_filtered(user_id, date_from=None, date_to=None)` — returns list of expenses for a user within the optional date range, ordered by date DESC

Add or modify helpers to support filtering:
- `get_expense_summary_filtered(user_id, date_from=None, date_to=None)` — returns dict with total_spent, transaction_count, top_category, all calculated only from expenses within the date range
- `get_category_breakdown_filtered(user_id, date_from=None, date_to=None)` — returns dict of category totals, filtered by date range

## Templates
Modify `profile.html`:
- Add a date filter section above the transaction history table with two input fields: "From Date" and "To Date" (both `<input type="date">`)
- Add a "Filter" button to submit the form (or auto-submit on change)
- Display the currently applied date range as a label (e.g., "Showing expenses from Jan 1, 2024 to Dec 31, 2024")
- Add a "Clear Filter" button/link to reset to all expenses
- All other sections (member since, summary stats, category breakdown) remain visually the same but display filtered data

## Files to change
- `app.py` — modify `/profile` route:
  - Extract `date_from` and `date_to` from `request.args` (query parameters)
  - Validate both are optional but must be valid YYYY-MM-DD format if provided
  - Call filtered helper functions: `get_user_expenses_filtered()`, `get_expense_summary_filtered()`, `get_category_breakdown_filtered()`
  - Pass filter parameters and current filter state to the template context
- `database/db.py` — add or update three helper functions:
  - `get_user_expenses_filtered(user_id, date_from=None, date_to=None)` — use parameterized WHERE clause with date comparisons
  - `get_expense_summary_filtered(user_id, date_from=None, date_to=None)`
  - `get_category_breakdown_filtered(user_id, date_from=None, date_to=None)`
- `templates/profile.html` — add filter form and display current filter state

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Date filtering uses SQL `>=` and `<=` comparisons on TEXT columns (YYYY-MM-DD format is lexicographically sortable)
- If both `date_from` and `date_to` are NULL, queries return all expenses (no filter applied)
- If only `date_from` is provided, filter is `date >= date_from` (no upper bound)
- If only `date_to` is provided, filter is `date <= date_to` (no lower bound)
- If both are provided, filter is `date >= date_from AND date <= date_to`
- Validate that `date_from` and `date_to` are valid dates (YYYY-MM-DD); return error or fallback to unfiltered if invalid
- All HTML form inputs must have proper `name` attributes for query parameter binding
- Summary stats (total spent, transaction count, top category) must be recalculated based on filtered data, not all data
- Category breakdown must only include categories that have expenses in the filtered range
- The filter form should use HTTP GET (to allow bookmarking/sharing filtered URLs) or a simple POST that redirects to a GET
- Preserve the layout and styling of the profile page from Step 4

## Definition of done
- [ ] Visiting `/profile` displays all expenses when no date filter is provided
- [ ] Visiting `/profile?date_from=YYYY-MM-DD` shows only expenses on or after that date
- [ ] Visiting `/profile?date_to=YYYY-MM-DD` shows only expenses on or before that date
- [ ] Visiting `/profile?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` shows only expenses within the range (inclusive)
- [ ] The page displays the currently applied date filter (or "No filter" if all expenses shown)
- [ ] A "Clear Filter" button removes all filter parameters and shows all expenses
- [ ] The "Total Spent" stat is recalculated to sum only filtered expenses
- [ ] The "Transaction Count" stat shows only the count of filtered expenses
- [ ] The "Top Category" stat is calculated only from filtered expenses
- [ ] The category breakdown table shows only categories with expenses in the filtered range
- [ ] The transaction history table shows only expenses in the filtered date range
- [ ] Invalid date format (non-YYYY-MM-DD) either shows an error or defaults to unfiltered view
- [ ] Date filter parameters are persistent in the query string (can bookmark or share)
- [ ] A different user's profile shows different filtered data
- [ ] All SQL queries use parameterized placeholders (`?`), never string interpolation
