import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
import smtplib
from email.message import EmailMessage

from fastapi import Depends, FastAPI, HTTPException, status
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
    name: str
    email: str
    password: str
    phone: str
    nin: str
    bvn: str
    pin: str | None = None


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: float
    description: str = "Transfer"
    pin: str | None = None


class UserProfile(BaseModel):
    name: str
    email: str
    phone: str
    account_number: str
    balance: float
    currency: str = "USD"


class AccountResponse(BaseModel):
    account_number: str
    balance: float
    currency: str
    type: str


class TransactionResponse(BaseModel):
    type: str
    amount: float
    description: str
    date: str


class LoginResponse(BaseModel):
    token: str
    user: UserProfile


class TransferResponse(BaseModel):
    status: str
    message: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                wallet_id TEXT,
                currency TEXT NOT NULL DEFAULT 'USD',
                is_admin INTEGER NOT NULL DEFAULT 0,
                token TEXT,
                nin TEXT,
                bvn TEXT,
                pin_hash TEXT
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
                user_id INTEGER UNIQUE NOT NULL,
                account_number TEXT UNIQUE NOT NULL,
                wallet_balance REAL NOT NULL DEFAULT 0.0,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL
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


def create_or_update_wallet(conn: sqlite3.Connection, user_id: int, account_number: str, balance: float = 0.0) -> str:
    existing_wallet = conn.execute("SELECT wallet_id FROM wallets WHERE user_id = ?", (user_id,)).fetchone()
    if existing_wallet:
        conn.execute(
            "UPDATE wallets SET account_number = ?, wallet_balance = ?, currency = ?, status = 'active' WHERE user_id = ?",
            (account_number, float(balance), "USD", user_id),
        )
        return existing_wallet["wallet_id"]

    wallet_id = f"WLT-{uuid.uuid4().hex[:12].upper()}"
    conn.execute(
        "INSERT INTO wallets (wallet_id, user_id, account_number, wallet_balance, currency, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (wallet_id, user_id, account_number, float(balance), "USD", "active", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
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
        users = conn.execute("SELECT id, account_number, balance FROM users").fetchall()
        for user in users:
            create_or_update_wallet(conn, user["id"], user["account_number"], float(user["balance"] or 0.0))
        conn.commit()


def validate_identity_number(value: str, field_name: str) -> str:
    if not value or len(value) != 11 or not value.isdigit() or any(char.isspace() for char in value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} must be exactly 11 digits with no spaces")
    return value

def validate_pin(pin: str) -> str:
    if not pin or len(pin) != 4 or not pin.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN must be exactly 4 digits")
    return pin


def generate_account_number() -> str:
    while True:
        suffix = datetime.now().strftime("%H%M%S")
        candidate = f"SK-{suffix}"
        if not get_user_by_account(candidate):
            return candidate


def resolve_account_number(account_number: str) -> str:
    aliases = {
        "VB-ADMIN": "SK-ADMIN",
    }
    return aliases.get(account_number, account_number)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str):
    normalized_email = normalize_email(email)
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE LOWER(email) = ?", (normalized_email,)).fetchone()


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


def send_email(to_address: str, subject: str, body: str) -> bool:
    load_env_file()

    smtp_host = os.getenv("SIRKOME_SMTP_HOST")
    smtp_port = int(os.getenv("SIRKOME_SMTP_PORT", "587"))
    smtp_user = os.getenv("SIRKOME_SMTP_USER")
    smtp_pass = os.getenv("SIRKOME_SMTP_PASS")

    # Always log the notification for audit/debug
    print({"email_to": to_address, "subject": subject, "body": body})

    if not smtp_host or not smtp_user or not smtp_pass:
        print("SMTP not configured: email notification skipped.")
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = os.getenv("SIRKOME_FROM", smtp_user)
        msg["To"] = to_address
        msg.set_content(body)

        if smtp_port == 465:
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
        print("Email send failed:", exc)
        return False


def notify_user_by_email(to_address: str, subject: str, body: str) -> bool:
    sent = send_email(to_address, subject, body)
    if not sent:
        print(f"Notification email could not be delivered to {to_address}.")
    return sent


def create_user_record(name: str, email: str, password: str, phone: str, nin: str, bvn: str, pin: str, is_admin: int = 0, balance: float = 0.0, account_number: str | None = None, token: str | None = None):
    account_number = account_number or generate_account_number()
    with get_connection() as conn:
        user_id_val = f"USR-{uuid.uuid4().hex[:12].upper()}"
        cursor = conn.execute(
            """
            INSERT INTO users (user_id, name, email, password, phone, account_number, balance, currency, is_admin, token, nin, bvn, pin_hash, wallet_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id_val, name, email, hash_password(password), phone, account_number, balance, "USD", is_admin, None, nin, bvn, hash_pin(pin), None),
        )
        conn.commit()
        user_id = cursor.lastrowid
        wallet_id = create_or_update_wallet(conn, user_id, account_number, float(balance))
        conn.execute("UPDATE users SET wallet_id = ? WHERE id = ?", (wallet_id, user_id))
        conn.commit()
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def seed_default_users():
    admin_exists = get_user_by_email("admin@sirkome.com")
    if not admin_exists:
        create_user_record(
            name="Admin User",
            email="admin@sirkome.com",
            password="admin1234",
            phone="+1-555-010-0001",
            nin="11111111111",
            bvn="22222222222",
            pin="1234",
            is_admin=1,
            balance=50000.0,
            account_number="SK-ADMIN",
        )

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

    alias_admin_exists = get_user_by_email("komeisioro+admin@gmail.com")
    if not alias_admin_exists:
        create_user_record(
            name="Admin User Alias",
            email="komeisioro+admin@gmail.com",
            password="admin1234",
            phone="+1-555-010-0001",
            nin="11111111111",
            bvn="22222222222",
            pin="1234",
            is_admin=1,
            balance=50000.0,
            account_number="SK-ADMIN-ALIAS",
        )

    alias_demo_exists = get_user_by_email("komeisioro+demo@gmail.com")
    if not alias_demo_exists:
        create_user_record(
            name="Kome Isioro Alias",
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


init_db()
ensure_user_columns()
ensure_wallets()
seed_default_users()


@app.get("/")
def home():
    return {"message": "SirKome Bank API Running"}


def build_user_profile(user):
    return {
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"],
        "account_number": user["account_number"],
        "balance": float(user["balance"]),
        "currency": user["currency"],
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

    token = create_access_token(user["id"])
    return build_auth_response(user, token)


@app.post("/auth/register", response_model=LoginResponse)
def register(payload: RegisterRequest):
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    nin = validate_identity_number(payload.nin, "NIN")
    bvn = validate_identity_number(payload.bvn, "BVN")
    pin = validate_pin(payload.pin or "1234")
    user = create_user_record(payload.name, payload.email, payload.password, payload.phone, nin, bvn, pin)
    token = create_access_token(user["id"])
    subject = "Welcome to SirKome Bank"
    body = f"Hello {user['name']},\n\nYour account {user['account_number']} has been created. Welcome to SirKome Bank.\n\nRegards,\nSirKome Team"
    notify_user_by_email(user["email"], subject, body)
    return build_auth_response(user, token)


@app.get("/accounts", response_model=list[AccountResponse])
def get_accounts(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    wallet = get_wallet_by_account(user["account_number"])
    balance = float(wallet["wallet_balance"] if wallet else user["balance"])

    return [{
        "account_number": user["account_number"],
        "balance": balance,
        "currency": user["currency"],
        "type": "Checking",
    }]


@app.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(credentials: HTTPAuthorizationCredentials | None = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE account_number = ? ORDER BY id DESC LIMIT 5",
            (user["account_number"],),
        ).fetchall()

    return [
        {
            "type": row["type"],
            "amount": float(row["amount"]),
            "description": row["description"],
            "date": row["date"],
        }
        for row in rows
    ]


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

    if payload.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero")

    if current_user["is_admin"] != 1 and sender["account_number"] != current_user["account_number"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only transfer from your own account")

    sender_wallet = get_wallet_by_account(sender["account_number"])
    receiver_wallet = get_wallet_by_account(receiver["account_number"])
    if not sender_wallet or not receiver_wallet:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Wallets are not available for this transfer")

    if sender_wallet["wallet_balance"] < payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

    with get_connection() as conn:
        conn.execute("UPDATE wallets SET wallet_balance = wallet_balance - ? WHERE account_number = ?", (payload.amount, sender["account_number"]))
        conn.execute("UPDATE wallets SET wallet_balance = wallet_balance + ? WHERE account_number = ?", (payload.amount, receiver["account_number"]))
        conn.execute("UPDATE users SET balance = (SELECT wallet_balance FROM wallets WHERE account_number = ?) WHERE account_number = ?", (sender["account_number"], sender["account_number"]))
        conn.execute("UPDATE users SET balance = (SELECT wallet_balance FROM wallets WHERE account_number = ?) WHERE account_number = ?", (receiver["account_number"], receiver["account_number"]))
        conn.commit()

    add_transaction(sender["account_number"], "debit", payload.amount, payload.description, receiver["account_number"])
    add_transaction(receiver["account_number"], "credit", payload.amount, payload.description, sender["account_number"])

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

    return {"status": "success", "message": "Transfer completed"}


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
        params.append(payload.name)
    if payload.phone:
        updates.append("phone = ?")
        params.append(payload.phone)
    if payload.email:
        updates.append("email = ?")
        params.append(payload.email)

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    params.append(user["id"])
    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()

    # send profile update notification
    try:
        send_email(user["email"], "Profile updated - SirKome Bank", f"Hello {payload.name or user['name']},\n\nYour profile was updated. If you did not perform this change, contact support immediately.")
    except Exception:
        pass

    return {"status": "success", "message": "Profile updated"}



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
    return {"sent": sent}
