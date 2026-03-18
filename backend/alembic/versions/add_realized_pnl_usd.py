"""add realized_pnl_usd to transactions

Revision ID: add_realized_pnl_usd
Revises: cff8cd6baaf6
Create Date: 2026-03-09 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_realized_pnl_usd"
down_revision = "cff8cd6baaf6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("transactions", sa.Column("realized_pnl_usd", sa.Numeric(15, 2), nullable=True))


def downgrade():
    op.drop_column("transactions", "realized_pnl_usd")
