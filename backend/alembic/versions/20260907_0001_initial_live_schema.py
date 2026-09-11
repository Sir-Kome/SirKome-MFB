"""Create the PostgreSQL schema matching the live SQLite tables.

Revision ID: 20260907_0001
Revises:
Create Date: 2026-09-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("date_of_birth", sa.String(), server_default="", nullable=False),
        sa.Column("gender", sa.String(), server_default="", nullable=False),
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("wallet_id", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), server_default="NGN", nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("token", sa.String(), nullable=True),
        sa.Column("nin", sa.String(), nullable=True),
        sa.Column("bvn", sa.String(), nullable=True),
        sa.Column("pin_hash", sa.String(), nullable=True),
        sa.Column("is_frozen", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("freeze_reason", sa.String(), server_default="", nullable=False),
        sa.Column("verification_tier", sa.Integer(), server_default="1", nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("proof_of_address_filename", sa.String(), nullable=True),
        sa.Column("proof_of_address_data", sa.Text(), nullable=True),
        sa.Column("proof_of_address_date", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("account_number"),
    )
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("related_account", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "wallets",
        sa.Column("wallet_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("wallet_balance", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(), server_default="NGN", nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("wallet_id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("account_number"),
    )
    op.create_table(
        "transfer_requests",
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("receipt_id", sa.String(), nullable=False),
        sa.Column("from_account", sa.String(), nullable=False),
        sa.Column("to_account", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("idempotency_key"),
        sa.UniqueConstraint("receipt_id"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "saved_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_number", sa.String(), nullable=False),
        sa.Column("account_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "account_number"),
    )


def downgrade() -> None:
    raise RuntimeError("Destructive downgrade is disabled for the initial live-schema migration")
