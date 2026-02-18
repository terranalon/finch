"""Service for populating asset daily metrics and slow-changing asset fields."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import Asset
from app.models.asset_daily_metrics import AssetDailyMetrics

logger = logging.getLogger(__name__)

_SLOW_CHANGING_FIELDS = frozenset({
    "description", "exchange", "website", "ceo", "employees",
    "beta", "avg_volume", "earnings_date", "ex_dividend_date",
    "target_est", "week_52_high", "week_52_low", "peg_ratio",
    "expense_ratio", "fund_family", "nav",
    "max_supply", "ath", "ath_date", "atl", "atl_date",
})


class AssetMetricsService:
    """Handles upsert of daily metrics and slow-changing asset field updates."""

    @staticmethod
    def upsert_daily_metrics(
        db: Session,
        asset_id: int,
        target_date: date,
        *,
        open: Decimal | None = None,
        high: Decimal | None = None,
        low: Decimal | None = None,
        close: Decimal | None = None,
        volume: int | None = None,
        market_cap: Decimal | None = None,
        pe_ratio: Decimal | None = None,
        forward_pe: Decimal | None = None,
        eps: Decimal | None = None,
        dividend_rate: Decimal | None = None,
        dividend_yield: Decimal | None = None,
        payout_ratio: Decimal | None = None,
        circulating_supply: Decimal | None = None,
        market_cap_rank: int | None = None,
        dominance: Decimal | None = None,
        source: str | None = None,
    ) -> None:
        """Upsert today's row in asset_daily_metrics.

        Uses INSERT ... ON CONFLICT (asset_id, date) DO UPDATE so that
        repeated intraday runs update the same row without duplicates.
        """
        values = {
            "asset_id": asset_id,
            "date": target_date,
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "forward_pe": forward_pe,
            "eps": eps,
            "dividend_rate": dividend_rate,
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "circulating_supply": circulating_supply,
            "market_cap_rank": market_cap_rank,
            "dominance": dominance,
            "source": source,
        }

        update_fields = {k: v for k, v in values.items() if k not in ("asset_id", "date")}

        stmt = pg_insert(AssetDailyMetrics).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_asset_daily_metrics_asset_date",
            set_=update_fields,
        )
        db.execute(stmt)
        db.commit()

    @staticmethod
    def update_slow_changing_fields(
        db: Session,
        asset: Asset,
        **fields: object,
    ) -> bool:
        """Update slow-changing fields on Asset only if values differ.

        Compares each provided field against the current value in memory.
        Only issues a commit if at least one field actually changed.
        None values are skipped (won't overwrite existing data).

        Returns:
            True if any field was changed, False otherwise
        """
        changed = False
        for field_name, new_value in fields.items():
            if field_name not in _SLOW_CHANGING_FIELDS:
                logger.warning("Ignoring unknown slow-changing field: %s", field_name)
                continue
            if new_value is None:
                continue
            current_value = getattr(asset, field_name)
            if current_value != new_value:
                setattr(asset, field_name, new_value)
                changed = True

        if changed:
            db.commit()
            logger.debug("Updated slow-changing fields for asset %s", asset.symbol)

        return changed
