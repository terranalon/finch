"""merge heads for asset detail

Revision ID: 6d6fbe4baf41
Revises: b2c3d4e5f6a7, consolidate_legacy_forex_pairs
Create Date: 2026-02-18 09:18:22.313808

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "6d6fbe4baf41"
down_revision: str | None = ("b2c3d4e5f6a7", "consolidate_legacy_forex_pairs")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
