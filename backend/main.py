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
from pathlib import Path
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage
from collections import defaultdict

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


class UserProfile(BaseModel):
    name: str
    email: str
    phone: str
    date_of_birth: str
    gender: str
    account_number: str
    balance: float
    currency: str = DEFAULT_CURRENCY
    is_admin: bool = False
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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
                proof_of_address_date TEXT
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
                related_account TEXT
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
        if (
            normalize_email(user["email"]) == normalized_email
            or stored_phone == phone
            or (nin is not None and user["nin"] == nin)
            or (bvn is not None and user["bvn"] == bvn)
        ):
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


def get_wallet_by_account(account_number: str):
    normalized_account = resolve_account_number(account_number)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM wallets WHERE account_number = ?", (normalized_account,)).fetchone()


def require_authenticated_admin(credentials: HTTPAuthorizationCredentials | None) -> sqlite3.Row:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    current_user = get_user_by_token(credentials.credentials)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if current_user["is_admin"] != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

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
    with get_connection() as conn:
        user_id_val = f"USR-{uuid.uuid4().hex[:12].upper()}"
        cursor = conn.execute(
            """
            INSERT INTO users (user_id, name, email, password, phone, date_of_birth, gender, account_number, currency, is_admin, token, nin, bvn, pin_hash, wallet_id, is_frozen, freeze_reason, verification_tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id_val, name, email, hash_password(password), phone, date_of_birth, gender, account_number, DEFAULT_CURRENCY, is_admin, None, nin, bvn, hash_pin(pin), user_id_val, is_frozen, freeze_reason, resolved_verification_tier),
        )
        conn.commit()
        user_id = cursor.lastrowid
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


init_db()
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


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = get_user_by_email(payload.email)
    if not user or user["password"] != hash_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user["is_frozen"] if "is_frozen" in user.keys() else 0:
        reason = user["freeze_reason"] if "freeze_reason" in user.keys() and user["freeze_reason"] else "No reason provided"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Your account has been frozen. Reason: {reason}")

    token = create_access_token(user["id"])
    return build_auth_response(user, token)


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
    smtp_configured = all(
        os.getenv(name)
        for name in ("SIRKOME_SMTP_HOST", "SIRKOME_SMTP_USER", "SIRKOME_SMTP_PASS")
    )
    if not sent and (smtp_configured or os.getenv("SIRKOME_ENV") == "production"):
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
        cursor = conn.execute(
            "INSERT INTO saved_accounts (user_id, account_number, account_name, created_at) VALUES (?, ?, ?, ?)",
            (current_user["id"], account_number, safe_name, created_at),
        )
        conn.commit()
        saved_id = cursor.lastrowid
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


@app.get("/admin/users")
def list_users_for_admin(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security), page: int = 1, per_page: int = 10):
    require_authenticated_admin(credentials)

    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page

    with get_connection() as conn:
        total_rows = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()
        total = int(total_rows["total"] if total_rows else 0)
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
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        ).fetchall()

    items = [
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

    if "page" not in request.query_params and "per_page" not in request.query_params:
        return items

    return {
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": max(1, (total + per_page - 1) // per_page),
        "items": items,
    }


@app.patch("/admin/users/{user_identifier}/freeze")
def freeze_user_for_admin(user_identifier: str, payload: FreezeUserRequest, credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    require_authenticated_admin(credentials)

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
            (1 if is_frozen else 0, reason if is_frozen else "", target_user["id"]),
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
    current_user = require_authenticated_admin(credentials)

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

    if sender_wallet["wallet_balance"] < payload.amount:
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
