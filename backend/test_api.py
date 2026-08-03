from datetime import datetime

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def test_login_success():
    response = client.post(
        "/auth/login",
        json={"email": "demo@sirkome.com", "password": "demo1234"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token"]
    assert data["user"]["name"] == "Kome Isioro"


def test_admin_login_returns_admin_flag_for_dashboard():
    response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["is_admin"] is True


def test_login_failure():
    response = client.post(
        "/auth/login",
        json={"email": "demo@sirkome.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_accounts_requires_authentication():
    response = client.get("/accounts")

    assert response.status_code == 401


def test_register_creates_a_user_and_returns_profile():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    response = client.post(
        "/auth/register",
        json={
            "name": "New Customer",
            "email": f"newcustomer{timestamp}@example.com",
            "password": "strongpass123",
            "phone": "+1-555-010-9999",
            "nin": "12345678901",
            "bvn": "10987654321",
            "pin": "1234",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"].endswith("@example.com")
    assert data["user"]["account_number"].startswith("SK-")
    assert data["user"]["balance"] == 0.0

    with main.get_connection() as conn:
        user = conn.execute("SELECT id, user_id, account_number FROM users WHERE email = ?", (data["user"]["email"],)).fetchone()
        wallet = conn.execute("SELECT * FROM wallets WHERE user_id = ?", (user["user_id"],)).fetchone()

    assert wallet is not None
    assert wallet["wallet_balance"] == 0.0
    assert wallet["account_number"] == user["account_number"]


def test_login_does_not_persist_access_token_in_database():
    email = "demo@sirkome.com"
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "demo1234"},
    )

    assert response.status_code == 200
    with main.get_connection() as conn:
        user = conn.execute("SELECT token FROM users WHERE email = ?", (email,)).fetchone()

    assert user["token"] in (None, "")


def test_wallet_user_id_uses_alphanumeric_user_reference():
    response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )

    assert response.status_code == 200
    user = main.get_user_by_email("admin@sirkome.com")

    with main.get_connection() as conn:
        wallet = conn.execute(
            "SELECT user_id, wallet_id FROM wallets WHERE account_number = ?",
            (user["account_number"],),
        ).fetchone()

    assert wallet is not None
    assert wallet["user_id"] == user["user_id"]
    assert wallet["wallet_id"] == user["user_id"]


def test_admin_can_list_users():
    admin_response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["email"] == "demo@sirkome.com" for item in data)


def test_transfer_moves_funds_between_accounts():
    admin_response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    customer_response = client.post(
        "/auth/register",
        json={
            "name": "Transfer Target",
            "email": f"transfer{timestamp}@example.com",
            "password": "strongpass123",
            "phone": "+1-555-010-1000",
            "nin": "11223344556",
            "bvn": "66554433221",
        },
    )
    customer_account = customer_response.json()["user"]["account_number"]

    transfer_response = client.post(
        "/transfer",
        json={
            "from_account": "VB-ADMIN",
            "to_account": customer_account,
            "amount": 250.0,
            "description": "Demo transfer",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert transfer_response.status_code == 200
    assert transfer_response.json()["status"] == "success"
