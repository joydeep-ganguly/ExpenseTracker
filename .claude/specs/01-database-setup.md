# Spec 01: Database Setup

## 1. Overview

This step replaces the stub implementation in `database/db.py` with a working SQLite persistence layer. It establishes the `users` and `expenses` tables, connection handling, and demo-data seeding that every later step depends on.

This is the foundational step of the project. Authentication (registration, login, sessions), user profile handling, and all expense tracking functionality (create, read, update, delete) require a working database connection and schema before they can be implemented. No other step can be completed until this one is done.

## 2. Depends on

None. This is the first implementation step and has no prerequisites.

## 3. Routes

- No new routes are introduced in this step.
- Existing placeholder routes in `app.py` remain unchanged in behavior and signature.

## 4. Database Schema

### Table A: `users`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| name | TEXT | NOT NULL |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

### Table B: `expenses`

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| user_id | INTEGER | NOT NULL, FOREIGN KEY → users(id) |
| amount | REAL | NOT NULL |
| category | TEXT | NOT NULL |
| date | TEXT | NOT NULL — must be stored as `YYYY-MM-DD` |
| description | TEXT | NULL allowed |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP |

## 5. Functions to Implement (`database/db.py`)

| Function | Responsibility |
|---|---|
| `get_db()` | Opens a connection to `spendly.db` in the project root, sets `row_factory = sqlite3.Row`, enables `PRAGMA foreign_keys = ON`, and returns the connection. |
| `init_db()` | Creates the `users` and `expenses` tables using `CREATE TABLE IF NOT EXISTS`. Safe to call multiple times without side effects. |
| `seed_db()` | Checks whether the `users` table already has rows; if so, returns early without inserting anything. Otherwise inserts one demo user (name: Demo User, email: demo@spendly.com, password: demo123, hashed via werkzeug) and 8 sample expenses linked to that user, covering all 7 categories, with dates spread across the current month. |

## 6. Changes to `app.py`

- Import `get_db`, `init_db`, and `seed_db` from `database.db`.
- Call `init_db()` and `seed_db()` inside `app.app_context()` during application startup.
- The database must be fully initialized and seeded before any route is served.

## 7. Files to Change

- `database/db.py`
- `app.py`

## 8. Files to Create

None.

## 9. Dependencies

- No new pip packages are required.
- Use the standard library `sqlite3` module.
- Use `werkzeug.security` (already listed in `requirements.txt`) for password hashing.

## 10. Categories (Fixed List)

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

## 11. Rules for Implementation

- No ORM, no SQLAlchemy — raw `sqlite3` only.
- Parameterized queries only — never use string formatting or f-strings to build SQL.
- `PRAGMA foreign_keys = ON` must be set on every connection returned by `get_db()`.
- `amount` must be stored as `REAL`, not `INTEGER`.
- Passwords must be hashed using `generate_password_hash` from `werkzeug.security`.
- `seed_db()` must be idempotent — safe to call on every app startup without creating duplicate data.
- Dates must always be stored and handled in `YYYY-MM-DD` format.

## 12. Expected Behavior

- `get_db()` must return a usable connection with `row_factory = sqlite3.Row` and foreign key enforcement enabled.
- `init_db()` must ensure both tables exist with the schema defined in Section 4, and must not error or duplicate tables if run repeatedly.
- `seed_db()` must ensure exactly one demo user and 8 demo expenses exist after the first run, and must not add more on subsequent runs.
- Database-level constraints must enforce: primary keys, uniqueness of `users.email`, `NOT NULL` fields, and the foreign key relationship between `expenses.user_id` and `users.id`.

## 13. Error Handling Expectations

- Inserting a user with a duplicate email must raise a `UNIQUE` constraint failure.
- Inserting an expense with a `user_id` that does not exist in `users` must raise a foreign key constraint failure.
- Malformed or invalid queries must raise clear, unsuppressed errors so issues surface during development rather than failing silently.

## 14. Definition of Done

- [ ] Database file (`spendly.db`) is created on app startup.
- [ ] Both `users` and `expenses` tables exist with the correct schema and constraints.
- [ ] Demo user exists with a properly hashed password.
- [ ] 8 sample expenses exist, covering all 7 categories.
- [ ] Repeated app startups do not create duplicate seed data.
- [ ] App starts without errors.
- [ ] Foreign key enforcement is active and verified.
- [ ] All database queries use parameterized SQL.
