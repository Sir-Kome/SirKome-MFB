import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage
from collections import defaultdict

from runtime_database import PostgresConnection

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)

DB_PATH = os.path.join(os.path.dirname(__file__), "sirkome_bank.db")
SECRET_KEY = os.getenv("SIRKOME_SECRET_KEY", "dev-secret-change-me")
DEFAULT_ACCESS_TOKEN_TTL_SECONDS = 30 * 60
DEFAULT_CURRENCY = "NGN"
VERIFICATION_CODE_TTL_SECONDS = 15 * 60
VERIFICATION_CACHE: dict[str, dict[str, object]] = {}
LAST_EMAIL_ERROR = ""

STAFF_ROLES = frozenset({
    "SUPER_ADMIN",
    "ADMIN",
    "BRANCH_MANAGER",
    "TELLER",
    "ACCOUNT_OFFICER",
    "MARKETER",
})
ROLE_PERMISSIONS = {
    "SUPER_ADMIN": frozenset({
        "lookup_customers",
        "view_staff",
        "view_branches",
        "view_all_customers",
        "manage_customers",
        "freeze_accounts",
        "view_transactions",
        "manage_operational_banking",
        "view_reports",
        "manage_staff",
        "manage_roles",
        "manage_branches",
        "system_configuration",
    }),
    "ADMIN": frozenset({
        "lookup_customers",
        "view_staff",
        "view_branches",
        "view_all_customers",
        "manage_customers",
        "freeze_accounts",
        "view_transactions",
        "manage_operational_banking",
        "view_reports",
        "manage_staff",
        "manage_branches",
    }),
    "BRANCH_MANAGER": frozenset({
        "view_staff",
        "view_assigned_branch",
        "view_teller_transactions",
        "view_branch_customers",
        "manage_branch_operations",
        "view_branch_transactions",
        "approve_branch_operations",
        "view_branch_reports",
        "manage_branch_staff",
    }),
    "TELLER": frozenset({
        "lookup_customers",
        "create_deposits",
        "create_withdrawals",
        "view_permitted_customer_accounts",
        "process_deposits",
        "process_withdrawals",
        "view_teller_transactions",
    }),
    "ACCOUNT_OFFICER": frozenset({
        "manage_permitted_customer_accounts",
        "view_assigned_customers",
        "view_account_information",
    }),
    "MARKETER": frozenset({
        "view_permitted_customer_profiles",
        "access_marketing_functions",
    }),
}
ROLE_MANAGEABLE_ROLES = {
    "SUPER_ADMIN": STAFF_ROLES,
    "ADMIN": frozenset(STAFF_ROLES - {"SUPER_ADMIN"}),
    "BRANCH_MANAGER": frozenset({"TELLER", "ACCOUNT_OFFICER", "MARKETER"}),
}


def load_env_file():
    env_path = Path(os.path.dirname(__file__)) / ".env"
    if not env_path.exists():
        return

    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                os.environ[k] = v


load_env_file()


def get_access_token_ttl_seconds() -> int:
    configured_ttl = int(os.getenv("SIRKOME_ACCESS_TOKEN_TTL_SECONDS", str(DEFAULT_ACCESS_TOKEN_TTL_SECONDS)))
    if configured_ttl < 5 * 60:
        return 5 * 60
    if configured_ttl > 60 * 60:
        return 60 * 60
    return configured_ttl


class LoginRequest(BaseModel):
    email: str
    password: str


class StaffLoginRequest(BaseModel):
    email: str
    password: str


class StaffCreateRequest(BaseModel):
    name: str
    email: str
    phone: str
    password: str
    pin: str
    role: str
    branch_id: int | None = None


class StaffUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: str | None = None
    branch_id: int | None = None


class StaffStatusRequest(BaseModel):
    is_active: bool


class BranchCreateRequest(BaseModel):
    branch_code: str
    name: str
    address: str
    city: str
    state: str
    phone: str
    email: str | None = None


class BranchUpdateRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None


class BranchStatusRequest(BaseModel):
    is_active: bool


class RegisterRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    name: str | None = None
    email: str
    password: str
    phone: str
    date_of_birth: str = ""
    gender: str = ""
    nin: str | None = None
    bvn: str | None = None
    identity_type: str | None = None
    pin: str | None = None


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: float
    description: str = "Transfer"
    pin: str | None = None
    idempotency_key: str | None = None


class FreezeUserRequest(BaseModel):
    is_frozen: bool
    reason: str | None = None
    model_config = {"extra": "forbid"}


class CustomerUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    model_config = {"extra": "forbid"}


class CustomerStatusRequest(BaseModel):
    is_frozen: bool
    reason: str | None = None
    model_config = {"extra": "forbid"}


class CustomerBranchRequest(BaseModel):
    branch_id: int
    model_config = {"extra": "forbid"}


class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    phone: str
    date_of_birth: str
    gender: str
    account_number: str
    balance: float
    currency: str = DEFAULT_CURRENCY
    is_admin: bool = False
    user_type: str = "CUSTOMER"
    role: str | None = None
    permissions: list[str] = []
    is_frozen: bool = False
    freeze_reason: str | None = None
    tier: str = "Tier 1"
    daily_transfer_limit: float = 50000.0
    address: str | None = None
    proof_of_address_date: str | None = None


class AccountResponse(BaseModel):
    account_number: str
    balance: float
    currency: str = DEFAULT_CURRENCY
    type: str


class TransactionResponse(BaseModel):
    type: str
    amount: float
    description: str
    date: str
    transaction_reference: str | None = None
    status: str | None = None


class TransactionPageResponse(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    items: list[TransactionResponse]


class LoginResponse(BaseModel):
    token: str
    user: UserProfile


class RegisterResponse(BaseModel):
    user: UserProfile


class TransferResponse(BaseModel):
    status: str
    message: str
    receipt_id: str | None = None
    from_account: str | None = None
    to_account: str | None = None
    amount: float | None = None
    description: str | None = None
    date: str | None = None


class TellerOperationRequest(BaseModel):
    account_number: str
    amount: Decimal
    description: str = ""
    idempotency_key: str | None = None


class TellerCustomerResponse(BaseModel):
    user_id: str
    name: str
    account_number: str
    wallet_id: str | None = None
    balance: float
    currency: str
    is_frozen: bool
    branch_id: int | None = None


class TellerTransactionResponse(BaseModel):
    transaction_reference: str | None = None
    type: str
    amount: float
    status: str | None = None
    account_number: str
    description: str
    date: str
    branch_id: int | None = None


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None


class ProfileUpgradeRequest(BaseModel):
    nin: str | None = None
    bvn: str | None = None
    address: str | None = None
    proof_of_address_filename: str | None = None
    proof_of_address_data: str | None = None
    proof_of_address_date: str | None = None


class EmailVerificationRequest(BaseModel):
    email: str


class EmailCodeVerificationRequest(BaseModel):
    email: str
    code: str


class SavedAccountRequest(BaseModel):
    account_number: str
    account_name: str | None = None


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: str


class NotificationPageResponse(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    unread: int
    items: list[NotificationResponse]


def get_connection():
    if os.getenv("DATABASE_URL"):
        return PostgresConnection()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if os.getenv("DATABASE_URL"):
        return
    with get_connection() as conn:
        users_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if users_columns and ("user_id" in users_columns or "wallet_id" in users_columns or "pin_hash" not in users_columns):
            conn.execute("DROP TABLE IF EXISTS transactions")
            conn.execute("DROP TABLE IF EXISTS wallets")
            conn.execute("DROP TABLE IF EXISTS users")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT NOT NULL,
                date_of_birth TEXT NOT NULL DEFAULT '',
                gender TEXT NOT NULL DEFAULT '',
                account_number TEXT UNIQUE NOT NULL,
                wallet_id TEXT,
                currency TEXT NOT NULL DEFAULT 'NGN',
                is_admin INTEGER NOT NULL DEFAULT 0,
                token TEXT,
                nin TEXT,
                bvn TEXT,
                pin_hash TEXT,
                is_frozen INTEGER NOT NULL DEFAULT 0,
                freeze_reason TEXT NOT NULL DEFAULT '',
                verification_tier INTEGER NOT NULL DEFAULT 1,
                address TEXT,
                proof_of_address_filename TEXT,
                proof_of_address_data TEXT,
                proof_of_address_date TEXT,
                branch_id INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                related_account TEXT,
                transaction_reference TEXT,
                status TEXT,
                idempotency_key TEXT,
                staff_user_id INTEGER,
                branch_id INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallets (
                wallet_id TEXT PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                wallet_balance REAL NOT NULL DEFAULT 0.0,
                currency TEXT NOT NULL DEFAULT 'NGN',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS branches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                staff_role TEXT NOT NULL,
                branch_code TEXT,
                branch_id INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transfer_requests (
                idempotency_key TEXT PRIMARY KEY,
                receipt_id TEXT UNIQUE NOT NULL,
                from_account TEXT NOT NULL,
                to_account TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_number TEXT NOT NULL,
                account_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, account_number)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS ix_branches_name ON branches(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_branches_is_active ON branches(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_staff_role ON staff_profiles(staff_role)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_branch_code ON staff_profiles(branch_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_branch_id ON staff_profiles(branch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_is_active ON staff_profiles(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_users_branch_id ON users(branch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_transactions_staff_user_id ON transactions(staff_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_transactions_branch_id ON transactions(branch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_transactions_status ON transactions(status)")
        conn.commit()


def ensure_sqlite_schema_compatibility():
    if os.getenv("DATABASE_URL"):
        return
    with get_connection() as conn:
        user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "branch_id" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN branch_id INTEGER")

        transaction_columns = {row["name"] for row in conn.execute("PRAGMA table_info(transactions)").fetchall()}
        for column_name, column_sql in {
            "transaction_reference": "TEXT",
            "status": "TEXT",
            "idempotency_key": "TEXT",
            "staff_user_id": "INTEGER",
            "branch_id": "INTEGER",
        }.items():
            if column_name not in transaction_columns:
                conn.execute(f"ALTER TABLE transactions ADD COLUMN {column_name} {column_sql}")

        branch_columns = {row["name"] for row in conn.execute("PRAGMA table_info(branches)").fetchall()}
        if not branch_columns:
            conn.execute(
                """
                CREATE TABLE branches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch_code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            for column_name, column_sql in {
                "branch_code": "TEXT",
                "name": "TEXT",
                "address": "TEXT",
                "city": "TEXT",
                "state": "TEXT",
                "phone": "TEXT",
                "email": "TEXT",
                "is_active": "INTEGER DEFAULT 1",
                "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            }.items():
                if column_name not in branch_columns:
                    conn.execute(f"ALTER TABLE branches ADD COLUMN {column_name} {column_sql}")

        profile_columns = {row["name"] for row in conn.execute("PRAGMA table_info(staff_profiles)").fetchall()}
        if not profile_columns:
            conn.execute(
                """
                CREATE TABLE staff_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    staff_role TEXT NOT NULL,
                    branch_code TEXT,
                    branch_id INTEGER,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
                )
                """
            )
        else:
            for column_name, column_sql in {
                "user_id": "INTEGER",
                "staff_role": "TEXT",
                "branch_code": "TEXT",
                "branch_id": "INTEGER",
                "is_active": "INTEGER DEFAULT 1",
                "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            }.items():
                if column_name not in profile_columns:
                    conn.execute(f"ALTER TABLE staff_profiles ADD COLUMN {column_name} {column_sql}")

        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_branches_branch_code ON branches(branch_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_staff_role ON staff_profiles(staff_role)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_branch_code ON staff_profiles(branch_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_branch_id ON staff_profiles(branch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_staff_profiles_is_active ON staff_profiles(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_branches_name ON branches(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_branches_is_active ON branches(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_users_branch_id ON users(branch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_transactions_staff_user_id ON transactions(staff_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_transactions_branch_id ON transactions(branch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_transactions_status ON transactions(status)")
        conn.commit()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def create_access_token(user_id: int, expires_in_seconds: int | None = None) -> str:
    now = int(time.time())
    ttl_seconds = expires_in_seconds if expires_in_seconds is not None else get_access_token_ttl_seconds()
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def decode_access_token(token: str) -> dict | None:
    try:
        encoded_payload, signature = token.rsplit(".", 1)
    except ValueError:
        return None

    expected_signature = hmac.new(SECRET_KEY.encode("utf-8"), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None

    padding = "=" * (-len(encoded_payload) % 4)
    try:
        decoded_payload = base64.urlsafe_b64decode(encoded_payload + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None

    try:
        payload = json.loads(decoded_payload)
    except json.JSONDecodeError:
        return None

    if payload.get("exp", 0) < int(time.time()):
        return None

    return payload


def create_or_update_wallet(conn: sqlite3.Connection, user_ref: int | str, account_number: str, balance: float = 0.0, wallet_id: str | None = None) -> str:
    wallet_id = wallet_id or str(user_ref)
    existing_wallet = conn.execute(
        "SELECT wallet_id FROM wallets WHERE user_id = ? OR wallet_id = ? OR account_number = ?",
        (wallet_id, wallet_id, account_number),
    ).fetchone()

    if existing_wallet:
        conn.execute(
            "UPDATE wallets SET wallet_id = ?, user_id = ?, account_number = ?, wallet_balance = ?, currency = ?, status = 'active' WHERE wallet_id = ?",
            (wallet_id, wallet_id, account_number, float(balance), DEFAULT_CURRENCY, existing_wallet["wallet_id"]),
        )
        return wallet_id

    conn.execute(
        "INSERT INTO wallets (wallet_id, user_id, account_number, wallet_balance, currency, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (wallet_id, wallet_id, account_number, float(balance), DEFAULT_CURRENCY, "active", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    return wallet_id


def ensure_user_columns():
    if os.getenv("DATABASE_URL"):
        return
    with get_connection() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "nin" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN nin TEXT")
        if "bvn" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN bvn TEXT")
        if "pin_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN pin_hash TEXT")
        if "user_id" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN user_id TEXT")
        if "wallet_id" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN wallet_id TEXT")
        if "is_frozen" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN is_frozen INTEGER NOT NULL DEFAULT 0")
        if "freeze_reason" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN freeze_reason TEXT NOT NULL DEFAULT ''")
        if "verification_tier" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN verification_tier INTEGER NOT NULL DEFAULT 1")
        if "address" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN address TEXT")
        if "proof_of_address_filename" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN proof_of_address_filename TEXT")
        if "proof_of_address_data" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN proof_of_address_data TEXT")
        if "proof_of_address_date" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN proof_of_address_date TEXT")
        if "date_of_birth" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN date_of_birth TEXT NOT NULL DEFAULT ''")
        if "gender" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN gender TEXT NOT NULL DEFAULT ''")
        conn.execute("UPDATE users SET verification_tier = 2 WHERE nin IS NOT NULL AND bvn IS NOT NULL AND verification_tier < 2")
        if "balance" in columns:
            rows = conn.execute(
                "SELECT id, user_id, name, email, password, phone, account_number, wallet_id, currency, is_admin, token, nin, bvn, pin_hash FROM users"
            ).fetchall()
            conn.execute(
                """
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    date_of_birth TEXT NOT NULL DEFAULT '',
                    gender TEXT NOT NULL DEFAULT '',
                    account_number TEXT UNIQUE NOT NULL,
                    wallet_id TEXT,
                    currency TEXT NOT NULL DEFAULT 'NGN',
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    token TEXT,
                    nin TEXT,
                    bvn TEXT,
                    pin_hash TEXT
                )
                """
            )
            for row in rows:
                resolved_user_id = row["user_id"] or f"USR-{uuid.uuid4().hex[:12].upper()}"
                resolved_wallet_id = row["wallet_id"] or resolved_user_id
                conn.execute(
                    """
                    INSERT INTO users_new (id, user_id, name, email, password, phone, date_of_birth, gender, account_number, wallet_id, currency, is_admin, token, nin, bvn, pin_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        resolved_user_id,
                        row["name"],
                        row["email"],
                        row["password"],
                        row["phone"],
                        "",
                        "",
                        row["account_number"],
                        resolved_wallet_id,
                        row["currency"],
                        row["is_admin"],
                        row["token"],
                        row["nin"],
                        row["bvn"],
                        row["pin_hash"],
                    ),
                )
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_new RENAME TO users")
            conn.commit()

        conn.execute("UPDATE users SET pin_hash = ? WHERE pin_hash IS NULL", (hash_pin("1234"),))
        conn.execute("UPDATE users SET token = NULL WHERE token IS NOT NULL")

        rows = conn.execute("SELECT id, user_id, account_number FROM users").fetchall()
        for row in rows:
            if not row["id"]:
                continue
            if not row["user_id"]:
                new_uid = f"USR-{uuid.uuid4().hex[:12].upper()}"
                conn.execute("UPDATE users SET user_id = ? WHERE id = ?", (new_uid, row["id"]))

        conn.commit()


def ensure_wallets():
    if os.getenv("DATABASE_URL"):
        return
    with get_connection() as conn:
        users = conn.execute("SELECT id, user_id, account_number FROM users").fetchall()
        for user in users:
            wallet_balance = conn.execute(
                "SELECT wallet_balance FROM wallets WHERE account_number = ?",
                (user["account_number"],),
            ).fetchone()
            create_or_update_wallet(
                conn,
                user["user_id"] or user["id"],
                user["account_number"],
                float(wallet_balance["wallet_balance"] if wallet_balance else 0.0),
                wallet_id=user["user_id"] or f"USR-{uuid.uuid4().hex[:12].upper()}",
            )
        conn.commit()


def validate_identity_number(value: str, field_name: str) -> str:
    if not value or len(value) != 11 or not value.isdigit() or any(char.isspace() for char in value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} must be exactly 11 digits with no spaces")
    return value


def validate_full_name(first_name: str | None, last_name: str | None, middle_name: str | None = None) -> str:
    value_parts = [first_name or "", last_name or ""]
    if middle_name:
        value_parts.append(middle_name)

    combined_name = " ".join(part.strip() for part in value_parts if part and part.strip())
    if not combined_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="First name and last name are required")

    if len(combined_name) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name must be at least 3 characters long")

    if not all(part.isalpha() or (part == "-" or part == "'") for part in combined_name.replace(" ", "")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name must contain only letters, spaces, apostrophes, and hyphens")

    return combined_name


def validate_phone_number(phone: str) -> str:
    digits_only = "".join(char for char in phone if char.isdigit())
    if len(digits_only) == 13 and digits_only.startswith("234"):
        normalized_phone = f"0{digits_only[3:]}"
    elif len(digits_only) == 11 and digits_only.startswith("0"):
        normalized_phone = digits_only
    elif len(digits_only) == 11 and digits_only.startswith("1"):
        normalized_phone = digits_only
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number must be a valid Nigerian mobile number")

    if len(normalized_phone) != 11 or not normalized_phone.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number must be a valid Nigerian mobile number")

    return normalized_phone


def validate_pin(pin: str) -> str:
    if not pin or len(pin) != 4 or not pin.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN must be exactly 4 digits")
    return pin


def generate_account_number() -> str:
    while True:
        suffix = datetime.now().strftime("%H%M%S%f")
        candidate = f"SK-{suffix}"
        with get_connection() as conn:
            existing_user = conn.execute("SELECT id FROM users WHERE account_number = ?", (candidate,)).fetchone()
            if not existing_user:
                return candidate


def resolve_account_number(account_number: str) -> str:
    aliases = {
        "VB-ADMIN": "SK-ADMIN",
    }
    return aliases.get(account_number, account_number)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email_address(email: str) -> str:
    normalized_email = normalize_email(email)
    if not normalized_email or not re.fullmatch(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", normalized_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please enter a valid email address")
    return normalized_email


def validate_date_of_birth(value: str) -> str:
    try:
        parsed_date = datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date of birth must use YYYY-MM-DD") from exc
    if parsed_date.date() > datetime.now().date():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Date of birth cannot be in the future") from None
    return value


def validate_gender(value: str) -> str:
    normalized_gender = value.strip().lower()
    if normalized_gender not in {"male", "female", "other", "prefer_not_to_say"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please select a valid gender")
    return normalized_gender


def validate_password(password: str) -> str:
    if not password or len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and include at least one number and one special character",
        )
    if not any(char.isdigit() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and include at least one number and one special character",
        )
    if not any(not char.isalnum() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and include at least one number and one special character",
        )
    return password


def hash_verification_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def issue_verification_code(email: str) -> str:
    normalized_email = normalize_email(email)
    code = str(uuid.uuid4().int % 1000000).zfill(6)
    expires_at = int(time.time()) + VERIFICATION_CODE_TTL_SECONDS
    VERIFICATION_CACHE[normalized_email] = {
        "code_hash": hash_verification_code(code),
        "expires_at": expires_at,
        "used": False,
    }
    return code


def verify_email_code(email: str, code: str) -> bool:
    normalized_email = normalize_email(email)
    cached_entry = VERIFICATION_CACHE.get(normalized_email)
    if not cached_entry:
        return False
    if bool(cached_entry.get("used", False)):
        return False
    if int(cached_entry.get("expires_at", 0)) < int(time.time()):
        VERIFICATION_CACHE.pop(normalized_email, None)
        return False
    if cached_entry.get("code_hash") != hash_verification_code(code):
        return False
    cached_entry["used"] = True
    return True


def clear_verification_code(email: str) -> None:
    VERIFICATION_CACHE.pop(normalize_email(email), None)


def get_user_by_email(email: str):
    normalized_email = normalize_email(email)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (normalized_email,)).fetchone()


def get_existing_registration_field(email: str, phone: str, nin: str, bvn: str):
    with get_connection() as conn:
        users = conn.execute("SELECT email, phone, nin, bvn FROM users").fetchall()

    normalized_email = normalize_email(email)
    for user in users:
        stored_phone = "".join(char for char in (user["phone"] or "") if char.isdigit())
        matched_field = None
        if normalize_email(user["email"]) == normalized_email:
            matched_field = "email"
        elif stored_phone == phone:
            matched_field = "phone"
        elif nin is not None and user["nin"] == nin:
            matched_field = "NIN"
        elif bvn is not None and user["bvn"] == bvn:
            matched_field = "BVN"

        if matched_field:
            print(f"Duplicate registration detected: {matched_field}")
            return user
    return None


def get_user_by_account(account_number: str):
    normalized_account = resolve_account_number(account_number)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE account_number = ?", (normalized_account,)).fetchone()


def get_user_by_token(token: str):
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_staff_profile_by_user_id(user_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT staff_role, branch_code, branch_id, is_active FROM staff_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()


def get_staff_context(user):
    profile = get_staff_profile_by_user_id(user["id"])
    if profile:
        if not bool(profile["is_active"]):
            return None
        role = profile["staff_role"]
        return {
            "role": role,
            "branch_code": profile["branch_code"],
            "branch_id": profile["branch_id"],
            "permissions": sorted(ROLE_PERMISSIONS.get(role, ())),
        }

    if bool(user["is_admin"]):
        return {
            "role": "SUPER_ADMIN",
            "branch_code": None,
            "branch_id": None,
            "permissions": sorted(ROLE_PERMISSIONS["SUPER_ADMIN"]),
        }

    return None


def get_wallet_by_account(account_number: str):
    normalized_account = resolve_account_number(account_number)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM wallets WHERE account_number = ?", (normalized_account,)).fetchone()


def get_current_user(credentials: HTTPAuthorizationCredentials | None):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    current_user = get_user_by_token(credentials.credentials)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return current_user


def require_staff(credentials: HTTPAuthorizationCredentials | None):
    current_user = get_current_user(credentials)
    if not get_staff_context(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return current_user


def require_role(credentials: HTTPAuthorizationCredentials | None, *roles: str):
    current_user = require_staff(credentials)
    staff_context = get_staff_context(current_user)
    if staff_context["role"] not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient staff role")
    return current_user


def require_permission(credentials: HTTPAuthorizationCredentials | None, permission: str):
    current_user = require_staff(credentials)
    staff_context = get_staff_context(current_user)
    if permission not in staff_context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient staff permission")
    return current_user


def staff_role(user) -> str:
    context = get_staff_context(user)
    return context["role"] if context else ""


def require_staff_management(credentials: HTTPAuthorizationCredentials | None):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "manage_staff" not in context["permissions"] and "manage_branch_staff" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff management access required")
    return current_user


def require_branch_management(credentials: HTTPAuthorizationCredentials | None):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "manage_branches" not in context["permissions"] and "view_assigned_branch" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch management access required")
    return current_user


def normalize_staff_role(value: str) -> str:
    role = (value or "").strip().upper()
    if role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid staff role")
    return role


def validate_staff_role_assignment(current_user, requested_role: str):
    role = normalize_staff_role(requested_role)
    current_role = staff_role(current_user)
    if role not in ROLE_MANAGEABLE_ROLES.get(current_role, frozenset()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not permitted to assign this staff role")
    return role


def get_branch_by_id(branch_id: int):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM branches WHERE id = ?", (branch_id,)).fetchone()


def get_staff_record(staff_identifier: str):
    normalized = staff_identifier.strip()
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT
                u.id AS user_id,
                u.user_id AS public_user_id,
                u.name,
                u.email,
                u.phone,
                sp.id AS staff_profile_id,
                sp.staff_role,
                sp.branch_id,
                sp.is_active,
                sp.created_at,
                sp.updated_at,
                b.branch_code,
                b.name AS branch_name
            FROM users AS u
            JOIN staff_profiles AS sp ON sp.user_id = u.id
            LEFT JOIN branches AS b ON b.id = sp.branch_id
            WHERE u.user_id = ? OR u.email = ? OR CAST(u.id AS TEXT) = ?
            """,
            (normalized, normalize_email(normalized), normalized),
        ).fetchone()


def staff_record_in_scope(current_user, staff_record) -> bool:
    context = get_staff_context(current_user)
    if not context:
        return False
    if context["role"] in {"SUPER_ADMIN", "ADMIN"}:
        return True
    return context["branch_id"] is not None and staff_record["branch_id"] == context["branch_id"]


def can_manage_staff_record(current_user, staff_record) -> bool:
    context = get_staff_context(current_user)
    if not context or not staff_record_in_scope(current_user, staff_record):
        return False
    if staff_record["staff_role"] == "SUPER_ADMIN" and context["role"] != "SUPER_ADMIN":
        return False
    return staff_record["staff_role"] in ROLE_MANAGEABLE_ROLES.get(context["role"], frozenset())


def branch_in_scope(current_user, branch_id: int) -> bool:
    context = get_staff_context(current_user)
    if not context:
        return False
    if context["role"] in {"SUPER_ADMIN", "ADMIN"}:
        return True
    return context["branch_id"] == branch_id


def format_timestamp(value) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else str(value) if value else None


def customer_status_label(user_row) -> str:
    return "FROZEN" if bool(user_row["is_frozen"]) else "ACTIVE"


def customer_accessible_branch(context):
    if context["role"] in {"SUPER_ADMIN", "ADMIN"}:
        return None
    if context["branch_id"] is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch access required")
    return context["branch_id"]


def customer_in_scope(current_user, customer_row) -> bool:
    context = get_staff_context(current_user)
    if not context:
        return False
    if context["role"] in {"SUPER_ADMIN", "ADMIN"}:
        return True
    if context["branch_id"] is None:
        return False
    return customer_row["branch_id"] == context["branch_id"]


def serialize_customer_summary(row):
    branch = None
    if row["branch_id"] is not None:
        branch = {
            "id": row["branch_id"],
            "code": row["branch_code"],
            "name": row["branch_name"],
        }
    wallet = None
    if row["wallet_balance"] is not None:
        wallet = {
            "account_number": row["account_number"],
            "balance": float(row["wallet_balance"] or 0.0),
            "currency": row["currency"],
            "status": row["wallet_status"] or "active",
        }
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "account_number": row["account_number"],
        "status": customer_status_label(row),
        "is_frozen": bool(row["is_frozen"]),
        "freeze_reason": row["freeze_reason"] or None,
        "branch": branch,
        "wallet": wallet,
        "branch_id": row["branch_id"],
    }


def serialize_customer_detail(row):
    summary = serialize_customer_summary(row)
    recent_transactions = []
    if row.get("recent_transactions"):
        recent_transactions = row["recent_transactions"]
    detail = {**summary, "address": row["address"], "date_of_birth": row["date_of_birth"], "gender": row["gender"], "currency": row["currency"], "user_type": "CUSTOMER", "recent_transactions": recent_transactions}
    detail.pop("wallet", None)
    detail["wallet"] = {
        "account_number": row["account_number"],
        "balance": float(row["wallet_balance"] or 0.0),
        "currency": row["currency"],
        "status": row["wallet_status"] or "active",
    } if row["wallet_balance"] is not None else None
    return detail


def serialize_branch(row):
    return {
        "id": row["id"],
        "branch_code": row["branch_code"],
        "name": row["name"],
        "address": row["address"],
        "city": row["city"],
        "state": row["state"],
        "phone": row["phone"],
        "email": row["email"],
        "is_active": bool(row["is_active"]),
        "created_at": format_timestamp(row["created_at"]),
        "updated_at": format_timestamp(row["updated_at"]),
    }


def serialize_staff(row):
    branch = None
    if row["branch_id"] is not None:
        branch = {
            "id": row["branch_id"],
            "code": row["branch_code"],
            "name": row["branch_name"],
        }
    return {
        "id": row["public_user_id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "role": row["staff_role"],
        "branch": branch,
        "is_active": bool(row["is_active"]),
        "created_at": format_timestamp(row["created_at"]),
        "updated_at": format_timestamp(row["updated_at"]),
    }


def teller_scope_clause(context):
    if context["role"] in {"SUPER_ADMIN", "ADMIN"}:
        return "", ()
    if context["branch_id"] is None:
        return " AND u.branch_id IS NULL AND 1 = 0", ()
    return " AND u.branch_id = ?", (context["branch_id"],)


def get_teller_customer(conn, account_number: str, context):
    scope_clause, scope_params = teller_scope_clause(context)
    return conn.execute(
        f"""
        SELECT u.id, u.user_id, u.name, u.account_number, u.wallet_id, u.currency,
               u.is_frozen, u.freeze_reason, u.branch_id,
               w.wallet_balance, w.status AS wallet_status,
               b.is_active AS branch_active
        FROM users AS u
        LEFT JOIN wallets AS w ON w.account_number = u.account_number
        LEFT JOIN branches AS b ON b.id = u.branch_id
        WHERE u.account_number = ?{scope_clause}
        """,
        (resolve_account_number(account_number), *scope_params),
    ).fetchone()


def serialize_teller_customer(row):
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "account_number": row["account_number"],
        "wallet_id": row["wallet_id"],
        "balance": float(row["wallet_balance"] or 0),
        "currency": row["currency"],
        "is_frozen": bool(row["is_frozen"]),
        "branch_id": row["branch_id"],
    }


def serialize_teller_transaction(row):
    return {
        "transaction_reference": row["transaction_reference"],
        "type": row["type"],
        "amount": float(row["amount"]),
        "status": row["status"],
        "account_number": row["account_number"],
        "description": row["description"],
        "date": row["date"],
        "branch_id": row["branch_id"],
    }


def validate_teller_amount(amount: Decimal) -> Decimal:
    try:
        value = Decimal(amount).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be a valid number") from exc
    if value <= Decimal("0.00"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero")
    return value


def require_teller_operation(credentials: HTTPAuthorizationCredentials | None, permission: str):
    current_user = require_permission(credentials, permission)
    if staff_role(current_user) != "TELLER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teller access required")
    return current_user


def process_teller_operation(payload: TellerOperationRequest, current_user, transaction_type: str):
    amount = validate_teller_amount(payload.amount)
    idempotency_key = (payload.idempotency_key or "").strip() or None
    description = (payload.description or "").strip() or transaction_type.title()
    context = get_staff_context(current_user)
    transaction_reference = f"TLL-{uuid.uuid4().hex[:16].upper()}"

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            existing = conn.execute(
                "SELECT * FROM transactions WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                if existing["account_number"] != resolve_account_number(payload.account_number) or Decimal(existing["amount"]) != amount or existing["type"] != transaction_type:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was already used for another transaction")
                return serialize_teller_transaction(existing)

        customer = get_teller_customer(conn, payload.account_number, context)
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer account not found")
        if bool(customer["is_frozen"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Frozen accounts cannot be used for teller operations")
        if customer["wallet_status"] != "active" or customer["branch_active"] is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer account is inactive")

        if transaction_type == "WITHDRAWAL":
            updated_wallet = conn.execute(
                "UPDATE wallets SET wallet_balance = wallet_balance - ? WHERE account_number = ? AND wallet_balance >= ? RETURNING wallet_balance",
                (amount, customer["account_number"], amount),
            ).fetchone()
            if not updated_wallet:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")
        else:
            updated_wallet = conn.execute(
                "UPDATE wallets SET wallet_balance = wallet_balance + ? WHERE account_number = ? RETURNING wallet_balance",
                (amount, customer["account_number"]),
            ).fetchone()

        transaction = conn.execute(
            """
            INSERT INTO transactions
                (account_number, type, amount, description, date, related_account,
                 transaction_reference, status, idempotency_key, staff_user_id, branch_id)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, NULL, ?, 'COMPLETED', ?, ?, ?)
            RETURNING transaction_reference, type, amount, status, account_number,
                      description, date, branch_id
            """,
            (customer["account_number"], transaction_type, amount, description, transaction_reference, idempotency_key, current_user["id"], context["branch_id"]),
        ).fetchone()
        conn.commit()

    return serialize_teller_transaction(transaction)


def require_authenticated_admin(credentials: HTTPAuthorizationCredentials | None):
    current_user = require_permission(credentials, "manage_customers")

    return current_user


def send_email(to_address: str, subject: str, body: str) -> bool:
    global LAST_EMAIL_ERROR
    LAST_EMAIL_ERROR = ""
    load_env_file()

    smtp_host = (os.getenv("SIRKOME_SMTP_HOST") or "").strip()
    smtp_port = int((os.getenv("SIRKOME_SMTP_PORT") or "587").strip())
    smtp_user = (os.getenv("SIRKOME_SMTP_USER") or "").strip()
    smtp_pass = (os.getenv("SIRKOME_SMTP_PASS") or "").replace(" ", "").strip()
    from_address = (os.getenv("SIRKOME_FROM") or smtp_user).strip()

    # Always log the notification for audit/debug
    print({"email_to": to_address, "subject": subject, "body": body})

    if not smtp_host or not smtp_user or not smtp_pass:
        LAST_EMAIL_ERROR = "SMTP host, user, or password is not configured"
        print("SMTP not configured: email notification unavailable.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.set_content(body)

    use_ssl = smtp_port == 465 or os.getenv("SIRKOME_SMTP_SSL", "false").strip().lower() == "true"
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as s:
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
        return True
    except Exception as exc:
        if smtp_port != 587:
            LAST_EMAIL_ERROR = f"{type(exc).__name__}: {exc}"
            print(f"Email send failed ({type(exc).__name__}): {exc}")
            return False

        try:
            with smtplib.SMTP_SSL(smtp_host, 465, timeout=10) as s:
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
            print("Email sent using SMTP SSL fallback on port 465.")
            return True
        except Exception as fallback_exc:
            LAST_EMAIL_ERROR = f"STARTTLS: {type(exc).__name__}: {exc}; SSL fallback: {type(fallback_exc).__name__}: {fallback_exc}"
            print(f"Email send failed ({type(fallback_exc).__name__}): {fallback_exc}")
            return False


def notify_user_by_email(to_address: str, subject: str, body: str) -> bool:
    user = get_user_by_email(to_address)
    if user:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO notifications (user_id, title, message, created_at) VALUES (?, ?, ?, ?)",
                (user["id"], subject, body, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
    sent = send_email(to_address, subject, body)
    if not sent:
        print(f"Notification email could not be delivered to {to_address}.")
    return sent


def create_user_record(name: str, email: str, password: str, phone: str, nin: str | None, bvn: str | None, pin: str, is_admin: int = 0, balance: float = 0.0, account_number: str | None = None, token: str | None = None, is_frozen: int = 0, freeze_reason: str = "", verification_tier: int | None = None, date_of_birth: str = "", gender: str = ""):
    account_number = account_number or generate_account_number()
    resolved_verification_tier = verification_tier if verification_tier is not None else (2 if nin and bvn else 1)
    is_admin_value = bool(is_admin)
    is_frozen_value = bool(is_frozen)
    with get_connection() as conn:
        user_id_val = f"USR-{uuid.uuid4().hex[:12].upper()}"
        insert_sql = """
            INSERT INTO users (user_id, name, email, password, phone, date_of_birth, gender, account_number, currency, is_admin, token, nin, bvn, pin_hash, wallet_id, is_frozen, freeze_reason, verification_tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        if os.getenv("DATABASE_URL"):
            insert_sql += " RETURNING id"
        cursor = conn.execute(
            insert_sql,
            (user_id_val, name, email, hash_password(password), phone, date_of_birth, gender, account_number, DEFAULT_CURRENCY, is_admin_value, None, nin, bvn, hash_pin(pin), user_id_val, is_frozen_value, freeze_reason, resolved_verification_tier),
        )
        conn.commit()
        user_id = cursor.fetchone()[0] if os.getenv("DATABASE_URL") else cursor.lastrowid
        wallet_id = create_or_update_wallet(conn, user_id_val, account_number, float(balance), wallet_id=user_id_val)
        conn.execute("UPDATE users SET wallet_id = ? WHERE id = ?", (wallet_id, user_id))
        conn.commit()
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def seed_default_users():
    admin_user = get_user_by_email("admin@sirkome.com")
    if not admin_user:
        admin_user = create_user_record(
            name="Admin User",
            email="admin@sirkome.com",
            password="admin1234",
            phone="+1-555-010-0001",
            nin="11111111111",
            bvn="22222222222",
            pin="1234",
            is_admin=1,
            balance=50000000.0,
            account_number="SK-ADMIN",
        )
    else:
        create_or_update_wallet(get_connection(), admin_user["user_id"], admin_user["account_number"], 50000000.0, wallet_id=admin_user["user_id"])

    demo_exists = get_user_by_email("demo@sirkome.com")
    if not demo_exists:
        create_user_record(
            name="Kome Isioro",
            email="demo@sirkome.com",
            password="demo1234",
            phone="+1 (555) 010-4821",
            nin="33333333333",
            bvn="44444444444",
            pin="1234",
            is_admin=0,
            balance=24580.0,
            account_number="SK-4821",
        )

    alias_admin_user = get_user_by_email("komeisioro+admin@gmail.com")
    if not alias_admin_user:
        alias_admin_user = create_user_record(
            name="Admin User",
            email="komeisioro+admin@gmail.com",
            password="admin1234",
            phone="+1-555-010-0001",
            nin="11111111111",
            bvn="22222222222",
            pin="1234",
            is_admin=1,
            balance=50000000.0,
            account_number="SK-ADMIN-ALIAS",
        )
    else:
        create_or_update_wallet(get_connection(), alias_admin_user["user_id"], alias_admin_user["account_number"], 50000000.0, wallet_id=alias_admin_user["user_id"])

    alias_demo_exists = get_user_by_email("komeisioro+demo@gmail.com")
    if not alias_demo_exists:
        create_user_record(
            name="Kome Isioro",
            email="komeisioro+demo@gmail.com",
            password="demo1234",
            phone="+1 (555) 010-4821",
            nin="33333333333",
            bvn="44444444444",
            pin="1234",
            is_admin=0,
            balance=24580.0,
            account_number="SK-4821-ALIAS",
        )

    ensure_wallets()


def add_transaction(account_number: str, transaction_type: str, amount: float, description: str, related_account: str | None = None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO transactions (account_number, type, amount, description, date, related_account) VALUES (?, ?, ?, ?, ?, ?)",
            (account_number, transaction_type, amount, description, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), related_account),
        )
        conn.commit()


def resolve_admin_user(conn: sqlite3.Connection, user_identifier: str):
    normalized_identifier = user_identifier.strip()
    if normalized_identifier.upper().startswith("USR-"):
        target_user = conn.execute("SELECT * FROM users WHERE user_id = ?", (normalized_identifier,)).fetchone()
        if target_user:
            return target_user
        suffix = normalized_identifier[4:]
        if suffix.isdigit():
            return conn.execute("SELECT * FROM users WHERE id = ?", (int(suffix),)).fetchone()
    if normalized_identifier.isdigit():
        return conn.execute("SELECT * FROM users WHERE id = ?", (int(normalized_identifier),)).fetchone()
    return conn.execute(
        "SELECT * FROM users WHERE account_number = ? OR LOWER(email) = ?",
        (resolve_account_number(normalized_identifier), normalize_email(normalized_identifier)),
    ).fetchone()


if os.getenv("DATABASE_URL"):
    # PostgreSQL schema/data are provisioned by Alembic and the reviewed import.
    # Runtime startup must never create, reset, or seed the migrated database.
    pass
else:
    init_db()
    ensure_sqlite_schema_compatibility()
    ensure_user_columns()
    ensure_wallets()
    seed_default_users()


@app.get("/")
def home():
    return {"message": "SirKome Bank API Running"}


def build_user_profile(user):
    wallet = get_wallet_by_account(user["account_number"])
    tier = int(user["verification_tier"] or 1) if "verification_tier" in user.keys() else 1
    tier_limits = {1: 50000.0, 2: 100000.0, 3: 500000.0}
    staff_context = get_staff_context(user)
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"],
        "date_of_birth": user["date_of_birth"] if "date_of_birth" in user.keys() else "",
        "gender": user["gender"] if "gender" in user.keys() else "",
        "account_number": user["account_number"],
        "balance": float(wallet["wallet_balance"] if wallet else 0.0),
        "currency": DEFAULT_CURRENCY,
        "is_admin": bool(user["is_admin"]),
        "user_type": "STAFF" if staff_context else "CUSTOMER",
        "role": staff_context["role"] if staff_context else None,
        "permissions": staff_context["permissions"] if staff_context else [],
        "is_frozen": bool(user["is_frozen"] if "is_frozen" in user.keys() else 0),
        "freeze_reason": user["freeze_reason"] if "freeze_reason" in user.keys() and user["freeze_reason"] else None,
        "tier": f"Tier {tier}",
        "daily_transfer_limit": tier_limits.get(tier, 50000.0),
        "address": user["address"] if "address" in user.keys() else None,
        "proof_of_address_date": user["proof_of_address_date"] if "proof_of_address_date" in user.keys() else None,
    }


def build_auth_response(user, token: str):
    return {
        "token": token,
        "user": build_user_profile(user),
    }


def authenticate_login_user(email: str, password: str):
    user = get_user_by_email(email)
    if not user or user["password"] != hash_password(password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    staff_profile = get_staff_profile_by_user_id(user["id"])
    if staff_profile and not bool(staff_profile["is_active"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This staff account is inactive")

    if user["is_frozen"] if "is_frozen" in user.keys() else 0:
        reason = user["freeze_reason"] if "freeze_reason" in user.keys() and user["freeze_reason"] else "No reason provided"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Your account has been frozen. Reason: {reason}")

    return user


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = authenticate_login_user(payload.email, payload.password)
    token = create_access_token(user["id"])
    return build_auth_response(user, token)


@app.post("/staff/login", response_model=LoginResponse)
def staff_login(payload: StaffLoginRequest):
    user = authenticate_login_user(payload.email, payload.password)
    if not get_staff_context(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")

    token = create_access_token(user["id"])
    return build_auth_response(user, token)


@app.get("/staff/me")
def staff_me(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    user = require_staff(credentials)
    staff_context = get_staff_context(user)
    return {
        "user": build_user_profile(user),
        "role": staff_context["role"],
        "branch_code": staff_context["branch_code"],
        "permissions": staff_context["permissions"],
    }


@app.get("/staff")
def list_staff(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if context["role"] not in {"SUPER_ADMIN", "ADMIN", "BRANCH_MANAGER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff listing access required")

    with get_connection() as conn:
        if context["role"] == "BRANCH_MANAGER":
            if context["branch_id"] is None:
                return []
            rows = conn.execute(
                """
                SELECT u.user_id AS public_user_id, u.name, u.email, u.phone,
                       sp.staff_role, sp.branch_id, sp.is_active, sp.created_at,
                       sp.updated_at, b.branch_code, b.name AS branch_name
                FROM users AS u
                JOIN staff_profiles AS sp ON sp.user_id = u.id
                LEFT JOIN branches AS b ON b.id = sp.branch_id
                WHERE sp.branch_id = ?
                ORDER BY u.name ASC
                """,
                (context["branch_id"],),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT u.user_id AS public_user_id, u.name, u.email, u.phone,
                       sp.staff_role, sp.branch_id, sp.is_active, sp.created_at,
                       sp.updated_at, b.branch_code, b.name AS branch_name
                FROM users AS u
                JOIN staff_profiles AS sp ON sp.user_id = u.id
                LEFT JOIN branches AS b ON b.id = sp.branch_id
                ORDER BY u.name ASC
                """
            ).fetchall()
    return [serialize_staff(row) for row in rows]


@app.get("/staff/{staff_id}")
def get_staff(staff_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff(credentials)
    record = get_staff_record(staff_id)
    if not record or not staff_record_in_scope(current_user, record):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    return serialize_staff(record)


@app.post("/staff")
def create_staff(payload: StaffCreateRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff_management(credentials)
    context = get_staff_context(current_user)
    role = validate_staff_role_assignment(current_user, payload.role)
    if not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Staff name is required")
    name = validate_full_name(payload.name, None, None)
    email = validate_email_address(payload.email)
    phone = validate_phone_number(payload.phone)
    password = validate_password(payload.password)
    pin = validate_pin(payload.pin)

    with get_connection() as conn:
        duplicate = conn.execute(
            "SELECT id FROM users WHERE LOWER(email) = ? OR phone = ?",
            (email, phone),
        ).fetchone()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email or phone already exists")

    branch_id = payload.branch_id
    if context["role"] == "BRANCH_MANAGER":
        if branch_id != context["branch_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch managers may assign staff only to their own branch")
    if branch_id is not None:
        branch = get_branch_by_id(branch_id)
        if not branch or not bool(branch["is_active"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active branch not found")

    user = create_user_record(
        name=name,
        email=email,
        password=password,
        phone=phone,
        nin=None,
        bvn=None,
        pin=pin,
        is_admin=False,
    )
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO staff_profiles (user_id, staff_role, branch_id, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (user["id"], role, branch_id, True),
        )
        conn.commit()
    return serialize_staff(get_staff_record(user["user_id"]))


@app.patch("/staff/{staff_id}/status")
def update_staff_status(staff_id: str, payload: StaffStatusRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff_management(credentials)
    target = get_staff_record(staff_id)
    if not target or not can_manage_staff_record(current_user, target):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    if target["user_id"] == current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot deactivate your own staff account")
    with get_connection() as conn:
        conn.execute(
            "UPDATE staff_profiles SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (bool(payload.is_active), target["staff_profile_id"]),
        )
        conn.commit()
    return serialize_staff(get_staff_record(staff_id))


@app.patch("/staff/{staff_id}")
def update_staff(staff_id: str, payload: StaffUpdateRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff_management(credentials)
    target = get_staff_record(staff_id)
    if not target or not can_manage_staff_record(current_user, target):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")

    context = get_staff_context(current_user)
    updates = []
    params = []
    if payload.name is not None:
        updates.append("name = ?")
        params.append(validate_full_name(payload.name, None, None))
    if payload.phone is not None:
        phone = validate_phone_number(payload.phone)
        with get_connection() as conn:
            duplicate = conn.execute("SELECT id FROM users WHERE phone = ? AND id <> ?", (phone, target["user_id"])).fetchone()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this phone already exists")
        updates.append("phone = ?")
        params.append(phone)

    role = target["staff_role"]
    if payload.role is not None:
        if target["user_id"] == current_user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot change your own staff role")
        role = validate_staff_role_assignment(current_user, payload.role)

    branch_id = target["branch_id"]
    if payload.branch_id is not None:
        if context["role"] == "BRANCH_MANAGER" and payload.branch_id != context["branch_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch managers may assign staff only to their own branch")
        branch = get_branch_by_id(payload.branch_id)
        if not branch or not bool(branch["is_active"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active branch not found")
        branch_id = payload.branch_id

    if role != target["staff_role"] or branch_id != target["branch_id"]:
        with get_connection() as conn:
            conn.execute(
                "UPDATE staff_profiles SET staff_role = ?, branch_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (role, branch_id, target["staff_profile_id"]),
            )
            conn.commit()
    if updates:
        params.append(target["user_id"])
        with get_connection() as conn:
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
            conn.commit()
    return serialize_staff(get_staff_record(staff_id))


@app.get("/branches")
def list_branches(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_branch_management(credentials)
    context = get_staff_context(current_user)
    with get_connection() as conn:
        if context["role"] == "BRANCH_MANAGER":
            if context["branch_id"] is None:
                return []
            rows = conn.execute("SELECT * FROM branches WHERE id = ?", (context["branch_id"],)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM branches ORDER BY name ASC").fetchall()
    return [serialize_branch(row) for row in rows]


@app.get("/branches/{branch_id}")
def get_branch(branch_id: int, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_branch_management(credentials)
    branch = get_branch_by_id(branch_id)
    if not branch or not branch_in_scope(current_user, branch_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    return serialize_branch(branch)


@app.get("/teller/customers", response_model=list[TellerCustomerResponse])
def lookup_teller_customers(query: str, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_permission(credentials, "lookup_customers")
    context = get_staff_context(current_user)
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Search query must contain at least two characters")
    scope_clause, scope_params = teller_scope_clause(context)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT u.id, u.user_id, u.name, u.account_number, u.wallet_id, u.currency,
                   u.is_frozen, u.branch_id, w.wallet_balance
            FROM users AS u
            LEFT JOIN wallets AS w ON w.account_number = u.account_number
            WHERE (u.account_number = ? OR LOWER(u.name) LIKE ? OR u.phone = ?){scope_clause}
            ORDER BY u.name ASC
            LIMIT 20
            """,
            (resolve_account_number(normalized_query), f"%{normalized_query.lower()}%", normalized_query, *scope_params),
        ).fetchall()
    return [serialize_teller_customer(row) for row in rows]


@app.post("/teller/deposits", response_model=TellerTransactionResponse)
def create_teller_deposit(payload: TellerOperationRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_teller_operation(credentials, "create_deposits")
    return process_teller_operation(payload, current_user, "DEPOSIT")


@app.post("/teller/withdrawals", response_model=TellerTransactionResponse)
def create_teller_withdrawal(payload: TellerOperationRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_teller_operation(credentials, "create_withdrawals")
    return process_teller_operation(payload, current_user, "WITHDRAWAL")


@app.get("/teller/transactions", response_model=list[TellerTransactionResponse])
def list_teller_transactions(credentials: HTTPAuthorizationCredentials | None = Depends(security), account_number: str | None = None, transaction_type: str | None = None, transaction_reference: str | None = None, limit: int = 50):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "view_teller_transactions" not in context["permissions"] and "view_branch_transactions" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teller transaction access required")
    conditions = ["t.status = 'COMPLETED'"]
    params = []
    if context["role"] not in {"SUPER_ADMIN", "ADMIN"}:
        if context["branch_id"] is None:
            return []
        conditions.append("t.branch_id = ?")
        params.append(context["branch_id"])
    if account_number:
        conditions.append("t.account_number = ?")
        params.append(resolve_account_number(account_number))
    if transaction_type:
        conditions.append("t.type = ?")
        params.append(transaction_type.strip().upper())
    if transaction_reference:
        conditions.append("t.transaction_reference = ?")
        params.append(transaction_reference.strip())
    limit = max(1, min(limit, 100))
    params.append(limit)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT transaction_reference, type, amount, status, account_number, description, date, branch_id FROM transactions AS t WHERE {' AND '.join(conditions)} ORDER BY t.id DESC LIMIT ?",
            tuple(params),
        ).fetchall()
    return [serialize_teller_transaction(row) for row in rows]


def validate_branch_payload(payload, partial: bool = False):
    values = {}
    for field in ("branch_code", "name", "address", "city", "state", "phone"):
        value = getattr(payload, field, None)
        if value is None and partial:
            continue
        value = (value or "").strip()
        if not value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field.replace('_', ' ').title()} is required")
        if len(value) > 255:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field.replace('_', ' ').title()} is too long")
        values[field] = value
    if "branch_code" in values:
        values["branch_code"] = values["branch_code"].upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{1,63}", values["branch_code"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch code must use 2-64 letters, numbers, hyphens, or underscores")
    if getattr(payload, "email", None) is not None:
        values["email"] = validate_email_address(payload.email) if payload.email.strip() else None
    return values


@app.post("/branches")
def create_branch(payload: BranchCreateRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    require_permission(credentials, "manage_branches")
    values = validate_branch_payload(payload)
    with get_connection() as conn:
        if conn.execute("SELECT id FROM branches WHERE branch_code = ?", (values["branch_code"],)).fetchone():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch code already exists")
        insert_sql = "INSERT INTO branches (branch_code, name, address, city, state, phone, email, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        if os.getenv("DATABASE_URL"):
            insert_sql += " RETURNING id"
        cursor = conn.execute(insert_sql, (values["branch_code"], values["name"], values["address"], values["city"], values["state"], values["phone"], values.get("email"), True))
        conn.commit()
        branch_id = cursor.fetchone()[0] if os.getenv("DATABASE_URL") else cursor.lastrowid
    return serialize_branch(get_branch_by_id(branch_id))


@app.patch("/branches/{branch_id}/status")
def update_branch_status(branch_id: int, payload: BranchStatusRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    require_permission(credentials, "manage_branches")
    branch = get_branch_by_id(branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    with get_connection() as conn:
        conn.execute("UPDATE branches SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (bool(payload.is_active), branch_id))
        conn.commit()
    return serialize_branch(get_branch_by_id(branch_id))


@app.patch("/branches/{branch_id}")
def update_branch(branch_id: int, payload: BranchUpdateRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    require_permission(credentials, "manage_branches")
    if not get_branch_by_id(branch_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    values = validate_branch_payload(payload, partial=True)
    if not values:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No branch fields to update")
    updates = [f"{field} = ?" for field in values]
    params = list(values.values()) + [branch_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE branches SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", tuple(params))
        conn.commit()
    return serialize_branch(get_branch_by_id(branch_id))


@app.post("/auth/send-verification")
def send_verification(payload: EmailVerificationRequest):
    normalized_email = validate_email_address(payload.email)
    if get_user_by_email(normalized_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Existing user found. Do you want to login?")

    code = issue_verification_code(normalized_email)
    response = {"status": "success", "message": "Verification code sent to your email"}
    sent = notify_user_by_email(
        normalized_email,
        "Verify your SirKome Bank email",
        f"Your verification code is: {code}\n\nThis code expires in 15 minutes. Enter it to complete your account creation.",
    )
    is_production = (os.getenv("SIRKOME_ENV") or "development").strip().lower() == "production"
    if not sent and is_production:
        clear_verification_code(normalized_email)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to send verification email. Check the SMTP configuration.")
    return response


@app.post("/auth/verify-email")
def verify_email(payload: EmailCodeVerificationRequest):
    normalized_email = validate_email_address(payload.email)
    if not verify_email_code(normalized_email, payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code")
    return {"status": "success", "message": "Email verified successfully"}


@app.post("/auth/register", response_model=RegisterResponse)
def register(payload: RegisterRequest):
    normalized_email = validate_email_address(payload.email)

    first_name = (payload.first_name or "").strip()
    last_name = (payload.last_name or "").strip()
    middle_name = (payload.middle_name or "").strip()
    if payload.name:
        resolved_name = payload.name.strip()
    else:
        resolved_name = validate_full_name(first_name, last_name, middle_name)

    if not payload.name:
        name_to_store = resolved_name
    else:
        name_to_store = validate_full_name(payload.name, None, None)

    phone = validate_phone_number(payload.phone)
    date_of_birth = validate_date_of_birth(payload.date_of_birth) if payload.date_of_birth else ""
    gender = validate_gender(payload.gender) if payload.gender else ""
    nin = validate_identity_number(payload.nin, "NIN") if payload.nin else None
    bvn = validate_identity_number(payload.bvn, "BVN") if payload.bvn else None
    if not nin and not bvn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide either a valid NIN or BVN")
    password = validate_password(payload.password)
    pin = validate_pin(payload.pin or "1234")

    existing_user = get_existing_registration_field(normalized_email, phone, nin, bvn)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Existing user found. Do you want to login?")

    cached_entry = VERIFICATION_CACHE.get(normalized_email)
    if not cached_entry or not bool(cached_entry.get("used", False)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please verify your email before creating an account")
    if int(cached_entry.get("expires_at", 0)) < int(time.time()):
        clear_verification_code(normalized_email)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code expired. Please request a new one")

    verification_tier = 2 if nin and bvn else 1
    user = create_user_record(name_to_store, normalized_email, password, phone, nin, bvn, pin, verification_tier=verification_tier, date_of_birth=date_of_birth, gender=gender)
    clear_verification_code(normalized_email)
    subject = "Welcome to SirKome Bank"
    body = f"Hello {user['name']},\n\nYour account {user['account_number']} has been created. Welcome to SirKome Bank.\n\nRegards,\nSirKome Team"
    notify_user_by_email(user["email"], subject, body)
    return {"user": build_user_profile(user)}


@app.get("/accounts", response_model=list[AccountResponse])
def get_accounts(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    wallet = get_wallet_by_account(user["account_number"])
    balance = float(wallet["wallet_balance"] if wallet else 0.0)

    return [{
        "account_number": user["account_number"],
        "balance": balance,
        "currency": DEFAULT_CURRENCY,
        "type": "Checking",
    }]


@app.get("/accounts/lookup")
def lookup_account(account_number: str, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    current_user = get_user_by_token(credentials.credentials)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    account_number = resolve_account_number((account_number or '').strip())
    if not account_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account number is required")

    target_user = get_user_by_account(account_number)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return {
        "account_number": target_user["account_number"],
        "name": target_user["name"],
        "exists": True,
        "is_current_user": target_user["id"] == current_user["id"],
    }


@app.get("/saved-accounts")
def list_saved_accounts(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    current_user = get_user_by_token(credentials.credentials)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, account_number, account_name, created_at FROM saved_accounts WHERE user_id = ? ORDER BY id DESC",
            (current_user["id"],),
        ).fetchall()

    return [{
        "id": row["id"],
        "account_number": row["account_number"],
        "account_name": row["account_name"],
        "created_at": row["created_at"],
    } for row in rows]


@app.post("/saved-accounts")
def save_account(payload: SavedAccountRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    current_user = get_user_by_token(credentials.credentials)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    account_number = resolve_account_number((payload.account_number or '').strip())
    if not account_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account number is required")

    target_user = get_user_by_account(account_number)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if target_user["id"] == current_user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot save your own account")

    safe_name = (payload.account_name or target_user["name"] or "Recipient").strip() or target_user["name"]
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM saved_accounts WHERE user_id = ? AND account_number = ?",
            (current_user["id"], account_number),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE saved_accounts SET account_name = ? WHERE id = ?",
                (safe_name, existing["id"]),
            )
            conn.commit()
            return {
                "id": existing["id"],
                "user_id": current_user["id"],
                "account_number": account_number,
                "account_name": safe_name,
                "created_at": existing["created_at"],
            }

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_sql = "INSERT INTO saved_accounts (user_id, account_number, account_name, created_at) VALUES (?, ?, ?, ?)"
        if os.getenv("DATABASE_URL"):
            insert_sql += " RETURNING id"
        cursor = conn.execute(
            insert_sql,
            (current_user["id"], account_number, safe_name, created_at),
        )
        conn.commit()
        saved_id = cursor.fetchone()[0] if os.getenv("DATABASE_URL") else cursor.lastrowid
        return {
            "id": saved_id,
            "user_id": current_user["id"],
            "account_number": account_number,
            "account_name": safe_name,
            "created_at": created_at,
        }


@app.get("/transactions", response_model=list[TransactionResponse] | TransactionPageResponse)
def get_transactions(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security), page: int = 1, per_page: int = 10):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page

    with get_connection() as conn:
        total_row = conn.execute(
            "SELECT COUNT(*) AS total FROM transactions WHERE account_number = ?",
            (user["account_number"],),
        ).fetchone()
        total = int(total_row["total"] if total_row else 0)
        rows = conn.execute(
            "SELECT * FROM transactions WHERE account_number = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user["account_number"], per_page, offset),
        ).fetchall()

    items = [
        {
            "type": row["type"],
            "amount": float(row["amount"]),
            "description": row["description"],
            "date": row["date"],
            "transaction_reference": row["transaction_reference"] if "transaction_reference" in row.keys() else None,
            "status": row["status"] if "status" in row.keys() else None,
        }
        for row in rows
    ]

    if "page" not in request.query_params and "per_page" not in request.query_params:
        return items

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, (total + per_page - 1) // per_page),
        "items": items,
    }


@app.get("/customers")
def list_customers(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security), page: int = 1, per_page: int = 20, query: str | None = None, branch_id: int | None = None, status: str | None = None):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "view_all_customers" not in context["permissions"] and "view_branch_customers" not in context["permissions"] and "view_assigned_customers" not in context["permissions"] and "view_permitted_customer_profiles" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer listing access required")

    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page
    conditions = []
    params = []

    if context["role"] not in {"SUPER_ADMIN", "ADMIN"}:
        if context["branch_id"] is None:
            return {"page": page, "per_page": per_page, "total": 0, "pages": 1, "items": []}
        conditions.append("u.branch_id = ?")
        params.append(context["branch_id"])
    if branch_id is not None:
        if context["role"] not in {"SUPER_ADMIN", "ADMIN"} and branch_id != context["branch_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch scope mismatch")
        conditions.append("u.branch_id = ?")
        params.append(branch_id)
    if status:
        normalized_status = status.strip().lower()
        if normalized_status == "active":
            conditions.append("CAST(u.is_frozen AS INTEGER) = 0")
        elif normalized_status == "frozen":
            conditions.append("CAST(u.is_frozen AS INTEGER) = 1")
        elif normalized_status == "inactive":
            conditions.append("CAST(u.is_frozen AS INTEGER) = 1")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported status filter")
    if query and query.strip():
        q = query.strip()
        conditions.append("(LOWER(u.name) LIKE ? OR LOWER(u.email) LIKE ? OR LOWER(u.phone) LIKE ? OR u.user_id = ? OR u.account_number = ?)")
        params.extend([f"%{q.lower()}%", f"%{q.lower()}%", f"%{q.lower()}%", q, resolve_account_number(q)])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    order_clause = "ORDER BY u.id DESC" if bool(status or (query and query.strip())) else "ORDER BY u.name ASC"
    with get_connection() as conn:
        total_row = conn.execute(f"SELECT COUNT(*) AS total FROM users AS u {where_clause}", tuple(params)).fetchone()
        total = int(total_row["total"] if total_row else 0)
        rows = conn.execute(
            f"""
            SELECT
                u.id,
                u.user_id,
                u.name,
                u.email,
                u.phone,
                u.account_number,
                u.currency,
                u.is_frozen,
                u.freeze_reason,
                u.branch_id,
                u.address,
                u.date_of_birth,
                u.gender,
                COALESCE(w.wallet_balance, 0.0) AS wallet_balance,
                w.status AS wallet_status,
                b.branch_code,
                b.name AS branch_name
            FROM users AS u
            LEFT JOIN wallets AS w ON w.account_number = u.account_number
            LEFT JOIN branches AS b ON b.id = u.branch_id
            {where_clause}
            {order_clause}
            LIMIT ? OFFSET ?
            """,
            (*params, per_page, offset),
        ).fetchall()

    items = [serialize_customer_summary(row) for row in rows]
    return {"page": page, "per_page": per_page, "total": total, "pages": max(1, (total + per_page - 1) // per_page), "items": items}


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "view_all_customers" not in context["permissions"] and "view_branch_customers" not in context["permissions"] and "view_assigned_customers" not in context["permissions"] and "view_permitted_customer_profiles" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access required")

    with get_connection() as conn:
        target = conn.execute(
            """
            SELECT
                u.id,
                u.user_id,
                u.name,
                u.email,
                u.phone,
                u.account_number,
                u.currency,
                u.is_frozen,
                u.freeze_reason,
                u.branch_id,
                u.address,
                u.date_of_birth,
                u.gender,
                COALESCE(w.wallet_balance, 0.0) AS wallet_balance,
                w.status AS wallet_status,
                b.branch_code,
                b.name AS branch_name
            FROM users AS u
            LEFT JOIN wallets AS w ON w.account_number = u.account_number
            LEFT JOIN branches AS b ON b.id = u.branch_id
            WHERE u.user_id = ? OR u.email = ? OR u.account_number = ? OR CAST(u.id AS TEXT) = ?
            LIMIT 1
            """,
            (customer_id, normalize_email(customer_id), resolve_account_number(customer_id), customer_id),
        ).fetchone()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    if not customer_in_scope(current_user, target):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer is outside your branch scope")
    recent_transactions = []
    with get_connection() as conn:
        recent_rows = conn.execute(
            "SELECT transaction_reference, type, amount, status, description, date FROM transactions WHERE account_number = ? ORDER BY id DESC LIMIT 10",
            (target["account_number"],),
        ).fetchall()
    for row in recent_rows:
        recent_transactions.append({
            "transaction_reference": row["transaction_reference"],
            "type": row["type"],
            "amount": float(row["amount"]),
            "status": row["status"],
            "description": row["description"],
            "date": row["date"],
        })
    target = {**dict(target), "recent_transactions": recent_transactions}
    return serialize_customer_detail(target)


@app.patch("/customers/{customer_id}")
def update_customer(customer_id: str, payload: CustomerUpdateRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "manage_customers" not in context["permissions"] and "view_permitted_customer_profiles" not in context["permissions"] and "manage_permitted_customer_accounts" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer profile update access required")
    with get_connection() as conn:
        target = conn.execute(
            "SELECT * FROM users WHERE user_id = ? OR email = ? OR account_number = ? OR CAST(id AS TEXT) = ?",
            (customer_id, normalize_email(customer_id), resolve_account_number(customer_id), customer_id),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        target = dict(target)
        if not customer_in_scope(current_user, target):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer is outside your branch scope")
        if payload.name is not None:
            if not payload.name.strip():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer name is required")
            target["name"] = validate_full_name(payload.name, None, None)
        if payload.email is not None:
            normalized_email = validate_email_address(payload.email)
            duplicate = conn.execute("SELECT id FROM users WHERE LOWER(email) = ? AND id <> ?", (normalized_email, target["id"])).fetchone()
            if duplicate:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")
            target["email"] = normalized_email
        if payload.phone is not None:
            target["phone"] = validate_phone_number(payload.phone)
        if payload.address is not None:
            target["address"] = (payload.address or "").strip() or None
        if payload.date_of_birth is not None:
            target["date_of_birth"] = validate_date_of_birth(payload.date_of_birth)
        if payload.gender is not None:
            target["gender"] = validate_gender(payload.gender)
        if payload.name is None and payload.email is None and payload.phone is None and payload.address is None and payload.date_of_birth is None and payload.gender is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No profile fields to update")
        updates = []
        params = []
        for field in ("name", "email", "phone", "address", "date_of_birth", "gender"):
            if field in {"name", "email", "phone", "address", "date_of_birth", "gender"} and target.get(field) is not None:
                if field == "name":
                    updates.append("name = ?")
                    params.append(target["name"])
                elif field == "email":
                    updates.append("email = ?")
                    params.append(target["email"])
                elif field == "phone":
                    updates.append("phone = ?")
                    params.append(target["phone"])
                elif field == "address":
                    updates.append("address = ?")
                    params.append(target["address"])
                elif field == "date_of_birth":
                    updates.append("date_of_birth = ?")
                    params.append(target["date_of_birth"])
                elif field == "gender":
                    updates.append("gender = ?")
                    params.append(target["gender"])
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No profile fields to update")
        params.append(target["id"])
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (target["id"],)).fetchone()
    updated = dict(updated) if updated is not None else {}
    updated["branch_id"] = updated.get("branch_id")
    return get_customer(updated["user_id"], credentials)


@app.patch("/customers/{customer_id}/status")
def update_customer_status(customer_id: str, payload: CustomerStatusRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "manage_customers" not in context["permissions"] and "freeze_accounts" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer status update access required")
    with get_connection() as conn:
        target = conn.execute("SELECT * FROM users WHERE user_id = ? OR email = ? OR account_number = ? OR CAST(id AS TEXT) = ?", (customer_id, normalize_email(customer_id), resolve_account_number(customer_id), customer_id)).fetchone()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        if not customer_in_scope(current_user, target):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer is outside your branch scope")
        if target["is_admin"] == 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator accounts cannot be frozen or deactivated through customer management")
        reason = (payload.reason or "").strip()
        if payload.is_frozen and not reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A freeze reason is required when freezing a customer")
        conn.execute("UPDATE users SET is_frozen = ?, freeze_reason = ? WHERE id = ?", (bool(payload.is_frozen), reason if payload.is_frozen else "", target["id"]))
        conn.commit()
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (target["id"],)).fetchone()
    if bool(updated["is_frozen"]):
        return {"status": "FROZEN", "reason": updated["freeze_reason"] or None, "customer": get_customer(updated["user_id"], credentials)}
    return {"status": "ACTIVE", "reason": None, "customer": get_customer(updated["user_id"], credentials)}


@app.patch("/customers/{customer_id}/branch")
def update_customer_branch(customer_id: str, payload: CustomerBranchRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_staff(credentials)
    context = get_staff_context(current_user)
    if "manage_customers" not in context["permissions"] and "manage_branch_operations" not in context["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Branch assignment access required")
    with get_connection() as conn:
        target = conn.execute("SELECT * FROM users WHERE user_id = ? OR email = ? OR account_number = ? OR CAST(id AS TEXT) = ?", (customer_id, normalize_email(customer_id), resolve_account_number(customer_id), customer_id)).fetchone()
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        if context["role"] not in {"SUPER_ADMIN", "ADMIN"} and context["branch_id"] != payload.branch_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only assign customers within your branch")
        branch = conn.execute("SELECT * FROM branches WHERE id = ?", (payload.branch_id,)).fetchone()
        if not branch or not bool(branch["is_active"]):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active branch not found")
        conn.execute("UPDATE users SET branch_id = ? WHERE id = ?", (payload.branch_id, target["id"]))
        conn.commit()
        updated = conn.execute("SELECT * FROM users WHERE id = ?", (target["id"],)).fetchone()
    return {"user_id": updated["user_id"], "branch": {"id": branch["id"], "code": branch["branch_code"], "name": branch["name"]}}


@app.get("/admin/users")
def list_users_for_admin(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security), page: int = 1, per_page: int = 10):
    require_permission(credentials, "view_all_customers")

    if "page" not in request.query_params and "per_page" not in request.query_params:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    u.id,
                    u.user_id,
                    u.name,
                    u.email,
                    u.phone,
                    u.account_number,
                    COALESCE(w.wallet_balance, 0.0) AS balance,
                    u.currency,
                    u.is_admin,
                    u.is_frozen,
                    u.freeze_reason
                FROM users AS u
                LEFT JOIN wallets AS w ON w.account_number = u.account_number
                ORDER BY u.id ASC
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "name": row["name"],
                "email": row["email"],
                "phone": row["phone"],
                "account_number": row["account_number"],
                "balance": float(row["balance"]),
                "currency": row["currency"],
                "is_admin": bool(row["is_admin"]),
                "is_frozen": bool(row["is_frozen"]),
                "freeze_reason": row["freeze_reason"] or None,
            }
            for row in rows
        ]

    return list_customers(request, credentials, page=page, per_page=per_page)


@app.get("/staff/customers")
def list_staff_customers(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security), page: int = 1, per_page: int = 20, query: str | None = None, branch_id: int | None = None, status: str | None = None):
    return list_customers(request, credentials, page=page, per_page=per_page, query=query, branch_id=branch_id, status=status)


@app.get("/staff/customers/{customer_id}")
def get_staff_customer(customer_id: str, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    return get_customer(customer_id, credentials)


@app.patch("/admin/users/{user_identifier}/freeze")
def freeze_user_for_admin(user_identifier: str, payload: FreezeUserRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    require_permission(credentials, "freeze_accounts")

    with get_connection() as conn:
        target_user = resolve_admin_user(conn, user_identifier)

        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if target_user["is_admin"] == 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins cannot be frozen")

        is_frozen = bool(payload.is_frozen)
        reason = (payload.reason or "").strip()
        if is_frozen and not reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A freeze reason is required when freezing an account")

        conn.execute(
            "UPDATE users SET is_frozen = ?, freeze_reason = ? WHERE id = ?",
            (is_frozen, reason if is_frozen else "", target_user["id"]),
        )
        conn.commit()
        target_user = conn.execute("SELECT * FROM users WHERE id = ?", (target_user["id"],)).fetchone()

    user_profile = build_user_profile(target_user)
    status_message = "User frozen successfully" if is_frozen else "User unfrozen successfully"
    notify_user_by_email(
        target_user["email"],
        "Account status updated - SirKome Bank",
        f"Your account has been {'frozen' if is_frozen else 'unfrozen'} by an administrator."
        + (f" Reason: {reason}" if is_frozen else ""),
    )
    return {"status": "success", "message": status_message, "user": user_profile}


@app.delete("/admin/users/{user_identifier}")
def delete_user_for_admin(user_identifier: str, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    current_user = require_permission(credentials, "manage_customers")

    with get_connection() as conn:
        target_user = resolve_admin_user(conn, user_identifier)

        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if target_user["id"] == current_user["id"] or target_user["is_admin"] == 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin accounts cannot be deleted")

        conn.execute("DELETE FROM transactions WHERE account_number = ?", (target_user["account_number"],))
        conn.execute("DELETE FROM wallets WHERE account_number = ?", (target_user["account_number"],))
        conn.execute("DELETE FROM users WHERE id = ?", (target_user["id"],))
        conn.commit()

    return {"status": "success", "message": "User removed successfully"}


@app.get("/notifications", response_model=NotificationPageResponse)
def list_notifications(credentials: HTTPAuthorizationCredentials | None = Depends(security), page: int = 1, per_page: int = 10):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    page = max(1, page)
    per_page = max(1, min(per_page, 50))
    offset = (page - 1) * per_page
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS total FROM notifications WHERE user_id = ?", (user["id"],)).fetchone()["total"]
        unread = conn.execute("SELECT COUNT(*) AS total FROM notifications WHERE user_id = ? AND is_read = 0", (user["id"],)).fetchone()["total"]
        rows = conn.execute(
            "SELECT id, title, message, is_read, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user["id"], per_page, offset),
        ).fetchall()

    return {
        "page": page,
        "per_page": per_page,
        "total": int(total),
        "pages": max(1, (int(total) + per_page - 1) // per_page),
        "unread": int(unread),
        "items": [{**dict(row), "is_read": bool(row["is_read"])} for row in rows],
    }


@app.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM notifications WHERE id = ? AND user_id = ?", (notification_id, user["id"]))
        conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"status": "success", "message": "Notification deleted"}


@app.delete("/notifications")
def clear_notifications(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    with get_connection() as conn:
        conn.execute("DELETE FROM notifications WHERE user_id = ?", (user["id"],))
        conn.commit()
    return {"status": "success", "message": "All notifications cleared"}


@app.post("/transfer", response_model=TransferResponse)
def transfer(payload: TransferRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    current_user = get_user_by_token(credentials.credentials)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    pin = validate_pin(payload.pin or "1234")
    if current_user["pin_hash"] != hash_pin(pin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid transfer PIN")

    sender = get_user_by_account(payload.from_account)
    receiver = get_user_by_account(payload.to_account)
    if not sender or not receiver:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

    if sender["account_number"].strip().upper() == receiver["account_number"].strip().upper():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot transfer money to your own account")

    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero")

    if current_user["is_admin"] != 1 and sender["account_number"] != current_user["account_number"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only transfer from your own account")

    if current_user["is_admin"] != 1:
        tier = int(current_user["verification_tier"] or 1) if "verification_tier" in current_user.keys() else 1
        daily_limit = {1: 50000.0, 2: 100000.0, 3: 500000.0}.get(tier, 50000.0)
        today = datetime.now().strftime("%Y-%m-%d")
        with get_connection() as conn:
            daily_total = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE account_number = ? AND type = 'debit' AND date LIKE ?",
                (sender["account_number"], f"{today}%"),
            ).fetchone()["total"]
        if float(daily_total) + payload.amount > daily_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Your {('Tier ' + str(tier))} daily transfer limit is {daily_limit:,.0f}")

    sender_wallet = get_wallet_by_account(sender["account_number"])
    receiver_wallet = get_wallet_by_account(receiver["account_number"])
    if not sender_wallet or not receiver_wallet:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Wallets are not available for this transfer")

    if float(sender_wallet["wallet_balance"]) < payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

    idempotency_key = (payload.idempotency_key or "").strip()
    if idempotency_key:
        with get_connection() as conn:
            existing_request = conn.execute(
                "SELECT * FROM transfer_requests WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if existing_request:
            return {
                "status": "success",
                "message": "Transfer completed",
                "receipt_id": existing_request["receipt_id"],
                "from_account": existing_request["from_account"],
                "to_account": existing_request["to_account"],
                "amount": float(existing_request["amount"]),
                "description": existing_request["description"],
                "date": existing_request["date"],
            }

    transfer_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    receipt_id = f"RCP-{uuid.uuid4().hex[:12].upper()}"
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        locked_sender_wallet = conn.execute(
            "SELECT wallet_balance FROM wallets WHERE account_number = ?",
            (sender["account_number"],),
        ).fetchone()
        if not locked_sender_wallet or float(locked_sender_wallet["wallet_balance"]) < payload.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")
        if idempotency_key:
            existing_request = conn.execute(
                "SELECT * FROM transfer_requests WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing_request:
                conn.commit()
                return {
                    "status": "success",
                    "message": "Transfer completed",
                    "receipt_id": existing_request["receipt_id"],
                    "from_account": existing_request["from_account"],
                    "to_account": existing_request["to_account"],
                    "amount": float(existing_request["amount"]),
                    "description": existing_request["description"],
                    "date": existing_request["date"],
                }

        conn.execute("UPDATE wallets SET wallet_balance = wallet_balance - ? WHERE account_number = ?", (payload.amount, sender["account_number"]))
        conn.execute("UPDATE wallets SET wallet_balance = wallet_balance + ? WHERE account_number = ?", (payload.amount, receiver["account_number"]))
        conn.execute(
            "INSERT INTO transactions (account_number, type, amount, description, date, related_account) VALUES (?, ?, ?, ?, ?, ?)",
            (sender["account_number"], "debit", payload.amount, payload.description, transfer_date, receiver["account_number"]),
        )
        conn.execute(
            "INSERT INTO transactions (account_number, type, amount, description, date, related_account) VALUES (?, ?, ?, ?, ?, ?)",
            (receiver["account_number"], "credit", payload.amount, payload.description, transfer_date, sender["account_number"]),
        )
        if idempotency_key:
            conn.execute(
                "INSERT INTO transfer_requests (idempotency_key, receipt_id, from_account, to_account, amount, description, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (idempotency_key, receipt_id, sender["account_number"], receiver["account_number"], payload.amount, payload.description, transfer_date),
            )
        conn.commit()

    sender_email = sender["email"]
    receiver_email = receiver["email"]
    notify_user_by_email(
        sender_email,
        "Debit notification - SirKome Bank",
        f"Your account {sender['account_number']} was debited by {payload.amount} {sender['currency']}.\nDescription: {payload.description}",
    )
    notify_user_by_email(
        receiver_email,
        "Credit notification - SirKome Bank",
        f"Your account {receiver['account_number']} was credited by {payload.amount} {receiver['currency']}.\nDescription: {payload.description}",
    )

    return {
        "status": "success",
        "message": "Transfer completed",
        "receipt_id": receipt_id,
        "from_account": sender["account_number"],
        "to_account": receiver["account_number"],
        "amount": payload.amount,
        "description": payload.description,
        "date": transfer_date,
    }


@app.post("/profile/update")
def update_profile(payload: ProfileUpdateRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    updates = []
    params = []
    if payload.name:
        updates.append("name = ?")
        params.append(validate_full_name(payload.name, None, None))
    if payload.phone:
        updates.append("phone = ?")
        params.append(validate_phone_number(payload.phone))
    if payload.email:
        updates.append("email = ?")
        params.append(validate_email_address(payload.email))
    if payload.date_of_birth:
        updates.append("date_of_birth = ?")
        params.append(validate_date_of_birth(payload.date_of_birth))
    if payload.gender:
        updates.append("gender = ?")
        params.append(validate_gender(payload.gender))

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    params.append(user["id"])
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()

    try:
        send_email(user["email"], "Profile updated - SirKome Bank", f"Hello {payload.name or user['name']},\n\nYour profile was updated. If you did not perform this change, contact support immediately.")
    except Exception:
        pass

    return {"status": "success", "message": "Profile updated"}


@app.get("/profile", response_model=UserProfile)
def get_profile(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return build_user_profile(user)


def verify_address_with_google_maps(address: str) -> bool:
    api_key = (os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("SIRKOME_GOOGLE_MAPS_API_KEY") or "").strip()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google Maps verification is not configured")
    query = urllib.parse.urlencode({"address": address, "key": api_key})
    try:
        with urllib.request.urlopen(f"https://maps.googleapis.com/maps/api/geocode/json?{query}", timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to verify the address with Google Maps") from exc
    return result.get("status") == "OK" and bool(result.get("results"))


@app.post("/profile/upgrade")
def upgrade_profile(payload: ProfileUpgradeRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    nin = validate_identity_number(payload.nin, "NIN") if payload.nin else user["nin"]
    bvn = validate_identity_number(payload.bvn, "BVN") if payload.bvn else user["bvn"]
    if not nin and not bvn:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide a valid NIN or BVN")

    tier = 2 if nin and bvn else 1
    proof_values = [payload.address, payload.proof_of_address_filename, payload.proof_of_address_data, payload.proof_of_address_date]
    if any(proof_values):
        if not all(proof_values):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Address, proof document, and proof date are all required")
        try:
            proof_date = datetime.strptime(payload.proof_of_address_date, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proof date must use YYYY-MM-DD") from exc
        if proof_date > datetime.now() or proof_date < datetime.now() - timedelta(days=90):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proof of address must be dated within the last 3 months")
        if not verify_address_with_google_maps(payload.address.strip()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google Maps could not verify this address")
        if len(payload.proof_of_address_data) > 8_000_000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proof document is too large")
        tier = 3 if nin and bvn else 2

    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET nin = ?, bvn = ?, verification_tier = ?, address = COALESCE(?, address), proof_of_address_filename = COALESCE(?, proof_of_address_filename), proof_of_address_data = COALESCE(?, proof_of_address_data), proof_of_address_date = COALESCE(?, proof_of_address_date) WHERE id = ?",
            (nin, bvn, tier, payload.address, payload.proof_of_address_filename, payload.proof_of_address_data, payload.proof_of_address_date, user["id"]),
        )
        conn.commit()
        updated_user = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
    return {"status": "success", "message": f"Profile upgraded to Tier {tier}", "user": build_user_profile(updated_user)}


@app.post("/debug/send-test-email")
def debug_send_test_email(payload: dict):
    """Send a test email to verify SMTP configuration.

    JSON body: { "email": "you@example.com", "subject": "optional", "body": "optional" }
    """
    email = payload.get("email")
    subject = payload.get("subject", "SirKome Test Email")
    body = payload.get("body", "This is a test email from SirKome Bank.")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email is required in the JSON body")

    sent = send_email(email, subject, body)
    return {
        "sent": sent,
        "smtp_host": (os.getenv("SIRKOME_SMTP_HOST") or "").strip(),
        "smtp_port": (os.getenv("SIRKOME_SMTP_PORT") or "587").strip(),
        "smtp_user": (os.getenv("SIRKOME_SMTP_USER") or "").strip(),
        "error": LAST_EMAIL_ERROR or None,
    }
