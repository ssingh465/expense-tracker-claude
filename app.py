from flask import Flask, render_template, request, redirect, url_for, flash, session

from database.db import get_db, init_db, seed_db, get_user_by_email

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"


# ------------------------------------------------------------------ #
# Database initialization                                              #
# ------------------------------------------------------------------ #

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not all([name, email, password, confirm_password]):
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        from werkzeug.security import generate_password_hash
        from database.db import create_user

        hashed_password = generate_password_hash(password)
        if create_user(name, email, hashed_password):
            flash("Account created successfully!", "success")
            return redirect(url_for("login"))
        else:
            flash("Email already registered.", "error")
            return render_template("register.html")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("landing"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("login.html")

        from werkzeug.security import check_password_hash
        user = get_user_by_email(email)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("landing"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    if "user_id" not in session:
        return redirect(url_for("landing"))
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
