"""Delete legacy forex rows so re-import creates single-row format

Revision ID: consolidate_legacy_forex_pairs
Revises: rename_sector_to_category
Create Date: 2026-02-15

Legacy IBKR forex imports created TWO transaction rows per conversion
(to_holding_id IS NULL). The new import_service creates ONE row with
to_holding_id set. This migration deletes all legacy rows; the next
broker import recreates them in the correct format.
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "consolidate_legacy_forex_pairs"
down_revision: str | None = "rename_sector_to_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        text("""
            DELETE FROM transactions
            WHERE type = 'Forex Conversion'
              AND to_holding_id IS NULL
        """)
    )
    print(f"Deleted {result.rowcount} legacy forex rows (re-import to recreate)")


def downgrade() -> None:
    print("Cannot restore deleted legacy forex rows; re-import from broker to recreate")
