"""Runtime database adapter for the legacy raw-SQL business layer.

PostgreSQL is selected when DATABASE_URL is configured. The adapter preserves
main.py's existing positional-parameter SQL and sqlite3.Row-style access while
using SQLAlchemy sessions and transactions underneath.
"""
from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import create_postgres_engine


class CompatRow:
    def __init__(self, row: Any):
        self._mapping = row._mapping

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            return tuple(self._mapping.values())[key]
        return self._mapping[key]

    def keys(self):
        return self._mapping.keys()


class CompatResult:
    def __init__(self, result: Any):
        self._result = result
        self.lastrowid = None

    def fetchone(self):
        row = self._result.fetchone()
        return CompatRow(row) if row is not None else None

    def fetchall(self):
        return [CompatRow(row) for row in self._result.fetchall()]

    def __iter__(self) -> Iterator[CompatRow]:
        for row in self._result:
            yield CompatRow(row)

    @property
    def rowcount(self):
        return self._result.rowcount


_PARAMETER_PATTERN = re.compile(r"\?")


def _bind_positional(sql: str, params: Sequence[Any] | None):
    if not params:
        return text(sql), {}
    names = [f"p{index}" for index in range(len(params))]
    bound_sql = _PARAMETER_PATTERN.sub(lambda _: f":{names.pop(0)}", sql)
    return text(bound_sql), {f"p{index}": value for index, value in enumerate(params)}


class PostgresConnection:
    def __init__(self):
        self.session = Session(create_postgres_engine(), expire_on_commit=False)
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
        finally:
            self.session.close()
            self._closed = True
        return False

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        normalized = sql.strip().upper()
        if normalized == "BEGIN IMMEDIATE":
            # Serialize transfer critical sections without SQLite-specific syntax.
            result = self.session.execute(text("SELECT pg_advisory_xact_lock(9384721)"))
            return CompatResult(result)
        statement, bound = _bind_positional(sql, params)
        return CompatResult(self.session.execute(statement, bound))

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def close(self):
        self.session.close()
        self._closed = True
