import calendar
import sqlite3
from datetime import date, datetime

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import CATEGORIES, create_user, get_db, get_user_by_email, init_db, seed_db
from database.queries import (
    delete_expense as delete_expense_row,
    get_category_breakdown,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    insert_expense,
    update_expense,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Date-filter helpers                                                 #
# ------------------------------------------------------------------ #

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _shift_months(d, months):
    total = d.month - 1 - months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        flash("All fields are required.")
        return render_template("register.html")

    if password != confirm_password:
        flash("Passwords do not match.")
        return render_template("register.html")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        flash("Email already registered.")
        return render_template("register.html")

    flash("Account created successfully. Please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.method != "POST":
        abort(405)

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.")
        return render_template("login.html")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user_row = get_user_by_id(user_id)
    if user_row is None:
        session.clear()
        return redirect(url_for("login"))

    initials = "".join(part[0] for part in user_row["name"].split()[:2]).upper()
    user = {**user_row, "initials": initials}

    date_from = _parse_date(request.args.get("date_from"))
    date_to = _parse_date(request.args.get("date_to"))

    if date_from is None or date_to is None:
        date_from = date_to = None
    elif date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = None

    date_from_str = date_from.isoformat() if date_from else None
    date_to_str = date_to.isoformat() if date_to else None

    today = date.today()
    presets = [
        {
            "key": "this_month",
            "label": "This Month",
            "date_from": today.replace(day=1).isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "key": "last_3_months",
            "label": "Last 3 Months",
            "date_from": _shift_months(today, 3).isoformat(),
            "date_to": today.isoformat(),
        },
        {
            "key": "last_6_months",
            "label": "Last 6 Months",
            "date_from": _shift_months(today, 6).isoformat(),
            "date_to": today.isoformat(),
        },
        {"key": "all_time", "label": "All Time", "date_from": None, "date_to": None},
    ]

    active = "custom"
    for preset in presets:
        if preset["date_from"] == date_from_str and preset["date_to"] == date_to_str:
            active = preset["key"]
            break

    filters = {
        "date_from": date_from_str or "",
        "date_to": date_to_str or "",
        "active": active,
    }

    stats = get_summary_stats(user_id, date_from_str, date_to_str)
    expenses = get_recent_transactions(user_id, limit=10, date_from=date_from_str, date_to=date_to_str)
    categories = get_category_breakdown(user_id, date_from_str, date_to_str)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        expenses=expenses,
        categories=categories,
        presets=presets,
        filters=filters,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            form_values={
                "amount": "",
                "category": "",
                "date": date.today().isoformat(),
                "description": "",
            },
        )

    if request.method != "POST":
        abort(405)

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description_raw = request.form.get("description", "").strip()
    form_values = {
        "amount": amount_raw,
        "category": category,
        "date": date_raw,
        "description": description_raw,
    }

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.")
        return render_template("add_expense.html", categories=CATEGORIES, form_values=form_values)

    if category not in CATEGORIES:
        flash("Please select a valid category.")
        return render_template("add_expense.html", categories=CATEGORIES, form_values=form_values)

    try:
        datetime.strptime(date_raw, "%Y-%m-%d")
    except ValueError:
        flash("Please enter a valid date.")
        return render_template("add_expense.html", categories=CATEGORIES, form_values=form_values)

    insert_expense(session["user_id"], amount, category, date_raw, description_raw or None)
    flash("Expense added successfully.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        form_values = {
            "amount": expense["amount"],
            "category": expense["category"],
            "date": expense["date"],
            "description": expense["description"] or "",
        }
        return render_template(
            "edit_expense.html", expense=expense, categories=CATEGORIES, form_values=form_values
        )

    if request.method != "POST":
        abort(405)

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description_raw = request.form.get("description", "").strip()
    form_values = {
        "amount": amount_raw,
        "category": category,
        "date": date_raw,
        "description": description_raw,
    }

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.")
        return render_template(
            "edit_expense.html", expense=expense, categories=CATEGORIES, form_values=form_values
        )

    if category not in CATEGORIES:
        flash("Please select a valid category.")
        return render_template(
            "edit_expense.html", expense=expense, categories=CATEGORIES, form_values=form_values
        )

    try:
        datetime.strptime(date_raw, "%Y-%m-%d")
    except ValueError:
        flash("Please enter a valid date.")
        return render_template(
            "edit_expense.html", expense=expense, categories=CATEGORIES, form_values=form_values
        )

    update_expense(id, user_id, amount, category, date_raw, description_raw or None)
    flash("Expense updated successfully.")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    if get_expense_by_id(id, user_id) is None:
        abort(404)

    delete_expense_row(id, user_id)
    flash("Expense deleted.")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
