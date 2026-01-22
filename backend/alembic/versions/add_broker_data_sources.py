"""Add broker data sources tracking

Revision ID: c2d3e4f5g6h7
Revises: b1c2d3e4f5g6
Create Date: 2026-01-11 15:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision = "c2d3e4f5g6h7"
down_revision = "b1c2d3e4f5g6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add broker data sources table and related columns."""
    # Create broker_data_sources table
    op.create_table(
        "broker_data_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("broker_type", sa.String(50), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_identifier", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("file_format", sa.String(10), nullable=True),
        sa.Column("import_stats", JSONB(), nullable=True),
        sa.Column("errors", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for broker_data_sources
    op.create_index(
        "idx_broker_sources_account_broker_dates",
        "broker_data_sources",
        ["account_id", "broker_type", "start_date", "end_date"],
    )
    op.create_index(
        "idx_broker_sources_file_hash", "broker_data_sources", ["file_hash", "account_id"]
    )
    op.create_index("idx_broker_sources_account", "broker_data_sources", ["account_id"])

    # Add broker_type column to accounts table
    op.add_column("accounts", sa.Column("broker_type", sa.String(50), nullable=True))

    # Add broker_source_id column to transactions table
    op.add_column(
        "transactions",
        sa.Column(
            "broker_source_id",
            sa.Integer(),
            sa.ForeignKey("broker_data_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("idx_transactions_broker_source", "transactions", ["broker_source_id"])


def downgrade() -> None:
    """Remove broker data sources tracking."""
    # Remove index and column from transactions
    op.drop_index("idx_transactions_broker_source", table_name="transactions")
    op.drop_column("transactions", "broker_source_id")

    # Remove column from accounts
    op.drop_column("accounts", "broker_type")

    # Remove indexes and table
    op.drop_index("idx_broker_sources_account", table_name="broker_data_sources")
    op.drop_index("idx_broker_sources_file_hash", table_name="broker_data_sources")
    op.drop_index("idx_broker_sources_account_broker_dates", table_name="broker_data_sources")
    op.drop_table("broker_data_sources")
