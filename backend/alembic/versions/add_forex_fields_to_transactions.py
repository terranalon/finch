"""Add forex fields to transactions for single-record forex conversions

Revision ID: d4e5f6g7h8i9
Revises: 5054502cdf05
Create Date: 2026-01-13 14:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6g7h8i9"
down_revision = "5054502cdf05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add forex-specific fields: to_holding_id, to_amount, exchange_rate."""
    # Add to_holding_id for destination currency holding
    op.add_column("transactions", sa.Column("to_holding_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_transactions_to_holding",
        "transactions",
        "holdings",
        ["to_holding_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add to_amount for amount received in forex conversion
    op.add_column(
        "transactions", sa.Column("to_amount", sa.Numeric(precision=15, scale=2), nullable=True)
    )

    # Add exchange_rate for forex conversion rate
    op.add_column(
        "transactions", sa.Column("exchange_rate", sa.Numeric(precision=12, scale=6), nullable=True)
    )


def downgrade() -> None:
    """Remove forex-specific fields."""
    op.drop_constraint("fk_transactions_to_holding", "transactions", type_="foreignkey")
    op.drop_column("transactions", "exchange_rate")
    op.drop_column("transactions", "to_amount")
    op.drop_column("transactions", "to_holding_id")
