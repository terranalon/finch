"""Increase currency column length for crypto symbols

Revision ID: increase_currency_column_length
Revises: add_portfolio_preferences
Create Date: 2026-01-21

Crypto symbols like BABY, SHIB, AVAX can exceed 3 characters.
Increase assets.currency from VARCHAR(3) to VARCHAR(10).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "increase_currency_column_length"
down_revision: str | None = "add_portfolio_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Increase currency column from VARCHAR(3) to VARCHAR(10)."""
    op.alter_column(
        "assets",
        "currency",
        type_=sa.String(length=10),
        existing_type=sa.String(length=3),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert currency column back to VARCHAR(3)."""
    op.alter_column(
        "assets",
        "currency",
        type_=sa.String(length=3),
        existing_type=sa.String(length=10),
        existing_nullable=False,
    )
