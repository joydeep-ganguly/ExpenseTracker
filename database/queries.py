from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        member_since = datetime.strptime(
            row["created_at"][:19], "%Y-%m-%d %H:%M:%S"
        ).strftime("%B %Y")
        return {"name": row["name"], "email": row["email"], "member_since": member_since}
    finally:
        conn.close()


def _build_filter(user_id, date_from, date_to):
    where = "WHERE user_id = ?"
    params = [user_id]
    if date_from and date_to:
        where += " AND date BETWEEN ? AND ?"
        params += [date_from, date_to]
    return where, params


def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        where, params = _build_filter(user_id, date_from, date_to)
        totals = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses {where}",
            params,
        ).fetchone()
        if totals["cnt"] == 0:
            return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
        top = conn.execute(
            f"SELECT category FROM expenses {where} GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params,
        ).fetchone()
        return {
            "total_spent": totals["total"],
            "transaction_count": totals["cnt"],
            "top_category": top["category"],
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    conn = get_db()
    try:
        where, params = _build_filter(user_id, date_from, date_to)
        rows = conn.execute(
            f"SELECT id, date, description, category, amount FROM expenses {where} "
            "ORDER BY date DESC, id DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_expense(expense_id, user_id, amount, category, date, description):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        where, params = _build_filter(user_id, date_from, date_to)
        rows = conn.execute(
            f"SELECT category, SUM(amount) AS total FROM expenses {where} "
            "GROUP BY category ORDER BY total DESC",
            params,
        ).fetchall()
        if not rows:
            return []
        grand_total = sum(row["total"] for row in rows)
        breakdown = [
            {
                "name": row["category"],
                "amount": row["total"],
                "pct": round(row["total"] / grand_total * 100),
            }
            for row in rows
        ]
        remainder = 100 - sum(item["pct"] for item in breakdown)
        breakdown[0]["pct"] += remainder
        return breakdown
    finally:
        conn.close()
