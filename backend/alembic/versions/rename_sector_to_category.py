"""rename sector to category

Revision ID: rename_sector_to_category
Revises: add_industry_to_assets
Create Date: 2026-01-13 20:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "rename_sector_to_category"
down_revision = "add_industry_to_assets"
branch_labels = None
depends_on = None


def upgrade():
    # Rename sector column to category
    op.alter_column("assets", "sector", new_column_name="category")


def downgrade():
    # Rename category column back to sector
    op.alter_column("assets", "category", new_column_name="sector")
