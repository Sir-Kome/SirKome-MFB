"""Safely import the live SQLite data into PostgreSQL.

This script is intentionally opt-in and is never called by main.py. Run
`alembic upgrade head` first, then invoke this script explicitly. It refuses
to import into a target containing data and never drops or truncates tables.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from sqlalchemy import inspect, select, text

from database import create_postgres_engine
from models_sqlalchemy import Base

TABLES = ("users", "transactions", "wallets", "transfer_requests", "notifications", "saved_accounts")
SEQUENCE_COLUMNS = {
    "users": "id",
    "transactions": "id",
    "notifications": "id",
    "saved_accounts": "id",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import the existing SQLite database into PostgreSQL safely.")
    parser.add_argument(
        "--sqlite-path",
        default=str(Path(__file__).with_name("sirkome_bank.db")),
        help="Path to the existing SQLite database (default: backend/sirkome_bank.db)",
    )
    return parser.parse_args()


def read_sqlite_rows(sqlite_path: Path) -> dict[str, list[dict[str, object]]]:
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")

    with sqlite3.connect(str(sqlite_path)) as connection:
        connection.row_factory = sqlite3.Row
        available = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        missing = set(TABLES) - available
        if missing:
            raise RuntimeError(f"SQLite database is missing expected tables: {', '.join(sorted(missing))}")
        return {
            table_name: [dict(row) for row in connection.execute(f'SELECT * FROM "{table_name}"')]
            for table_name in TABLES
        }


def ensure_empty_target(connection) -> None:
    inspector = inspect(connection)
    missing = set(TABLES) - set(inspector.get_table_names())
    if missing:
        raise RuntimeError(
            "PostgreSQL schema is incomplete. Run `alembic upgrade head` first; "
            f"missing tables: {', '.join(sorted(missing))}"
        )

    populated = []
    for table_name in TABLES:
        count = connection.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
        if count:
            populated.append(f"{table_name}={count}")
    if populated:
        raise RuntimeError(
            "Refusing to import into a non-empty PostgreSQL database: "
            + ", ".join(populated)
            + ". No data was changed."
        )


def reset_sequences(connection) -> None:
    for table_name, column_name in SEQUENCE_COLUMNS.items():
        sequence_name = connection.execute(
            text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
            {"table_name": table_name, "column_name": column_name},
        ).scalar_one_or_none()
        if sequence_name:
            connection.execute(
                text("SELECT setval(:sequence_name, COALESCE((SELECT MAX(id) FROM " + f'"{table_name}"' + "), 1), true)"),
                {"sequence_name": sequence_name},
            )


def import_rows(sqlite_rows: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    engine = create_postgres_engine()
    try:
        with engine.begin() as connection:
            ensure_empty_target(connection)
            for table_name in TABLES:
                rows = sqlite_rows[table_name]
                if rows:
                    connection.execute(Base.metadata.tables[table_name].insert(), rows)
            reset_sequences(connection)
            counts = {
                table_name: connection.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
                for table_name in TABLES
            }
            return counts
    finally:
        engine.dispose()


def main() -> None:
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).resolve()
    sqlite_rows = read_sqlite_rows(sqlite_path)
    source_counts = {table_name: len(rows) for table_name, rows in sqlite_rows.items()}
    print(f"Source SQLite: {sqlite_path}")
    print("Source row counts:")
    for table_name in TABLES:
        print(f"  {table_name}: {source_counts[table_name]}")

    target_counts = import_rows(sqlite_rows)
    print("PostgreSQL row counts after import:")
    for table_name in TABLES:
        print(f"  {table_name}: {target_counts[table_name]}")
        if target_counts[table_name] != source_counts[table_name]:
            raise RuntimeError(f"Row-count mismatch for {table_name}; review the transaction before retrying")
    print("Import completed with matching row counts.")


if __name__ == "__main__":
    main()
