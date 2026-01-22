"""Add TASE securities table and tase_security_number to assets

Revision ID: d4e5f6g7h8i9
Revises: 5054502cdf05
Create Date: 2026-01-14

This migration adds:
1. tase_securities table for caching Israeli securities data from TASE API
2. tase_security_number field to assets table for Israeli security mapping
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_tase_securities"
down_revision: str | None = "rename_sector_to_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create tase_securities table for caching TASE API data
    op.create_table(
        "tase_securities",
        sa.Column("security_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=True),
        sa.Column("yahoo_symbol", sa.String(length=50), nullable=True),
        sa.Column("isin", sa.String(length=20), nullable=True),
        sa.Column("security_name", sa.String(length=200), nullable=True),
        sa.Column("security_name_en", sa.String(length=200), nullable=True),
        sa.Column("security_type_code", sa.String(length=10), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("company_sector", sa.String(length=100), nullable=True),
        sa.Column("company_sub_sector", sa.String(length=100), nullable=True),
        sa.Column(
            "last_synced_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("security_id"),
    )
    op.create_index(
        "idx_tase_securities_symbol", "tase_securities", ["symbol"], unique=False
    )
    op.create_index(
        "idx_tase_securities_isin", "tase_securities", ["isin"], unique=False
    )
    op.create_index(
        "idx_tase_securities_type_code",
        "tase_securities",
        ["security_type_code"],
        unique=False,
    )

    # Add tase_security_number to assets table
    op.add_column(
        "assets", sa.Column("tase_security_number", sa.String(length=20), nullable=True)
    )
    op.create_index(
        "idx_assets_tase_security_number",
        "assets",
        ["tase_security_number"],
        unique=False,
    )


def downgrade() -> None:
    # Remove tase_security_number from assets
    op.drop_index("idx_assets_tase_security_number", table_name="assets")
    op.drop_column("assets", "tase_security_number")

    # Drop tase_securities table
    op.drop_index("idx_tase_securities_type_code", table_name="tase_securities")
    op.drop_index("idx_tase_securities_isin", table_name="tase_securities")
    op.drop_index("idx_tase_securities_symbol", table_name="tase_securities")
    op.drop_table("tase_securities")
