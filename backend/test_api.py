from datetime import datetime

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def register_verified_user(name, email, password, phone, nin, bvn, pin="1234"):
    setup_response = client.post("/auth/send-verification", json={"email": email})
    assert setup_response.status_code == 200

    code = main.issue_verification_code(email)
    verify_response = client.post("/auth/verify-email", json={"email": email, "code": code})
    assert verify_response.status_code == 200

    response = client.post(
        "/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
            "phone": phone,
            "nin": nin,
            "bvn": bvn,
            "pin": pin,
        },
    )

    assert response.status_code == 200
    return response


def test_login_success():
    response = client.post(
        "/auth/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "demo1234"},
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


def test_admin_seed_account_has_funding_for_transfers():
    admin = main.get_user_by_email("admin@sirkome.com")
    assert admin is not None
    wallet = main.get_wallet_by_account(admin["account_number"])
    assert wallet is not None
    assert wallet["wallet_balance"] == 50000000.0


def test_login_failure():
    response = client.post(
        "/auth/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_register_rejects_weak_passwords():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    response = client.post(
        "/auth/register",
        json={
            "name": "Weak Password User",
            "email": f"weakpass{timestamp}@example.com",
            "password": "weakpass",
            "phone": "+1-555-010-7777",
            "nin": "12345678901",
            "bvn": "10987654321",
            "pin": "1234",
        },
    )

    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"].lower()


def test_register_does_not_return_access_token():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    response = register_verified_user(
        name="No Token User",
        email=f"notoken{timestamp}@example.com",
        password="Strongpass!123",
        phone="+1-555-010-7788",
        nin="12345678902",
        bvn="10987654322",
        pin="1234",
    )

    assert response.status_code == 200
    assert "token" not in response.json()
    assert "user" in response.json()


def test_email_verification_is_required_before_registration():
    email = f"verify{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
    setup_response = client.post("/auth/send-verification", json={"email": email})
    assert setup_response.status_code == 200

    raw_code = main.issue_verification_code(email)
    verify_response = client.post("/auth/verify-email", json={"email": email, "code": raw_code})
    assert verify_response.status_code == 200

    response = client.post(
        "/auth/register",
        json={
            "name": "Verified User",
            "email": email,
            "password": "Strongpass!123",
            "phone": "+1-555-010-2100",
            "nin": "12345678905",
            "bvn": "10987654325",
            "pin": "1234",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["email"] == email


def test_register_rejects_existing_registration_identifiers():
    existing_user = main.get_user_by_email("komeisioro+demo@gmail.com")
    base_payload = {
        "name": "Duplicate Customer",
        "email": "new-duplicate-check@example.com",
        "password": "Strongpass!123",
        "phone": "08012345678",
        "nin": "98765432109",
        "bvn": "87654321098",
        "pin": "1234",
    }

    for field, value in {
        "email": existing_user["email"],
        "phone": existing_user["phone"],
        "nin": existing_user["nin"],
        "bvn": existing_user["bvn"],
    }.items():
        email = f"duplicate-{field}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}@example.com"
        payload = {**base_payload, "email": email, field: value}
        code = main.issue_verification_code(email)
        assert main.verify_email_code(email, code)
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "Existing user found. Do you want to login?"


def test_admin_can_freeze_and_unfreeze_a_customer():
    admin_response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    customer_response = register_verified_user(
        name="Freeze Me",
        email=f"freeze{timestamp}@example.com",
        password="Strongpass!123",
        phone="+1-555-010-7799",
        nin="12345678903",
        bvn="10987654323",
        pin="1234",
    )
    customer_id = customer_response.json()["user"]["account_number"]

    freeze_response = client.patch(
        f"/admin/users/{customer_id}/freeze",
        json={"is_frozen": True, "reason": "Policy review"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert freeze_response.status_code == 200
    assert freeze_response.json()["user"]["is_frozen"] is True

    unfreeze_response = client.patch(
        f"/admin/users/{customer_id}/freeze",
        json={"is_frozen": False, "reason": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unfreeze_response.status_code == 200
    assert unfreeze_response.json()["user"]["is_frozen"] is False


def test_admin_login_returns_admin_flag():
    response = client.post(
        "/auth/login",
        json={"email": "komeisioro+admin@gmail.com", "password": "admin1234"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is True


def test_accounts_requires_authentication():
    response = client.get("/accounts")

    assert response.status_code == 401


def test_saved_accounts_are_user_specific_and_require_authentication():
    login_response = client.post(
        "/auth/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "demo1234"},
    )
    token = login_response.json()["token"]

    response = client.get("/saved-accounts", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    response = client.post(
        "/saved-accounts",
        json={"account_number": "SK-ADMIN", "account_name": "Admin User"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["account_number"] == "SK-ADMIN"

    response = client.get("/saved-accounts", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert any(item["account_number"] == "SK-ADMIN" for item in data)

    guest_response = client.get("/saved-accounts")
    assert guest_response.status_code == 401


def test_transactions_support_pagination_metadata():
    login_response = client.post(
        "/auth/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "demo1234"},
    )
    token = login_response.json()["token"]

    response = client.get(
        "/transactions?page=1&per_page=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"page", "per_page", "total", "pages", "items"}
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert len(data["items"]) <= 2


def test_register_creates_a_user_and_returns_profile():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    response = register_verified_user(
        name="New Customer",
        email=f"newcustomer{timestamp}@example.com",
        password="Strongpass!123",
        phone="+1-555-010-9999",
        nin="12345678901",
        bvn="10987654321",
        pin="1234",
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
    email = "komeisioro+demo@gmail.com"
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
        json={"email": "komeisioro+admin@gmail.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    customer_response = register_verified_user(
        name="Transfer Target",
        email=f"transfer{timestamp}@example.com",
        password="Strongpass!123",
        phone="+1-555-010-1000",
        nin="11223344556",
        bvn="66554433221",
        pin="1234",
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


def test_duplicate_transfer_request_is_processed_once():
    admin_response = client.post(
        "/auth/login",
        json={"email": "komeisioro+admin@gmail.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]
    recipient = main.get_user_by_email("komeisioro+demo@gmail.com")
    before = main.get_wallet_by_account(recipient["account_number"])["wallet_balance"]
    transfer_payload = {
        "from_account": "SK-ADMIN-ALIAS",
        "to_account": recipient["account_number"],
        "amount": 1.0,
        "description": "Idempotency test",
        "pin": "1234",
        "idempotency_key": f"test-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
    }
    headers = {"Authorization": f"Bearer {admin_token}"}

    first_response = client.post("/transfer", json=transfer_payload, headers=headers)
    second_response = client.post("/transfer", json=transfer_payload, headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["receipt_id"] == second_response.json()["receipt_id"]
    after = main.get_wallet_by_account(recipient["account_number"])["wallet_balance"]
    assert after - before == 1.0

"""
def test_admin_can_delete_a_user():
    admin_response = client.post(
        "/auth/login",
        json={"email": "komeisioro+admin@gmail.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    customer_response = register_verified_user(
        name="Delete Me",
        email=f"delete{timestamp}@example.com",
        password="Strongpass!123",
        phone="+1-555-010-8888",
        nin="12341234123",
        bvn="32143214321",
        pin="1234",
    )
    user_email = customer_response.json()["user"]["email"]

    with main.get_connection() as conn:
        user = conn.execute("SELECT id, account_number FROM users WHERE email = ?", (user_email,)).fetchone()
        assert user is not None
        user_id = user["id"]

    delete_response = client.delete(
        f"/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "User removed successfully"

    with main.get_connection() as conn:
        deleted_user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        deleted_wallet = conn.execute("SELECT wallet_id FROM wallets WHERE user_id = ?", (user_id,)).fetchone()

    assert deleted_user is None
    assert deleted_wallet is None
"""

def test_cannot_transfer_to_own_account_number():
    response = client.post(
        "/auth/login",
        json={"email": "demo@sirkome.com", "password": "demo1234"},
    )
    token = response.json()["token"]
    user = main.get_user_by_email("demo@sirkome.com")

    transfer_response = client.post(
        "/transfer",
        json={
            "from_account": user["account_number"],
            "to_account": user["account_number"],
            "amount": 10.0,
            "description": "Self transfer",
            "pin": "1234",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert transfer_response.status_code == 400
    assert "your own account" in transfer_response.json()["detail"].lower()


def test_account_numbers_are_unique_when_registering():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    first_account = main.generate_account_number()
    second_account = main.generate_account_number()

    assert first_account != second_account

    response = register_verified_user(
        name="Unique Number User",
        email=f"unique{timestamp}@example.com",
        password="Strongpass!123",
        phone="+1-555-010-2001",
        nin="12345678904",
        bvn="10987654324",
        pin="1234",
    )

    assert response.status_code == 200
    assert response.json()["user"]["account_number"].startswith("SK-")
    assert response.json()["user"]["account_number"] not in {first_account, second_account}
