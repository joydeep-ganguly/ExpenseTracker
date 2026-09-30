from database.db import create_user, get_db, get_user_by_email
from database.queries import get_expense_by_id, insert_expense, update_expense

DEMO_EMAIL = "demo@spendly.com"


def _login(client, email=DEMO_EMAIL, password="demo123"):
    from database.db import seed_db

    seed_db()
    client.post("/login", data={"email": email, "password": password})
    return get_user_by_email(email)["id"]


def _fetch_expense(expense_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ------------------------------------------------------------------ #
# get_expense_by_id                                                   #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_valid_owner(db_path):
    user_id = create_user("Owner", "owner1@example.com", "password123")
    expense_id = insert_expense(user_id, 25.0, "Food", "2026-03-20", "Snacks")

    result = get_expense_by_id(expense_id, user_id)

    assert result is not None
    assert result["amount"] == 25.0
    assert result["category"] == "Food"
    assert result["date"] == "2026-03-20"
    assert result["description"] == "Snacks"


def test_get_expense_by_id_wrong_owner(db_path):
    owner_id = create_user("Owner", "owner2@example.com", "password123")
    other_id = create_user("Other", "other2@example.com", "password123")
    expense_id = insert_expense(owner_id, 25.0, "Food", "2026-03-20", "Snacks")

    assert get_expense_by_id(expense_id, other_id) is None


def test_get_expense_by_id_nonexistent(db_path):
    user_id = create_user("Owner", "owner3@example.com", "password123")

    assert get_expense_by_id(99999, user_id) is None


# ------------------------------------------------------------------ #
# update_expense                                                      #
# ------------------------------------------------------------------ #

def test_update_expense_valid_owner_reflects_change(db_path):
    user_id = create_user("Owner", "owner4@example.com", "password123")
    expense_id = insert_expense(user_id, 25.0, "Food", "2026-03-20", "Snacks")

    update_expense(expense_id, user_id, 99.0, "Bills", "2026-04-01", "Rent")

    row = _fetch_expense(expense_id)
    assert row["amount"] == 99.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-04-01"
    assert row["description"] == "Rent"


def test_update_expense_wrong_owner_no_change(db_path):
    owner_id = create_user("Owner", "owner5@example.com", "password123")
    other_id = create_user("Other", "other5@example.com", "password123")
    expense_id = insert_expense(owner_id, 25.0, "Food", "2026-03-20", "Snacks")

    update_expense(expense_id, other_id, 99.0, "Bills", "2026-04-01", "Rent")

    row = _fetch_expense(expense_id)
    assert row["amount"] == 25.0
    assert row["category"] == "Food"


# ------------------------------------------------------------------ #
# /expenses/<id>/edit route                                           #
# ------------------------------------------------------------------ #

def test_get_edit_expense_unauthenticated_redirects(client):
    response = client.get("/expenses/1/edit", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_get_edit_expense_own_expense(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.get(f"/expenses/{expense_id}/edit")
    body = response.data.decode()

    assert response.status_code == 200
    assert 'value="42.0"' in body
    assert 'value="2026-05-01"' in body
    assert 'value="Checkup"' in body
    assert f'option value="Health" selected' in body


def test_get_edit_expense_other_users_expense_404(client):
    other_id = create_user("Other", "other6@example.com", "password123")
    expense_id = insert_expense(other_id, 10.0, "Food", "2026-03-20", "Snacks")
    _login(client)

    response = client.get(f"/expenses/{expense_id}/edit")

    assert response.status_code == 404


def test_get_edit_expense_nonexistent_404(client):
    _login(client)

    response = client.get("/expenses/999999/edit")

    assert response.status_code == 404


def test_post_edit_expense_unauthenticated_redirects(client):
    response = client.post(
        "/expenses/1/edit",
        data={"amount": "10", "category": "Food", "date": "2026-03-20", "description": ""},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_post_edit_expense_valid_redirects_and_updates(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "77.5", "category": "Bills", "date": "2026-06-15", "description": "Updated"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"

    row = _fetch_expense(expense_id)
    assert row["amount"] == 77.5
    assert row["category"] == "Bills"
    assert row["date"] == "2026-06-15"
    assert row["description"] == "Updated"


def test_post_edit_expense_other_users_expense_404(client):
    other_id = create_user("Other", "other7@example.com", "password123")
    expense_id = insert_expense(other_id, 10.0, "Food", "2026-03-20", "Snacks")
    _login(client)

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "10", "category": "Food", "date": "2026-03-20", "description": ""},
    )

    assert response.status_code == 404


def test_post_edit_expense_missing_amount_shows_error(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "", "category": "Health", "date": "2026-05-01", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Amount must be a positive number." in body
    assert _fetch_expense(expense_id)["amount"] == 42.0


def test_post_edit_expense_zero_amount_shows_error(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "0", "category": "Health", "date": "2026-05-01", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Amount must be a positive number." in body
    assert _fetch_expense(expense_id)["amount"] == 42.0


def test_post_edit_expense_non_numeric_amount_shows_error(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "abc", "category": "Health", "date": "2026-05-01", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Amount must be a positive number." in body
    assert _fetch_expense(expense_id)["amount"] == 42.0


def test_post_edit_expense_invalid_category_shows_error(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "42.0", "category": "Crypto", "date": "2026-05-01", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Please select a valid category." in body
    assert _fetch_expense(expense_id)["category"] == "Health"


def test_post_edit_expense_invalid_date_shows_error(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "42.0", "category": "Health", "date": "not-a-date", "description": ""},
    )
    body = response.data.decode()

    assert response.status_code == 200
    assert "Please enter a valid date." in body
    assert _fetch_expense(expense_id)["date"] == "2026-05-01"


def test_post_edit_expense_no_description_saves_null(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 42.0, "Health", "2026-05-01", "Checkup")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "42.0", "category": "Health", "date": "2026-05-01", "description": ""},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"
    assert _fetch_expense(expense_id)["description"] is None
