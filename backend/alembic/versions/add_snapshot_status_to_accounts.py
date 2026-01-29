"""add_snapshot_status_to_accounts

Revision ID: a1b2c3d4e5f6
Revises: 9dfcd336c17e
Create Date: 2026-01-29 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9dfcd336c17e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add snapshot_status column to accounts table
    # Values: None, "generating", "ready", "failed"
    op.add_column(
        "accounts",
        sa.Column("snapshot_status", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "snapshot_status")
