# Spec: Add Expense

## Overview
This feature allows logged-in users to record their spending by adding new expense entries to the system. This is a core functionality of Spendly, enabling the application to move from a read-only profile view to an interactive tracking tool.

## Depends on
- 05-connect-profile-backend (User session and profile data)

## Routes
- `GET /expenses/add` — Render the expense addition form — logged-in
- `POST /expenses/add` — Process the form and save the expense to the database — logged-in

## Database changes
No database changes. The `expenses` table already exists with the necessary columns: `user_id`, `amount`, `category`, `date`, `description`.

## Templates
- **Create:** `templates/add_expense.html` — A form for inputting expense details (amount, category, date, description).
- **Modify:** `templates/base.html` — Add a link to the "Add Expense" page in the navigation or profile section.

## Files to change
- `app.py` — Implement the GET and POST handlers for `/expenses/add`.
- `database/db.py` — Add a helper function `create_expense(user_id, amount, category, date, description)` to handle the insertion.

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate that `amount` is a positive number.
- Ensure `date` is provided and in a valid format.
- Use `flash()` to provide feedback on success or failure.
- Redirect to `/profile` after a successful addition.

## Definition of done
- [ ] Navigating to `/expenses/add` while logged in renders a form.
- [ ] Attempting to access `/expenses/add` while logged out redirects to `/login`.
- [ ] Submitting the form with missing required fields (amount, category, date) triggers a flash error and keeps the user on the page.
- [ ] Submitting the form with a negative amount triggers a validation error.
- [ ] Submitting a valid expense saves the record to the `expenses` table and redirects the user to the profile page.
- [ ] The newly added expense is immediately visible in the "Recent Transactions" list on the profile page.
