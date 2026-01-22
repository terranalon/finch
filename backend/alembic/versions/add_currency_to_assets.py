"""add currency to assets

Revision ID: add_currency_to_assets
Revises: e9aca3dbb267
Create Date: 2026-01-07 15:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_currency_to_assets"
down_revision = "e9aca3dbb267"
branch_labels = None
depends_on = None


def upgrade():
    # Add currency column to assets table
    op.add_column("assets", sa.Column("currency", sa.String(length=3), nullable=True))

    # Set default currency to USD for existing assets
    op.execute("UPDATE assets SET currency = 'USD' WHERE currency IS NULL")

    # Make currency NOT NULL after setting defaults
    op.alter_column("assets", "currency", nullable=False)


def downgrade():
    op.drop_column("assets", "currency")
