import sqlite3
from pathlib import Path


DB = Path(__file__).parent / "sirkome_bank.db"
if not DB.exists():
    print("Database file not found:", DB)
    raise SystemExit(1)

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

print("PRAGMA table_info(users):")
for r in conn.execute("PRAGMA table_info(users)").fetchall():
    print(dict(r))

print("\nUsers table rows:")
for r in conn.execute("SELECT id,user_id,account_number,name,email,password,pin_hash,is_admin FROM users").fetchall():
    print(dict(r))

conn.close()
