"""add asset detail columns and asset_daily_metrics table

Revision ID: cff8cd6baaf6
Revises: 6d6fbe4baf41
Create Date: 2026-02-18 09:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cff8cd6baaf6"
down_revision: Union[str, None] = "6d6fbe4baf41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- New columns on assets table --
    # About / static
    op.add_column("assets", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("assets", sa.Column("exchange", sa.String(50), nullable=True))
    op.add_column("assets", sa.Column("website", sa.String(255), nullable=True))
    op.add_column("assets", sa.Column("ceo", sa.String(100), nullable=True))
    op.add_column("assets", sa.Column("employees", sa.Integer(), nullable=True))

    # Slow-changing stats (stocks)
    op.add_column("assets", sa.Column("beta", sa.Numeric(8, 4), nullable=True))
    op.add_column("assets", sa.Column("avg_volume", sa.BigInteger(), nullable=True))
    op.add_column("assets", sa.Column("earnings_date", sa.Date(), nullable=True))
    op.add_column("assets", sa.Column("ex_dividend_date", sa.Date(), nullable=True))
    op.add_column("assets", sa.Column("target_est", sa.Numeric(15, 4), nullable=True))
    op.add_column("assets", sa.Column("week_52_high", sa.Numeric(15, 4), nullable=True))
    op.add_column("assets", sa.Column("week_52_low", sa.Numeric(15, 4), nullable=True))
    op.add_column("assets", sa.Column("peg_ratio", sa.Numeric(10, 4), nullable=True))

    # ETF-specific
    op.add_column("assets", sa.Column("expense_ratio", sa.Numeric(8, 6), nullable=True))
    op.add_column("assets", sa.Column("fund_family", sa.String(100), nullable=True))
    op.add_column("assets", sa.Column("nav", sa.Numeric(15, 4), nullable=True))

    # Crypto slow-changing
    op.add_column("assets", sa.Column("max_supply", sa.Numeric(20, 4), nullable=True))
    op.add_column("assets", sa.Column("ath", sa.Numeric(20, 4), nullable=True))
    op.add_column("assets", sa.Column("ath_date", sa.Date(), nullable=True))
    op.add_column("assets", sa.Column("atl", sa.Numeric(20, 4), nullable=True))
    op.add_column("assets", sa.Column("atl_date", sa.Date(), nullable=True))

    # -- New asset_daily_metrics table --
    op.create_table(
        "asset_daily_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        # OHLCV
        sa.Column("open", sa.Numeric(15, 4), nullable=True),
        sa.Column("high", sa.Numeric(15, 4), nullable=True),
        sa.Column("low", sa.Numeric(15, 4), nullable=True),
        sa.Column("close", sa.Numeric(15, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        # Daily-changing fundamentals
        sa.Column("market_cap", sa.Numeric(20, 2), nullable=True),
        sa.Column("pe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("forward_pe", sa.Numeric(10, 4), nullable=True),
        sa.Column("eps", sa.Numeric(10, 4), nullable=True),
        sa.Column("dividend_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(8, 6), nullable=True),
        sa.Column("payout_ratio", sa.Numeric(8, 4), nullable=True),
        # Crypto daily
        sa.Column("circulating_supply", sa.Numeric(20, 4), nullable=True),
        sa.Column("market_cap_rank", sa.Integer(), nullable=True),
        sa.Column("dominance", sa.Numeric(8, 4), nullable=True),
        # Meta
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_asset_daily_metrics_asset_date", "asset_daily_metrics", ["asset_id", "date"]
    )
    op.create_index(
        "idx_asset_daily_metrics_asset_date", "asset_daily_metrics", ["asset_id", "date"]
    )


def downgrade() -> None:
    # Drop table
    op.drop_index("idx_asset_daily_metrics_asset_date", table_name="asset_daily_metrics")
    op.drop_constraint("uq_asset_daily_metrics_asset_date", "asset_daily_metrics", type_="unique")
    op.drop_table("asset_daily_metrics")

    # Drop columns from assets (reverse order)
    op.drop_column("assets", "atl_date")
    op.drop_column("assets", "atl")
    op.drop_column("assets", "ath_date")
    op.drop_column("assets", "ath")
    op.drop_column("assets", "max_supply")
    op.drop_column("assets", "nav")
    op.drop_column("assets", "fund_family")
    op.drop_column("assets", "expense_ratio")
    op.drop_column("assets", "peg_ratio")
    op.drop_column("assets", "week_52_low")
    op.drop_column("assets", "week_52_high")
    op.drop_column("assets", "target_est")
    op.drop_column("assets", "ex_dividend_date")
    op.drop_column("assets", "earnings_date")
    op.drop_column("assets", "avg_volume")
    op.drop_column("assets", "beta")
    op.drop_column("assets", "employees")
    op.drop_column("assets", "ceo")
    op.drop_column("assets", "website")
    op.drop_column("assets", "exchange")
    op.drop_column("assets", "description")
