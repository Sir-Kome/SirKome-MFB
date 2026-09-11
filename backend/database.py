"""PostgreSQL foundation for the existing SQLite-backed application.

The current FastAPI runtime still uses backend/main.py and SQLite. This module
is intentionally isolated until the PostgreSQL migration is reviewed.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for PostgreSQL operations")
    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("DATABASE_URL must use the postgresql+psycopg:// scheme")
    return database_url


def create_postgres_engine() -> Engine:
    return create_engine(get_database_url(), future=True, pool_pre_ping=True)
