"""merge auth upgrade and service account

Revision ID: 2d16e9096e9a
Revises: add_auth_upgrade_tables, add_service_account_flag
Create Date: 2026-01-22 17:56:48.872827

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '2d16e9096e9a'
down_revision: str | None = ('add_auth_upgrade_tables', 'add_service_account_flag')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
