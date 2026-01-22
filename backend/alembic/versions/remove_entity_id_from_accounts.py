"""Remove entity_id from accounts table

Revision ID: remove_entity_id_from_accounts
Revises: migrate_entities_to_portfolios
Create Date: 2026-01-19

This migration:
1. Drops the entity_id column from accounts table
2. Drops the foreign key constraint and index
3. Converts user_preferences to use user_id instead of entity_id
4. Removes entities and user_preferences tables (no longer needed)

Note: Run migrate_entities_to_portfolios first to migrate data.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "remove_entity_id_from_accounts"
down_revision: str | None = "migrate_entities_to_portfolios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove entity_id from accounts and clean up legacy tables."""
    # 1. Drop foreign key constraint from accounts.entity_id
    op.drop_constraint("accounts_entity_id_fkey", "accounts", type_="foreignkey")

    # 2. Drop index on entity_id
    op.drop_index("idx_accounts_entity", table_name="accounts")

    # 3. Drop entity_id column from accounts
    op.drop_column("accounts", "entity_id")

    # 4. Drop user_preferences table (was linked to entities, not used)
    op.drop_table("user_preferences")

    # 5. Drop entities table (no longer needed)
    op.drop_table("entities")

    print("Removed entity_id from accounts and dropped legacy tables")


def downgrade() -> None:
    """Recreate entity tables and add entity_id back to accounts."""
    # 1. Recreate entities table
    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    # 2. Recreate user_preferences table
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "entity_id",
            sa.Integer(),
            sa.ForeignKey("entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_currency", sa.String(3), server_default="USD", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("entity_id", name="uq_user_preferences_entity"),
    )

    # 3. Add entity_id column back to accounts
    op.add_column("accounts", sa.Column("entity_id", sa.Integer(), nullable=True))

    # 4. Add foreign key constraint
    op.create_foreign_key(
        "accounts_entity_id_fkey",
        "accounts",
        "entities",
        ["entity_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Recreate index
    op.create_index("idx_accounts_entity", "accounts", ["entity_id"])

    print("Restored entity_id column and legacy tables")
