"""Add teller transaction metadata and customer branch scope.

Revision ID: 20260910_0004
Revises: 20260910_0003
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260910_0004"
down_revision: Union[str, Sequence[str], None] = "20260910_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("branch_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_branch_id",
        "users",
        "branches",
        ["branch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_branch_id", "users", ["branch_id"])

    op.add_column("transactions", sa.Column("transaction_reference", sa.String(length=40), nullable=True))
    op.add_column("transactions", sa.Column("status", sa.String(length=16), nullable=True))
    op.add_column("transactions", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("transactions", sa.Column("staff_user_id", sa.Integer(), nullable=True))
    op.add_column("transactions", sa.Column("branch_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_staff_user_id",
        "transactions",
        "users",
        ["staff_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_transactions_branch_id",
        "transactions",
        "branches",
        ["branch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("uq_transactions_reference", "transactions", ["transaction_reference"], unique=True, postgresql_where=sa.text("transaction_reference IS NOT NULL"))
    op.create_index("uq_transactions_idempotency_key", "transactions", ["idempotency_key"], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))
    op.create_index("ix_transactions_staff_user_id", "transactions", ["staff_user_id"])
    op.create_index("ix_transactions_branch_id", "transactions", ["branch_id"])
    op.create_index("ix_transactions_status", "transactions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_index("ix_transactions_branch_id", table_name="transactions")
    op.drop_index("ix_transactions_staff_user_id", table_name="transactions")
    op.drop_index("uq_transactions_idempotency_key", table_name="transactions")
    op.drop_index("uq_transactions_reference", table_name="transactions")
    op.drop_constraint("fk_transactions_branch_id", "transactions", type_="foreignkey")
    op.drop_constraint("fk_transactions_staff_user_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "branch_id")
    op.drop_column("transactions", "staff_user_id")
    op.drop_column("transactions", "idempotency_key")
    op.drop_column("transactions", "status")
    op.drop_column("transactions", "transaction_reference")
    op.drop_index("ix_users_branch_id", table_name="users")
    op.drop_constraint("fk_users_branch_id", "users", type_="foreignkey")
    op.drop_column("users", "branch_id")
