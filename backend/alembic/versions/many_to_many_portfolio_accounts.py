"""Many-to-many portfolio-account relationship

Revision ID: many_to_many_portfolios
Revises: a1b2c3d4e5f6
Create Date: 2026-01-29

This migration:
1. Creates portfolio_accounts association table
2. Migrates existing data from accounts.portfolio_id to portfolio_accounts
3. Drops the old portfolio_id column and related constraints
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "many_to_many_portfolios"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create association table
    op.create_table(
        "portfolio_accounts",
        sa.Column("portfolio_id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("portfolio_id", "account_id"),
    )

    # 2. Migrate existing data from accounts.portfolio_id to portfolio_accounts
    op.execute(
        """
        INSERT INTO portfolio_accounts (portfolio_id, account_id)
        SELECT portfolio_id, id FROM accounts WHERE portfolio_id IS NOT NULL
        """
    )

    # 3. Drop old index on portfolio_id
    op.drop_index("idx_accounts_portfolio", table_name="accounts")

    # 4. Drop old foreign key constraint
    op.drop_constraint("fk_accounts_portfolio_id", "accounts", type_="foreignkey")

    # 5. Drop portfolio_id column
    op.drop_column("accounts", "portfolio_id")


def downgrade() -> None:
    # 1. Add back the portfolio_id column
    op.add_column("accounts", sa.Column("portfolio_id", sa.String(36), nullable=True))

    # 2. Migrate data back (takes first portfolio if account has multiple)
    op.execute(
        """
        UPDATE accounts SET portfolio_id = (
            SELECT portfolio_id FROM portfolio_accounts
            WHERE portfolio_accounts.account_id = accounts.id
            LIMIT 1
        )
        """
    )

    # 3. Add back the foreign key constraint
    op.create_foreign_key(
        "fk_accounts_portfolio_id",
        "accounts",
        "portfolios",
        ["portfolio_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4. Add back the index
    op.create_index("idx_accounts_portfolio", "accounts", ["portfolio_id"])

    # 5. Drop association table
    op.drop_table("portfolio_accounts")
