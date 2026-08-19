# CLAUDE.md

## Project Overview

This is a Flask-based expense tracking application built for educational purposes. It allows users to register, log in, and track their expenses. The codebase is structured as a step-by-step learning project, with placeholder routes intended to be implemented by students in upcoming steps.

## Architecture

```
expense-tracker/
├── app.py                          # Flask app entry point & route handlers
├── requirements.txt                # Project dependencies
├── app.log                         # Runtime application log
├── database/                       # Data persistence layer
│   ├── __init__.py                # Python package marker
│   └── db.py                      # SQLite connection & init logic
│                                   # (get_db, init_db, seed_db)
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                  # Base template
│   ├── landing.html               # Landing page
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── terms.html                 # Terms of service
│   └── privacy.html               # Privacy policy
└── static/                         # Static assets
    ├── css/
    │   └── style.css              # Stylesheet
    └── js/
        └── main.js                # Client-side JavaScript
```

**Where things belong:**
- New routes → `app.py` only, no blueprints
- DB logic → `database/db.py` only, never inline in routes
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file, not inline `<style>` tags

## Code Style

- **Python**: Follow PEP 8 conventions. Use `snake_case` for all variables and functions.
- **Templates**: Jinja2 with `url_for()` for every internal link — never hardcode URLs.
- **Route functions**: One responsibility only — fetch data, render template, done.
- **DB queries**: Always use parameterized queries (`?` placeholders) — never f-strings in SQL.
- **Error handling**: Use `abort()` for HTTP errors, not bare `return "error string"`.
- Placeholder routes return simple string responses indicating which step will implement them (e.g., `"Logout — coming in Step 3"`).

## Tech Constraints

- **Python Version**: Python 3.10+ assumed — f-strings and `match` statements are fine.
- **Framework**: Flask only — no FastAPI, no Django, no other web frameworks.
- **Database**: SQLite only — no PostgreSQL, no SQLAlchemy ORM, no external DB.
- **Frontend**: Vanilla JS only — no React, no jQuery, no npm packages.
- **Dependencies**: No new pip packages — work within `requirements.txt` as-is unless explicitly told otherwise.
- **Server**: Werkzeug 3.1.6 (via Flask 3.1.3).
- **Testing**: pytest 8.3.5 with pytest-flask 1.3.0.
- The app runs on port 5001 (not the default 5000) to avoid conflicts.

## Commands

```bash
# Setup
python -m venv .venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Run a specific test by name
pytest -k "test_name"

# Run tests with output visible
pytest -s
```

## Warnings and Things to Avoid

- **Never use raw string returns for stub routes** once a step is implemented — always render a template.
- **Never hardcode URLs** in templates — always use `url_for()`.
- **Never put DB logic in route functions** — it belongs in `database/db.py`.
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync.
- **Never use JS frameworks** — the frontend is intentionally vanilla.
- **`database/db.py` is currently empty** — do not assume helpers exist until the step that implements them.
- **FK enforcement is manual** — SQLite foreign keys are off by default; `get_db()` must run `PRAGMA foreign_keys = ON` on every connection.
- The app runs on **port 5001**, not the Flask default 5000 — don't change this.