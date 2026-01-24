"""merge_heads

Revision ID: 2c6f06592138
Revises: 2d16e9096e9a, increase_fees_precision
Create Date: 2026-01-24 06:28:38.163593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c6f06592138'
down_revision: Union[str, None] = ('2d16e9096e9a', 'increase_fees_precision')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass