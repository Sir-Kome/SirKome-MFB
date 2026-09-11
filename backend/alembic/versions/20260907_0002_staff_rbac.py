"""Add staff profiles for role-based access control.

Revision ID: 20260907_0002
Revises: 20260907_0001
Create Date: 2026-09-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_0002"
down_revision: Union[str, Sequence[str], None] = "20260907_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAFF_ROLES = (
    "SUPER_ADMIN",
    "ADMIN",
    "BRANCH_MANAGER",
    "TELLER",
    "ACCOUNT_OFFICER",
    "MARKETER",
)


def upgrade() -> None:
    op.create_table(
        "staff_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("staff_role", sa.String(length=32), nullable=False),
        sa.Column("branch_code", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.CheckConstraint(
            "staff_role IN ('SUPER_ADMIN', 'ADMIN', 'BRANCH_MANAGER', 'TELLER', 'ACCOUNT_OFFICER', 'MARKETER')",
            name="ck_staff_profiles_staff_role",
        ),
    )
    op.create_index("ix_staff_profiles_staff_role", "staff_profiles", ["staff_role"])
    op.create_index("ix_staff_profiles_branch_code", "staff_profiles", ["branch_code"])
    op.execute(
        sa.text(
            """
            INSERT INTO staff_profiles (user_id, staff_role)
            SELECT id, 'SUPER_ADMIN'
            FROM users
            WHERE is_admin IS TRUE
            ON CONFLICT (user_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_staff_profiles_branch_code", table_name="staff_profiles")
    op.drop_index("ix_staff_profiles_staff_role", table_name="staff_profiles")
    op.drop_table("staff_profiles")
