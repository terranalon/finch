"""add_ownership_transfer_fields

Revision ID: 9dfcd336c17e
Revises: 2c6f06592138
Create Date: 2026-01-24 06:28:41.080233

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9dfcd336c17e'
down_revision: str | None = '2c6f06592138'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add fields to transactions table
    op.add_column(
        "transactions",
        sa.Column("external_transaction_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        "idx_transactions_content_hash", "transactions", ["content_hash"]
    )

    # Add date_ranges to broker_data_sources
    op.add_column(
        "broker_data_sources",
        sa.Column("date_ranges", sa.dialects.postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("broker_data_sources", "date_ranges")
    op.drop_index("idx_transactions_content_hash", table_name="transactions")
    op.drop_column("transactions", "content_hash")
    op.drop_column("transactions", "external_transaction_id")
