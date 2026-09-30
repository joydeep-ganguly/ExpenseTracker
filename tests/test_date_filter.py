from datetime import date

from database.db import get_db, get_user_by_email
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)

DEMO_EMAIL = "demo@spendly.com"


def _seed_demo_user_id():
    from database.db import seed_db

    seed_db()
    return get_user_by_email(DEMO_EMAIL)["id"]


def _insert_expense(user_id, amount, category, expense_date, description="test"):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Query helpers — date filtering                                      #
# ------------------------------------------------------------------ #

def test_summary_stats_unfiltered_matches_step05(db_path):
    user_id = _seed_demo_user_id()

    stats = get_summary_stats(user_id)

    assert stats["total_spent"] == 346.24
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_summary_stats_respects_date_range(db_path):
    user_id = _seed_demo_user_id()
    _insert_expense(user_id, 10.00, "Food", "2020-01-05")
    _insert_expense(user_id, 20.00, "Food", "2020-01-10")

    stats = get_summary_stats(user_id, "2020-01-01", "2020-01-31")

    assert stats["total_spent"] == 30.00
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Food"


def test_summary_stats_empty_range_returns_zero_state(db_path):
    user_id = _seed_demo_user_id()

    stats = get_summary_stats(user_id, "2020-01-01", "2020-01-02")

    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_recent_transactions_respects_date_range(db_path):
    user_id = _seed_demo_user_id()
    _insert_expense(user_id, 10.00, "Food", "2020-01-05", "in range")
    _insert_expense(user_id, 20.00, "Food", "2019-12-31", "out of range")

    transactions = get_recent_transactions(user_id, date_from="2020-01-01", date_to="2020-01-31")

    assert len(transactions) == 1
    assert transactions[0]["description"] == "in range"


def test_category_breakdown_respects_date_range(db_path):
    user_id = _seed_demo_user_id()
    _insert_expense(user_id, 10.00, "Food", "2020-01-05")
    _insert_expense(user_id, 20.00, "Transport", "2020-01-06")

    breakdown = get_category_breakdown(user_id, "2020-01-01", "2020-01-31")

    names = {row["name"] for row in breakdown}
    assert names == {"Food", "Transport"}
    assert sum(row["pct"] for row in breakdown) == 100


def test_category_breakdown_empty_range_returns_empty_list(db_path):
    user_id = _seed_demo_user_id()

    assert get_category_breakdown(user_id, "2020-01-01", "2020-01-02") == []


# ------------------------------------------------------------------ #
# /profile route — date filtering                                     #
# ------------------------------------------------------------------ #

def test_profile_no_query_params_is_unfiltered(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": "demo123"})

    response = client.get("/profile")
    body = response.data.decode()

    assert response.status_code == 200
    assert "346.24" in body
    assert 'class="filter-btn filter-btn-active">All Time' in body


def test_profile_this_month_preset(client):
    user_id = get_user_by_email(DEMO_EMAIL)["id"]
    client.post("/login", data={"email": DEMO_EMAIL, "password": "demo123"})
    today = date.today()
    first_of_month = today.replace(day=1).isoformat()

    # Seed dates are spread across days 1-22 of the current month (Step 01), so
    # some may fall after "today" on an early-month test run — compute the
    # expected total the same way the route does, rather than assuming all
    # 8 seed expenses are in range.
    expected_stats = get_summary_stats(user_id, first_of_month, today.isoformat())

    response = client.get(f"/profile?date_from={first_of_month}&date_to={today.isoformat()}")
    body = response.data.decode()

    assert response.status_code == 200
    assert "%.2f" % expected_stats["total_spent"] in body
    assert 'This Month</a>' in body
    assert "filter-btn-active" in body


def test_profile_out_of_range_shows_zero_state(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": "demo123"})

    response = client.get("/profile?date_from=2020-01-01&date_to=2020-01-02")
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹0.00" in body
    assert "—" in body


def test_profile_reversed_range_flashes_and_falls_back(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": "demo123"})

    response = client.get("/profile?date_from=2026-06-01&date_to=2026-01-01")
    body = response.data.decode()

    assert response.status_code == 200
    assert "Start date must be before end date." in body
    assert "346.24" in body  # fell back to unfiltered


def test_profile_malformed_date_does_not_crash(client):
    client.post("/login", data={"email": DEMO_EMAIL, "password": "demo123"})

    response = client.get("/profile?date_from=not-a-date&date_to=also-bad")
    body = response.data.decode()

    assert response.status_code == 200
    assert "346.24" in body  # unfiltered fallback
