"""
Run the existing `main.py` module-level initialization to ensure the
database and default users are created, then print the seeded users.

Usage:
    python backend/ensure_seed.py
"""
from pathlib import Path
import runpy
import sqlite3
import os
import sys


HERE = Path(__file__).parent
MAIN_PY = HERE / "main.py"
DB_PATH = HERE / "sirkome_bank.db"

if not MAIN_PY.exists():
    print("Error: main.py not found in backend/", file=sys.stderr)
    sys.exit(1)

print("Executing backend/main.py to initialize DB and seed users...")
# Running the module will execute module-level init (init_db/seed_default_users)
runpy.run_path(str(MAIN_PY), run_name="__main__")

if not DB_PATH.exists():
    print(f"Database file not found at {DB_PATH}", file=sys.stderr)
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT account_number, name, email, balance, is_admin FROM users WHERE account_number IN ('SK-ADMIN','SK-4821')",
).fetchall()

if not rows:
    print("No admin/demo users found after seeding.")
else:
    print("Seeded users:")
    for r in rows:
        print(f"- account_number={r['account_number']}, name={r['name']}, email={r['email']}, balance={r['balance']}, is_admin={r['is_admin']}")

conn.close()

print("Done.")
