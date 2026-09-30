import os
import sqlite3
from calendar import monthrange
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db")

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

SEED_EXPENSES = [
    ("Food", 42.50, "Groceries"),
    ("Transport", 18.75, "Bus fare"),
    ("Bills", 95.00, "Electricity bill"),
    ("Bills", 60.49, "Internet bill"),
    ("Health", 33.20, "Pharmacy"),
    ("Entertainment", 24.99, "Movie tickets"),
    ("Shopping", 55.00, "Clothing"),
    ("Other", 16.31, "Miscellaneous"),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()


def create_user(name, email, password):
    conn = get_db()
    try:
        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def _seed_dates(count):
    today = date.today()
    _, days_in_month = monthrange(today.year, today.month)
    dates = []
    for i in range(count):
        day = min(1 + i * 3, days_in_month)
        dates.append(date(today.year, today.month, day).strftime("%Y-%m-%d"))
    return dates


def seed_db():
    conn = get_db()

    existing = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
    if existing["count"] > 0:
        conn.close()
        return

    password_hash = generate_password_hash("demo123")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cursor.lastrowid

    dates = _seed_dates(len(SEED_EXPENSES))
    for (category, amount, description), expense_date in zip(SEED_EXPENSES, dates):
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )

    conn.commit()
    conn.close()
