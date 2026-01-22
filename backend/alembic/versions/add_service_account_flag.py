"""Add is_service_account flag to users table

Revision ID: add_service_account_flag
Revises: increase_currency_column_length
Create Date: 2026-01-21

Adds is_service_account boolean field to distinguish service accounts
(like Airflow) from regular user accounts.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "add_service_account_flag"
down_revision: str | None = "increase_currency_column_length"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_service_account column with default False."""
    op.add_column(
        "users",
        sa.Column("is_service_account", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove is_service_account column."""
    op.drop_column("users", "is_service_account")
