import random
import string
from datetime import datetime
import uuid

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


def unique_registration_data(label):
    for _ in range(200):
        numeric_suffix = str(uuid.uuid4().int % 100000000).zfill(8)
        phone = f"080{numeric_suffix}"
        nin = str(uuid.uuid4().int % 100000000000).zfill(11)
        bvn = str(uuid.uuid4().int % 100000000000).zfill(11)
        email = f"{label}-{uuid.uuid4().hex}@example.com"
        with main.get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE LOWER(email) = ? OR phone = ? OR nin = ? OR bvn = ?",
                (email.lower(), phone, nin, bvn),
            ).fetchone()
        if not existing:
            return {"email": email, "phone": phone, "nin": nin, "bvn": bvn}
    raise RuntimeError(f"Unable to generate unique registration data for label '{label}'")


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


def test_staff_login_returns_staff_role_and_permissions():
    response = client.post(
        "/staff/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["user_type"] == "STAFF"
    assert data["user"]["role"] == "SUPER_ADMIN"
    assert "manage_staff" in data["user"]["permissions"]

    context_response = client.get(
        "/staff/me",
        headers={"Authorization": f"Bearer {data['token']}"},
    )
    assert context_response.status_code == 200
    assert context_response.json()["role"] == "SUPER_ADMIN"


def test_customer_cannot_authenticate_as_staff_or_access_staff_context():
    staff_login_response = client.post(
        "/staff/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "demo1234"},
    )
    assert staff_login_response.status_code == 403

    customer_login_response = client.post(
        "/auth/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "demo1234"},
    )
    customer_token = customer_login_response.json()["token"]

    context_response = client.get(
        "/staff/me",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert context_response.status_code == 403

    admin_users_response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert admin_users_response.status_code == 403


def test_admin_seed_account_has_funding_for_transfers():
    admin = main.get_user_by_email("admin@sirkome.com")
    assert admin is not None
    wallet = main.get_wallet_by_account(admin["account_number"])
    assert wallet is not None
    assert float(wallet["wallet_balance"]) >= 250.0


def test_login_failure():
    response = client.post(
        "/auth/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_register_rejects_weak_passwords():
    registration = unique_registration_data("weakpass")
    response = client.post(
        "/auth/register",
        json={
            "name": "Weak Password User",
            **registration,
            "password": "weakpass",
            "pin": "1234",
        },
    )

    assert response.status_code == 400
    assert "at least 8 characters" in response.json()["detail"].lower()


def test_register_does_not_return_access_token():
    registration = unique_registration_data("notoken")
    response = register_verified_user(
        name="No Token User",
        **registration,
        password="Strongpass!123",
        pin="1234",
    )

    assert response.status_code == 200
    assert "token" not in response.json()
    assert "user" in response.json()


def test_email_verification_is_required_before_registration():
    registration = unique_registration_data("verify")
    email = registration["email"]
    setup_response = client.post("/auth/send-verification", json={"email": email})
    assert setup_response.status_code == 200

    raw_code = main.issue_verification_code(email)
    verify_response = client.post("/auth/verify-email", json={"email": email, "code": raw_code})
    assert verify_response.status_code == 200

    response = client.post(
        "/auth/register",
        json={
            "name": "Verified User",
            **registration,
            "password": "Strongpass!123",
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

    registration = unique_registration_data("freeze")
    customer_response = register_verified_user(
        name="Freeze Me",
        **registration,
        password="Strongpass!123",
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
    registration = unique_registration_data("newcustomer")
    response = register_verified_user(
        name="New Customer",
        **registration,
        password="Strongpass!123",
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


def test_staff_customer_management_endpoints_work_and_mask_sensitive_fields():
    admin_response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]
    unique_suffix = "".join(random.choice(string.ascii_uppercase) for _ in range(6))
    customer_name = f"Customer Management User {unique_suffix}"

    registration = unique_registration_data("custmgmt")
    customer_response = register_verified_user(
        name=customer_name,
        **registration,
        password="Strongpass!123",
        pin="1234",
    )
    customer_data = customer_response.json()["user"]
    customer_id = customer_data["user_id"]

    list_response = client.get(
        "/customers",
        params={"query": customer_name, "page": 1, "per_page": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["items"]
    assert any(item["user_id"] == customer_id for item in list_response.json()["items"])

    detail_response = client.get(
        f"/customers/{customer_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["user_id"] == customer_id
    assert "password" not in payload
    assert "pin_hash" not in payload
    assert "token" not in payload
    assert "nin" not in payload
    assert "bvn" not in payload

    patch_response = client.patch(
        f"/customers/{customer_id}",
        json={"phone": "+234-802-000-1111", "address": "No. 6 Fintech Street"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["phone"] == "08020001111"
    assert patch_response.json()["address"] == "No. 6 Fintech Street"

    freeze_response = client.patch(
        f"/customers/{customer_id}/status",
        json={"is_frozen": True, "reason": "Review required"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert freeze_response.status_code == 200
    assert freeze_response.json()["status"] == "FROZEN"

    unfreeze_response = client.patch(
        f"/customers/{customer_id}/status",
        json={"is_frozen": False, "reason": ""},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert unfreeze_response.status_code == 200
    assert unfreeze_response.json()["status"] == "ACTIVE"


def test_customer_management_respects_branch_scope_and_prevents_balance_tampering():
    admin_response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]
    branch_suffix = "".join(random.choice(string.ascii_uppercase) for _ in range(6))
    customer_name = f"Branch Scoped Customer {branch_suffix}"

    branch_response = client.post(
        "/branches",
        json={
            "branch_code": f"KTM-{branch_suffix}",
            "name": "Ketu Main",
            "address": "28 Ikorodu Road",
            "city": "Lagos",
            "state": "Lagos",
            "phone": "+2347000000001",
            "email": f"ketu-{branch_suffix.lower()}@example.com",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert branch_response.status_code == 200
    branch_id = branch_response.json()["id"]

    registration = unique_registration_data("branchscope")
    customer_response = register_verified_user(
        name=customer_name,
        **registration,
        password="Strongpass!123",
        pin="1234",
    )
    customer_id = customer_response.json()["user"]["user_id"]

    assign_response = client.patch(
        f"/customers/{customer_id}/branch",
        json={"branch_id": branch_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["branch"]["id"] == branch_id

    filtered_response = client.get(
        "/customers",
        params={"branch_id": branch_id, "status": "active"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert filtered_response.status_code == 200
    assert any(item["user_id"] == customer_id for item in filtered_response.json()["items"])

    tamper_response = client.patch(
        f"/customers/{customer_id}",
        json={"balance": 999999.99},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert tamper_response.status_code == 422

    customer_wallet = main.get_wallet_by_account(customer_response.json()["user"]["account_number"])
    assert float(customer_wallet["wallet_balance"]) >= 0.0


def test_customer_endpoints_require_staff_access_and_branch_scope():
    customer_login = client.post(
        "/auth/login",
        json={"email": "komeisioro+demo@gmail.com", "password": "demo1234"},
    )
    customer_token = customer_login.json()["token"]

    list_response = client.get(
        "/customers",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert list_response.status_code == 403

    detail_response = client.get(
        "/customers/1",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert detail_response.status_code == 403


def test_customer_search_and_status_filters_work():
    admin_response = client.post(
        "/auth/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]
    unique_suffix = "".join(random.choice(string.ascii_uppercase) for _ in range(4))
    unique_name = f"Search Filter Customer {unique_suffix}"

    registration = unique_registration_data("searchfilter")
    customer_response = register_verified_user(
        name=unique_name,
        **registration,
        password="Strongpass!123",
        pin="1234",
    )
    customer_id = customer_response.json()["user"]["user_id"]

    client.patch(
        f"/customers/{customer_id}/status",
        json={"is_frozen": True, "reason": "Compliance check"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    search_response = client.get(
        "/customers",
        params={"query": "searchfilter", "status": "frozen"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert search_response.status_code == 200
    assert any(item["user_id"] == customer_id for item in search_response.json()["items"])


def test_transfer_moves_funds_between_accounts():
    admin_response = client.post(
        "/auth/login",
        json={"email": "komeisioro+admin@gmail.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]

    registration = unique_registration_data("transfer")
    customer_response = register_verified_user(
        name="Transfer Target",
        **registration,
        password="Strongpass!123",
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
    first_account = main.generate_account_number()
    second_account = main.generate_account_number()

    assert first_account != second_account

    response = register_verified_user(
        name="Unique Number User",
        **unique_registration_data("unique"),
        password="Strongpass!123",
        pin="1234",
    )

    assert response.status_code == 200
    assert response.json()["user"]["account_number"].startswith("SK-")
    assert response.json()["user"]["account_number"] not in {first_account, second_account}


def test_super_admin_can_manage_branches_and_staff_scope():
    admin_response = client.post(
        "/staff/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_token = admin_response.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    branch_suffix = uuid.uuid4().hex[:10].upper()

    branch_response = client.post(
        "/branches",
        json={
            "branch_code": f"TST-{branch_suffix}",
            "name": "Test Central Branch",
            "address": "1 Test Street",
            "city": "Lagos",
            "state": "Lagos",
            "phone": "080" + str(uuid.uuid4().int % 100000000).zfill(8),
            "email": f"branch-{branch_suffix.lower()}@example.com",
        },
        headers=admin_headers,
    )
    assert branch_response.status_code == 200
    branch = branch_response.json()
    assert branch["branch_code"] == f"TST-{branch_suffix}"
    assert branch["is_active"] is True

    duplicate_response = client.post(
        "/branches",
        json={
            "branch_code": branch["branch_code"],
            "name": "Duplicate Branch",
            "address": "2 Test Street",
            "city": "Lagos",
            "state": "Lagos",
            "phone": "080" + str(uuid.uuid4().int % 100000000).zfill(8),
        },
        headers=admin_headers,
    )
    assert duplicate_response.status_code == 400

    staff_data = unique_registration_data("branch-manager")
    staff_response = client.post(
        "/staff",
        json={
            "name": "Branch Manager",
            **staff_data,
            "password": "Strongpass!123",
            "pin": "1234",
            "role": "BRANCH_MANAGER",
            "branch_id": branch["id"],
        },
        headers=admin_headers,
    )
    assert staff_response.status_code == 200
    staff = staff_response.json()
    assert staff["role"] == "BRANCH_MANAGER"
    assert staff["branch"]["id"] == branch["id"]
    assert not {"password", "password_hash", "pin", "pin_hash", "token", "nin", "bvn"}.intersection(staff)

    staff_login = client.post(
        "/staff/login",
        json={"email": staff_data["email"], "password": "Strongpass!123"},
    )
    assert staff_login.status_code == 200
    staff_headers = {"Authorization": f"Bearer {staff_login.json()['token']}"}
    scoped_branches = client.get("/branches", headers=staff_headers)
    assert scoped_branches.status_code == 200
    assert [item["id"] for item in scoped_branches.json()] == [branch["id"]]

    scoped_staff = client.get("/staff", headers=staff_headers)
    assert scoped_staff.status_code == 200
    assert any(item["id"] == staff["id"] for item in scoped_staff.json())

    deactivate_response = client.patch(
        f"/staff/{staff['id']}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert deactivate_response.status_code == 200
    inactive_login = client.post(
        "/staff/login",
        json={"email": staff_data["email"], "password": "Strongpass!123"},
    )
    assert inactive_login.status_code == 403

    reactivate_response = client.patch(
        f"/staff/{staff['id']}/status",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert reactivate_response.status_code == 200


def test_customer_cannot_manage_branches_or_staff():
    login_response = client.post(
        "/auth/login",
        json={"email": "demo@sirkome.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['token']}"}
    assert client.get("/branches", headers=headers).status_code == 403
    assert client.get("/staff", headers=headers).status_code == 403
    assert client.post(
        "/staff",
        json={
            "name": "Unauthorized Staff",
            **unique_registration_data("unauthorized"),
            "password": "Strongpass!123",
            "pin": "1234",
            "role": "TELLER",
        },
        headers=headers,
    ).status_code == 403


def test_teller_deposit_withdrawal_scope_and_idempotency():
    admin_response = client.post(
        "/staff/login",
        json={"email": "admin@sirkome.com", "password": "admin1234"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_response.json()['token']}"}
    suffix = uuid.uuid4().hex[:10].upper()
    branch_response = client.post(
        "/branches",
        json={
            "branch_code": f"TEL-{suffix}",
            "name": "Teller Test Branch",
            "address": "3 Teller Street",
            "city": "Lagos",
            "state": "Lagos",
            "phone": "080" + str(uuid.uuid4().int % 100000000).zfill(8),
        },
        headers=admin_headers,
    )
    assert branch_response.status_code == 200
    branch_id = branch_response.json()["id"]

    teller_data = unique_registration_data("teller")
    teller_response = client.post(
        "/staff",
        json={
            "name": "Test Teller",
            **teller_data,
            "password": "Strongpass!123",
            "pin": "1234",
            "role": "TELLER",
            "branch_id": branch_id,
        },
        headers=admin_headers,
    )
    assert teller_response.status_code == 200

    customer_data = unique_registration_data("teller-customer")
    customer_response = register_verified_user(
        name="Teller Customer",
        **customer_data,
        password="Strongpass!123",
        pin="1234",
    )
    customer_account = customer_response.json()["user"]["account_number"]
    with main.get_connection() as conn:
        conn.execute("UPDATE users SET branch_id = ? WHERE account_number = ?", (branch_id, customer_account))
        conn.commit()

    teller_login = client.post(
        "/staff/login",
        json={"email": teller_data["email"], "password": "Strongpass!123"},
    )
    assert teller_login.status_code == 200
    teller_headers = {"Authorization": f"Bearer {teller_login.json()['token']}"}

    lookup = client.get("/teller/customers", params={"query": customer_account}, headers=teller_headers)
    assert lookup.status_code == 200
    assert lookup.json()[0]["account_number"] == customer_account

    deposit_payload = {
        "account_number": customer_account,
        "amount": "100.00",
        "description": "Initial teller deposit",
        "idempotency_key": f"deposit-{uuid.uuid4().hex}",
    }
    deposit = client.post("/teller/deposits", json=deposit_payload, headers=teller_headers)
    assert deposit.status_code == 200
    deposit_data = deposit.json()
    assert deposit_data["type"] == "DEPOSIT"
    assert deposit_data["status"] == "COMPLETED"
    assert deposit_data["transaction_reference"].startswith("TLL-")

    duplicate_deposit = client.post("/teller/deposits", json=deposit_payload, headers=teller_headers)
    assert duplicate_deposit.status_code == 200
    assert duplicate_deposit.json()["transaction_reference"] == deposit_data["transaction_reference"]

    withdrawal = client.post(
        "/teller/withdrawals",
        json={"account_number": customer_account, "amount": "40.00", "description": "Cash withdrawal", "idempotency_key": f"withdrawal-{uuid.uuid4().hex}"},
        headers=teller_headers,
    )
    assert withdrawal.status_code == 200
    assert withdrawal.json()["type"] == "WITHDRAWAL"

    insufficient = client.post(
        "/teller/withdrawals",
        json={"account_number": customer_account, "amount": "1000.00"},
        headers=teller_headers,
    )
    assert insufficient.status_code == 400

    history = client.get("/transactions", params={"page": 1, "per_page": 20}, headers={"Authorization": f"Bearer {client.post('/auth/login', json={'email': customer_data['email'], 'password': 'Strongpass!123'}).json()['token']}"})
    assert history.status_code == 200
    history_items = history.json()["items"]
    assert any(item["transaction_reference"] == deposit_data["transaction_reference"] for item in history_items)


def test_customer_cannot_use_teller_operations():
    login_response = client.post(
        "/auth/login",
        json={"email": "demo@sirkome.com", "password": "demo1234"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['token']}"}
    payload = {"account_number": "SK-4821", "amount": "1.00"}
    assert client.get("/teller/customers", params={"query": "SK-4821"}, headers=headers).status_code == 403
    assert client.post("/teller/deposits", json=payload, headers=headers).status_code == 403
    assert client.post("/teller/withdrawals", json=payload, headers=headers).status_code == 403
