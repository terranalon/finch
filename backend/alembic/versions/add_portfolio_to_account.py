"""Add portfolio_id to accounts table

Revision ID: add_portfolio_to_account
Revises: add_auth_tables
Create Date: 2026-01-18

This migration adds:
1. portfolio_id column to accounts table (nullable for existing data)
2. Foreign key constraint to portfolios table
3. Index for portfolio_id
4. Makes entity_id nullable (was required before)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_portfolio_to_account"
down_revision: str | None = "add_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add portfolio_id column (nullable for existing data)
    op.add_column(
        "accounts",
        sa.Column("portfolio_id", sa.String(36), nullable=True),
    )
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_accounts_portfolio_id",
        "accounts",
        "portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="CASCADE",
    )
    # Add index for performance
    op.create_index("idx_accounts_portfolio", "accounts", ["portfolio_id"])
    # Make entity_id nullable (was required before)
    op.alter_column("accounts", "entity_id", nullable=True)


def downgrade() -> None:
    op.drop_index("idx_accounts_portfolio", table_name="accounts")
    op.drop_constraint("fk_accounts_portfolio_id", "accounts", type_="foreignkey")
    op.drop_column("accounts", "portfolio_id")
    op.alter_column("accounts", "entity_id", nullable=False)
