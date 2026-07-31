"""Idempotent seeding script that uses functions from backend.main
to create the admin and demo users with known credentials.

Run with:
    python backend/seed_now.py
"""
import runpy


# Execute backend/main.py and get its globals so we can call helper functions
ns = runpy.run_path("backend/main.py")


def get(name):
    return ns.get(name)


def ensure_user(account_number: str, name: str, email: str, password: str, phone: str, nin: str, bvn: str, pin: str, is_admin: int, balance: float):
    existing = get("get_user_by_account")(account_number)
    if existing:
        print(f"User already exists: {existing['account_number']} - {existing['email']}")
        return existing

    user = get("create_user_record")(name, email, password, phone, nin, bvn, pin, is_admin=is_admin, balance=balance, account_number=account_number)
    print(f"Created user: {user['account_number']} - {user['email']}")
    return user


def main_seed():
    admin = ensure_user(
        account_number="SK-ADMIN",
        name="Admin User",
        email="komeisioro+admin@gmail.com",
        password="admin1234",
        phone="+1-555-010-0001",
        nin="11111111111",
        bvn="22222222222",
        pin="1234",
        is_admin=1,
        balance=50000.0,
    )

    demo = ensure_user(
        account_number="SK-4821",
        name="Kome Isioro",
        email="komeisioro+demo@gmail.com",
        password="demo1234",
        phone="+1 (555) 010-4821",
        nin="33333333333",
        bvn="44444444444",
        pin="1234",
        is_admin=0,
        balance=24580.0,
    )

    # Print summary
    for acct in ("SK-ADMIN", "SK-4821"):
        u = get("get_user_by_account")(acct)
        if u:
            print(f"- {acct}: {u['name']} {u['email']} balance={u['balance']} is_admin={u['is_admin']}")
        else:
            print(f"- {acct}: NOT FOUND")


if __name__ == "__main__":
    main_seed()
