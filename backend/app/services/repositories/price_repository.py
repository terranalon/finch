"""Asset price data access layer."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import AssetPrice
from app.models.asset_daily_metrics import AssetDailyMetrics

if TYPE_CHECKING:
    from collections.abc import Sequence


class PriceRepository:
    """Centralized asset price data access.

    Naming conventions:
    - find_* : Query that may return None or empty list
    - get_* : Query that raises exception if missing
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_latest_by_asset(self, asset_id: int) -> AssetPrice | None:
        """Find the most recent price for an asset."""
        return (
            self._db.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset_id)
            .order_by(desc(AssetPrice.date))
            .first()
        )

    def find_by_asset_and_date(self, asset_id: int, target_date: date) -> AssetPrice | None:
        """Find price for a specific asset and date."""
        return (
            self._db.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset_id, AssetPrice.date == target_date)
            .first()
        )

    def find_latest_by_assets(
        self,
        asset_ids: list[int],
        limit_per_asset: int = 2,
        *,
        before_date: date | None = None,
    ) -> dict[int, list[AssetPrice]]:
        """Find latest prices for multiple assets.

        Returns a dict mapping asset_id to list of recent prices (newest first).
        If before_date is set, only prices strictly before that date are considered.
        """
        if not asset_ids:
            return {}

        base_filter = [AssetPrice.asset_id.in_(asset_ids)]
        if before_date is not None:
            base_filter.append(AssetPrice.date < before_date)

        subquery = (
            self._db.query(
                AssetPrice,
                func.row_number()
                .over(
                    partition_by=AssetPrice.asset_id,
                    order_by=desc(AssetPrice.date),
                )
                .label("rn"),
            )
            .filter(*base_filter)
            .subquery()
        )

        prices = (
            self._db.query(AssetPrice)
            .join(subquery, AssetPrice.id == subquery.c.id)
            .filter(subquery.c.rn <= limit_per_asset)
            .order_by(AssetPrice.asset_id, desc(AssetPrice.date))
            .all()
        )

        result: dict[int, list[AssetPrice]] = {}
        for price in prices:
            result.setdefault(price.asset_id, []).append(price)

        return result

    def find_price_history(
        self,
        asset_id: int,
        start_date: date,
        end_date: date,
    ) -> "Sequence[AssetPrice]":
        """Find price history for an asset within a date range."""
        return (
            self._db.query(AssetPrice)
            .filter(
                AssetPrice.asset_id == asset_id,
                AssetPrice.date >= start_date,
                AssetPrice.date <= end_date,
            )
            .order_by(AssetPrice.date)
            .all()
        )

    def find_previous_close(self, asset_id: int, before_date: date) -> AssetPrice | None:
        """Find the most recent price before a given date."""
        return (
            self._db.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset_id, AssetPrice.date < before_date)
            .order_by(desc(AssetPrice.date))
            .first()
        )

    def find_previous_closes(
        self, asset_ids: list[int], before_date: date
    ) -> dict[int, AssetPrice]:
        """Find the most recent price before a given date for multiple assets.

        Returns a dict mapping asset_id -> AssetPrice (most recent before before_date).
        """
        by_asset = self.find_latest_by_assets(asset_ids, limit_per_asset=1, before_date=before_date)
        return {aid: prices[0] for aid, prices in by_asset.items()}

    def find_latest_market_caps(self, asset_ids: list[int]) -> dict[int, Decimal]:
        """Find the latest market cap for each asset from asset_daily_metrics."""
        if not asset_ids:
            return {}

        latest_sq = (
            self._db.query(
                AssetDailyMetrics.asset_id,
                func.max(AssetDailyMetrics.date).label("max_date"),
            )
            .filter(
                AssetDailyMetrics.asset_id.in_(asset_ids),
                AssetDailyMetrics.market_cap.isnot(None),
            )
            .group_by(AssetDailyMetrics.asset_id)
            .subquery()
        )

        rows = (
            self._db.query(AssetDailyMetrics.asset_id, AssetDailyMetrics.market_cap)
            .join(
                latest_sq,
                (AssetDailyMetrics.asset_id == latest_sq.c.asset_id)
                & (AssetDailyMetrics.date == latest_sq.c.max_date),
            )
            .all()
        )

        return {aid: Decimal(str(mc)) for aid, mc in rows if mc is not None}
