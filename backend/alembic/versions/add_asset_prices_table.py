"""add asset prices table

Revision ID: add_asset_prices_table
Revises: add_currency_to_assets
Create Date: 2026-01-07 16:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_asset_prices_table"
down_revision = "add_currency_to_assets"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "asset_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "closing_price", sa.Numeric(15, 4), nullable=False, comment="End-of-day closing price"
        ),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("asset_id", "date", name="uq_asset_price_date"),
    )
    op.create_index("idx_asset_prices_asset_date", "asset_prices", ["asset_id", "date"])


def downgrade():
    op.drop_index("idx_asset_prices_asset_date", table_name="asset_prices")
    op.drop_table("asset_prices")
