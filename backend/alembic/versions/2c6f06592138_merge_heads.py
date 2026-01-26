"""merge_heads

Revision ID: 2c6f06592138
Revises: 2d16e9096e9a, increase_fees_precision
Create Date: 2026-01-24 06:28:38.163593

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '2c6f06592138'
down_revision: str | None = ('2d16e9096e9a', 'increase_fees_precision')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
