"""Add amount field to transactions for dividend support

Revision ID: f1b2c3d4e5f6
Revises: add_user_preferences
Create Date: 2026-01-09 06:50:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f1b2c3d4e5f6"
down_revision = "add_user_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add amount field for cash dividends and create index on type and date."""
    # Add amount column for dividend transactions
    op.add_column(
        "transactions", sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=True)
    )

    # Create composite index for faster dividend queries
    op.create_index("idx_transactions_type_date", "transactions", ["type", "date"])


def downgrade() -> None:
    """Remove amount field and index."""
    # Drop index
    op.drop_index("idx_transactions_type_date", table_name="transactions")

    # Drop column
    op.drop_column("transactions", "amount")
