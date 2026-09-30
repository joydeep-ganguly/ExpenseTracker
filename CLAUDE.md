# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly — a personal expense tracker built with Flask + SQLite (stdlib `sqlite3`, no ORM) + Jinja2. It is a teaching/scaffolding project driven by numbered spec files in the project root (`Spec_01_database_setup_prompt.md` through `Spec_09-delete-expense_prompt.md`). These are meta-prompts that generate a spec document into `.claude/specs/NN-*.md` (per `Spec_genration_prompt.md`) — the generated spec docs don't exist yet. When asked to implement a step, read the relevant `Spec_XX_*.md` for its embedded requirements/rules.

This is not a git repository (no `.git` directory).

## Run / install

```
pip install -r requirements.txt
python app.py
```
Serves at `http://127.0.0.1:5001` (Flask dev server, debug mode, no host override).

## Global conventions (apply across all steps, stated repeatedly in the specs)

- **No ORM / no SQLAlchemy.** Raw `sqlite3` only, always through `database/db.py`'s `get_db()`.
- **Parameterized queries only** — never string-format or f-string values into SQL, including dates.
- **`PRAGMA foreign_keys = ON`** must be set on every DB connection.
- **Currency always renders as ₹**, never £ or $.
- **Dates are always `YYYY-MM-DD`**, parsed/validated via `datetime.strptime`.
- **Fixed 7-category list, exact strings**: Food, Transport, Bills, Health, Entertainment, Shopping, Other.
- **All page templates extend `base.html`** (`{% extends "base.html" %}`).
- **No inline styles anywhere**, with one carved-out exception: `style="display:inline"` on the delete-expense `<form>` (Step 09) — a layout-utility value, not a design value. No hex colors or design values may ever be inlined.
- **Use CSS variables, never hardcoded hex** — see the design-system tokens below.
- **Use `url_for()` for every internal link**, never a hardcoded path. (Note: current `login.html`/`register.html` forms still use hardcoded `action="/login"` / `action="/register"` — fix when touching those files.)
- **Session key for the logged-in user is `session["user_id"]`** (an integer), via Flask's built-in `session` — no custom session mechanism.
- **Auth guard pattern**: check `session.get("user_id")`; redirect unauthenticated users to `url_for("login")`.
- Passwords are hashed with `generate_password_hash`/`check_password_hash` from `werkzeug.security`.

## Database (once Step 1 is implemented)

- `database/db.py` provides `get_db()` (opens `spendly.db` in project root, `row_factory = sqlite3.Row`, foreign keys on), `init_db()` (idempotent `CREATE TABLE IF NOT EXISTS`), `seed_db()` (idempotent demo-data seed).
- `database/queries.py` (introduced in Step 5) holds pure query helpers with **no Flask imports** — always open via `get_db()` and close the connection before returning.
- Schema: `users(id, name, email, password_hash, created_at)`, `expenses(id, user_id, amount REAL, category, date, description, created_at)`.
- Both `init_db()` and `seed_db()` are called inside `app.app_context()` in `app.py` on startup, before any route is served.

## CSS design system (`static/css/style.css`)

`:root` custom properties — reuse these, don't invent new hex values:
- Ink/paper: `--ink`, `--ink-soft`, `--ink-muted`, `--ink-faint`, `--paper`, `--paper-warm`, `--paper-card`
- Accent: `--accent` (green), `--accent-light`, `--accent-2` (amber), `--accent-2-light`, `--danger`, `--danger-light`
- Borders: `--border`, `--border-soft`
- Fonts: `--font-display` (DM Serif Display), `--font-body` (DM Sans)
- Layout: `--max-width` (1200px), `--auth-width` (440px); radii: `--radius-sm/md/lg`

`base.html` blocks available to child templates: `title`, `head`, `content`, `scripts`.

Page-specific CSS (e.g. `static/css/landing.css`) overrides base rules via **cascade/load order** — link it in that page's `head` block so it loads after `style.css`, rather than editing `style.css` directly.

## Testing

`pytest` and `pytest-flask` are in `requirements.txt` but not yet configured — no `tests/` directory, `conftest.py`, or `pytest.ini` exist yet. Specs from Step 5 onward reference planned test files (`tests/test_backend_connection.py`, `tests/test_add_expense.py`, etc.) with specific expected demo-data values (e.g. total_spent = ₹346.24, transaction_count = 8, top_category = "Bills") — match these when the demo seed data is implemented.
