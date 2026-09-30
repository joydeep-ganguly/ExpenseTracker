import re

from database.db import create_user, get_user_by_email
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

DEMO_EMAIL = "demo@spendly.com"
ALL_CATEGORIES = {
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
}


def _seed_demo_user_id(db_path):
    from database.db import seed_db

    seed_db()
    return get_user_by_email(DEMO_EMAIL)["id"]


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(db_path):
    user_id = _seed_demo_user_id(db_path)

    result = get_user_by_id(user_id)

    assert result["name"] == "Demo User"
    assert result["email"] == DEMO_EMAIL
    assert re.match(r"^[A-Za-z]+ \d{4}$", result["member_since"])


def test_get_user_by_id_missing(db_path):
    assert get_user_by_id(99999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(db_path):
    user_id = _seed_demo_user_id(db_path)

    stats = get_summary_stats(user_id)

    assert stats["total_spent"] == 346.24
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(db_path):
    user_id = create_user("Fresh User", "fresh@example.com", "password123")

    stats = get_summary_stats(user_id)

    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_with_expenses(db_path):
    user_id = _seed_demo_user_id(db_path)

    transactions = get_recent_transactions(user_id)

    assert len(transactions) == 8
    for txn in transactions:
        assert set(txn.keys()) == {"id", "date", "description", "category", "amount"}
    dates = [txn["date"] for txn in transactions]
    assert dates == sorted(dates, reverse=True)


def test_get_recent_transactions_no_expenses(db_path):
    user_id = create_user("Fresh User", "fresh2@example.com", "password123")

    assert get_recent_transactions(user_id) == []


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_with_expenses(db_path):
    user_id = _seed_demo_user_id(db_path)

    breakdown = get_category_breakdown(user_id)

    amounts = [row["amount"] for row in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert breakdown[0]["name"] == "Bills"
    assert all(isinstance(row["pct"], int) for row in breakdown)
    assert sum(row["pct"] for row in breakdown) == 100


def test_get_category_breakdown_no_expenses(db_path):
    user_id = create_user("Fresh User", "fresh3@example.com", "password123")

    assert get_category_breakdown(user_id) == []


# ------------------------------------------------------------------ #
# /profile route                                                      #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects(client):
    response = client.get("/profile", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_profile_authenticated_demo_user(client, db_path):
    user_id = get_user_by_email(DEMO_EMAIL)["id"]
    client.post("/login", data={"email": DEMO_EMAIL, "password": "demo123"})

    response = client.get("/profile")
    body = response.data.decode()

    assert response.status_code == 200
    assert "Demo User" in body
    assert DEMO_EMAIL in body
    assert "₹" in body
    assert "346.24" in body
    assert "Bills" in body

    for category in ALL_CATEGORIES:
        assert category in body

    reference_order = [txn["description"] for txn in get_recent_transactions(user_id)]
    positions = [body.index(desc) for desc in reference_order]
    assert positions == sorted(positions)


def test_profile_new_user_no_expenses(client):
    client.post(
        "/register",
        data={
            "name": "New Person",
            "email": "newperson@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )
    client.post("/login", data={"email": "newperson@example.com", "password": "password123"})

    response = client.get("/profile")
    body = response.data.decode()

    assert response.status_code == 200
    assert "₹0.00" in body
    assert "—" in body
