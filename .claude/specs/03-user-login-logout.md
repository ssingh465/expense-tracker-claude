# Spec: User Login and Logout

## Overview
This feature implements the authentication flow, allowing registered users to log in using their email and password, and securely log out. It establishes the user session, which is critical for protecting subsequent features like the profile page and expense management.

## Depends on
- Step 01: Database Setup
- Step 02: User Registration

## Routes
- `GET /login` — Display login form — Public
- `POST /login` — Process login credentials — Public
- `GET /logout` — Terminate user session — Logged-in

## Database changes
No database changes.

## Templates
- **Modify:** `templates/login.html` — Add a login form with email and password fields.

## Files to change
- `app.py` — Implement the `POST /login` handler and the `/logout` route.
- `templates/login.html` — Update the template to include a form for user credentials.

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Store `user_id` in `flask.session` upon successful login.
- Use `flask.flash()` for authentication error messages.
- Use `abort(401)` or redirect to `/login` for unauthorized access to protected routes.

## Definition of done
- [ ] User can log in with valid email and password.
- [ ] User is redirected to the landing page after successful login.
- [ ] User sees an error message when providing invalid credentials.
- [ ] User can successfully log out, which clears the session.
- [ ] After logging out, the user is redirected to the login page or landing page.
- [ ] Session is cleared upon logout.