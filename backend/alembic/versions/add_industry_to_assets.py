"""add industry to assets

Revision ID: add_industry_to_assets
Revises: d4e5f6g7h8i9
Create Date: 2026-01-13 19:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_industry_to_assets"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade():
    # Add industry column to assets table (nullable, will be populated by update script)
    op.add_column("assets", sa.Column("industry", sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column("assets", "industry")
