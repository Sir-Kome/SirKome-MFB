"""Add branch management and staff lifecycle fields.

Revision ID: 20260910_0003
Revises: 20260907_0002
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260910_0003"
down_revision: Union[str, Sequence[str], None] = "20260907_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


STAFF_ROLE_CHECK = "staff_role IN ('SUPER_ADMIN', 'ADMIN', 'BRANCH_MANAGER', 'TELLER', 'ACCOUNT_OFFICER', 'MARKETER')"


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("branch_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_code"),
    )
    op.create_index("ix_branches_name", "branches", ["name"])
    op.create_index("ix_branches_is_active", "branches", ["is_active"])

    op.add_column("staff_profiles", sa.Column("branch_id", sa.Integer(), nullable=True))
    op.add_column("staff_profiles", sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("staff_profiles", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.add_column("staff_profiles", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_foreign_key(
        "fk_staff_profiles_branch_id",
        "staff_profiles",
        "branches",
        ["branch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_staff_profiles_branch_id", "staff_profiles", ["branch_id"])
    op.create_index("ix_staff_profiles_is_active", "staff_profiles", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_staff_profiles_is_active", table_name="staff_profiles")
    op.drop_index("ix_staff_profiles_branch_id", table_name="staff_profiles")
    op.drop_constraint("fk_staff_profiles_branch_id", "staff_profiles", type_="foreignkey")
    op.drop_column("staff_profiles", "updated_at")
    op.drop_column("staff_profiles", "created_at")
    op.drop_column("staff_profiles", "is_active")
    op.drop_column("staff_profiles", "branch_id")
    op.drop_index("ix_branches_is_active", table_name="branches")
    op.drop_index("ix_branches_name", table_name="branches")
    op.drop_table("branches")
