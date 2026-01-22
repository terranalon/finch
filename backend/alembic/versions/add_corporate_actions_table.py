"""Add corporate actions table

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f7
Create Date: 2026-01-10 10:03:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5g6"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add corporate actions table for tracking symbol changes, mergers, splits."""
    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "action_type", sa.String(50), nullable=False
        ),  # 'SYMBOL_CHANGE', 'SPAC_MERGER', 'SPLIT', 'MERGER', 'SPINOFF'
        sa.Column("old_asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("new_asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("ratio", sa.Numeric(15, 8), nullable=True),  # For splits: 2.0 for 2:1 split
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_corporate_actions_old_asset", "corporate_actions", ["old_asset_id"])
    op.create_index("idx_corporate_actions_new_asset", "corporate_actions", ["new_asset_id"])
    op.create_index("idx_corporate_actions_type", "corporate_actions", ["action_type"])
    op.create_index("idx_corporate_actions_date", "corporate_actions", ["effective_date"])


def downgrade() -> None:
    """Remove corporate actions table."""
    op.drop_index("idx_corporate_actions_date", table_name="corporate_actions")
    op.drop_index("idx_corporate_actions_type", table_name="corporate_actions")
    op.drop_index("idx_corporate_actions_new_asset", table_name="corporate_actions")
    op.drop_index("idx_corporate_actions_old_asset", table_name="corporate_actions")
    op.drop_table("corporate_actions")
