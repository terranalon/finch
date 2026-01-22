"""Increase fees field precision for crypto fees

Revision ID: increase_fees_precision
Revises: remove_entity_id_from_accounts
Create Date: 2026-01-22

This migration increases the precision of the fees column in transactions table
from Numeric(15, 2) to Numeric(20, 8) to support crypto withdrawal fees
which require 8 decimal places (e.g., 0.0005 BTC).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "increase_fees_precision"
down_revision = "add_service_account_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase fees column precision to 8 decimal places."""
    op.alter_column(
        "transactions",
        "fees",
        existing_type=sa.Numeric(precision=15, scale=2),
        type_=sa.Numeric(precision=20, scale=8),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert fees column to 2 decimal places."""
    op.alter_column(
        "transactions",
        "fees",
        existing_type=sa.Numeric(precision=20, scale=8),
        type_=sa.Numeric(precision=15, scale=2),
        existing_nullable=False,
    )
