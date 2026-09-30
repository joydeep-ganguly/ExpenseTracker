from database.db import create_user, get_db, get_user_by_email
from database.queries import insert_expense

DEMO_EMAIL = "demo@spendly.com"


def _login(client, email=DEMO_EMAIL, password="demo123"):
    from database.db import seed_db

    seed_db()
    client.post("/login", data={"email": email, "password": password})
    return get_user_by_email(email)["id"]


def _count_expenses(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["cnt"]


# ------------------------------------------------------------------ #
# insert_expense                                                      #
# ------------------------------------------------------------------ #

def test_insert_expense_valid_row_is_queryable(db_path):
    user_id = create_user("Expense Tester", "expense1@example.com", "password123")

    insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

    conn = get_db()
    row = conn.execute(
        "SELECT amount, category, date, description FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_none_description_stored_as_null(db_path):
    user_id = create_user("Expense Tester", "expense2@example.com", "password123")

    insert_expense(user_id, 20.0, "Transport", "2026-03-21", None)

    conn = get_db()
    row = conn.execute(
        "SELECT description FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()

    assert row["description"] is None


# ------------------------------------------------------------------ #
# /expenses/add route                                                 #
# ------------------------------------------------------------------ #

def test_get_add_expense_unauthenticated_redirects(client):
    response = client.get("/expenses/add", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_get_add_expense_authenticated(client):
    _login(client)

    response = client.get("/expenses/add")
    body = response.data.decode()

    assert response.status_code == 200
    assert 'method="POST"' in body
    for category in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
        assert f'value="{category}"' in body


def test_post_add_expense_unauthenticated_redirects(client):
    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2026-03-20", "description": ""},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_post_add_expense_valid_redirects_and_inserts(client):
    user_id = _login(client)
    before = _count_expenses(user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "50.0", "category": "Food", "date": "2026-03-20", "description": "Lunch"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"
    assert _count_expenses(user_id) == before + 1

    conn = get_db()
    row = conn.execute(
        "SELECT amount, category, date, description FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_post_add_expense_missing_amount_shows_error(client):
    user_id = _login(client)
    before = _count_expenses(user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "", "category": "Food", "date": "2026-03-20", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Amount must be a positive number." in body
    assert _count_expenses(user_id) == before


def test_post_add_expense_zero_amount_shows_error(client):
    user_id = _login(client)
    before = _count_expenses(user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "0", "category": "Food", "date": "2026-03-20", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Amount must be a positive number." in body
    assert _count_expenses(user_id) == before


def test_post_add_expense_non_numeric_amount_shows_error(client):
    user_id = _login(client)
    before = _count_expenses(user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "abc", "category": "Food", "date": "2026-03-20", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Amount must be a positive number." in body
    assert _count_expenses(user_id) == before


def test_post_add_expense_invalid_category_shows_error(client):
    user_id = _login(client)
    before = _count_expenses(user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Crypto", "date": "2026-03-20", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Please select a valid category." in body
    assert _count_expenses(user_id) == before


def test_post_add_expense_invalid_date_shows_error(client):
    user_id = _login(client)
    before = _count_expenses(user_id)

    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "not-a-date", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Please enter a valid date." in body
    assert _count_expenses(user_id) == before


def test_post_add_expense_no_description_inserts_null(client):
    user_id = _login(client)

    response = client.post(
        "/expenses/add",
        data={"amount": "15", "category": "Other", "date": "2026-03-22", "description": ""},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"

    conn = get_db()
    row = conn.execute(
        "SELECT description FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    assert row["description"] is None
