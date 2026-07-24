from datetime import datetime

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_login_success():
    response = client.post(
        "/auth/login",
        json={"email": "demo@sirkome.com", "password": "demo1234"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "demo-token"
    assert data["user"]["name"] == "Kome Isioro"


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
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"].endswith("@example.com")
    assert data["user"]["account_number"].startswith("VB-")
    assert data["user"]["balance"] == 0.0


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
