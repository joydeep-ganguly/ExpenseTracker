from database.db import create_user, get_db, get_user_by_email
from database.queries import delete_expense, insert_expense

DEMO_EMAIL = "demo@spendly.com"


def _login(client, email=DEMO_EMAIL, password="demo123"):
    from database.db import seed_db

    seed_db()
    client.post("/login", data={"email": email, "password": password})
    return get_user_by_email(email)["id"]


def _expense_exists(expense_id):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return row is not None


# ------------------------------------------------------------------ #
# delete_expense                                                      #
# ------------------------------------------------------------------ #

def test_delete_expense_valid_owner_removes_row(db_path):
    user_id = create_user("Owner", "owner1@example.com", "password123")
    expense_id = insert_expense(user_id, 10.0, "Food", "2026-03-20", "Snacks")

    delete_expense(expense_id, user_id)

    assert not _expense_exists(expense_id)


def test_delete_expense_wrong_owner_leaves_row(db_path):
    owner_id = create_user("Owner", "owner2@example.com", "password123")
    other_id = create_user("Other", "other2@example.com", "password123")
    expense_id = insert_expense(owner_id, 10.0, "Food", "2026-03-20", "Snacks")

    delete_expense(expense_id, other_id)

    assert _expense_exists(expense_id)


def test_delete_expense_nonexistent_id_no_error(db_path):
    user_id = create_user("Owner", "owner3@example.com", "password123")

    delete_expense(999999, user_id)  # should not raise


# ------------------------------------------------------------------ #
# /expenses/<id>/delete route                                         #
# ------------------------------------------------------------------ #

def test_post_delete_expense_unauthenticated_redirects(client):
    response = client.post("/expenses/1/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_post_delete_expense_own_expense(client):
    user_id = _login(client)
    expense_id = insert_expense(user_id, 10.0, "Food", "2026-03-20", "Snacks")

    response = client.post(f"/expenses/{expense_id}/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"] == "/profile"
    assert not _expense_exists(expense_id)


def test_post_delete_expense_other_users_expense_404(client):
    other_id = create_user("Other", "other4@example.com", "password123")
    expense_id = insert_expense(other_id, 10.0, "Food", "2026-03-20", "Snacks")
    _login(client)

    response = client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 404
    assert _expense_exists(expense_id)


def test_post_delete_expense_nonexistent_id_404(client):
    _login(client)

    response = client.post("/expenses/999999/delete")

    assert response.status_code == 404


def test_get_delete_expense_returns_405(client):
    response = client.get("/expenses/1/delete")

    assert response.status_code == 405
