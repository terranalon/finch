"""Add portfolio preferences columns

Revision ID: add_portfolio_preferences
Revises: remove_entity_id_from_accounts
Create Date: 2026-01-19

This migration adds:
1. default_currency column to portfolios table (String(3), default "USD")
2. is_default column to portfolios table (Boolean, default False)
3. show_combined_view column to users table (Boolean, default True)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_portfolio_preferences"
down_revision: str | None = "remove_entity_id_from_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add preference columns to portfolios and users tables."""
    # Add default_currency column to portfolios
    op.add_column(
        "portfolios",
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="USD"),
    )

    # Add is_default column to portfolios
    op.add_column(
        "portfolios",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Add show_combined_view column to users
    op.add_column(
        "users",
        sa.Column("show_combined_view", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    """Remove preference columns from portfolios and users tables."""
    op.drop_column("users", "show_combined_view")
    op.drop_column("portfolios", "is_default")
    op.drop_column("portfolios", "default_currency")
