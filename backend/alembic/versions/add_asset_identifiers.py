"""Add permanent identifiers to assets (CUSIP, ISIN, CONID, FIGI)

Revision ID: a1b2c3d4e5f7
Revises: f1b2c3d4e5f6
Create Date: 2026-01-10 06:50:00.000000

These identifiers don't change when ticker symbols change, enabling automatic
detection of ticker symbol changes (e.g., CEP -> XXI).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "f1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add permanent identifier fields to assets table."""
    # Add identifier columns
    op.add_column("assets", sa.Column("cusip", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("isin", sa.String(20), nullable=True))
    op.add_column("assets", sa.Column("conid", sa.String(50), nullable=True))
    op.add_column("assets", sa.Column("figi", sa.String(20), nullable=True))

    # Create indexes for fast lookups
    op.create_index("idx_assets_cusip", "assets", ["cusip"])
    op.create_index("idx_assets_isin", "assets", ["isin"])
    op.create_index("idx_assets_conid", "assets", ["conid"])


def downgrade() -> None:
    """Remove permanent identifier fields."""
    # Drop indexes
    op.drop_index("idx_assets_conid", table_name="assets")
    op.drop_index("idx_assets_isin", table_name="assets")
    op.drop_index("idx_assets_cusip", table_name="assets")

    # Drop columns
    op.drop_column("assets", "figi")
    op.drop_column("assets", "conid")
    op.drop_column("assets", "isin")
    op.drop_column("assets", "cusip")
