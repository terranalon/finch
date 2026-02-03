"""Asset price data access layer."""

import logging
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import AssetPrice

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


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
        self, asset_ids: list[int], limit_per_asset: int = 2
    ) -> dict[int, list[AssetPrice]]:
        """Find latest prices for multiple assets.

        Returns a dict mapping asset_id to list of recent prices.
        Useful for calculating day change (need current + previous price).
        """
        if not asset_ids:
            return {}

        # Get the latest N prices for each asset using window function
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
            .filter(AssetPrice.asset_id.in_(asset_ids))
            .subquery()
        )

        prices = (
            self._db.query(AssetPrice)
            .join(subquery, AssetPrice.id == subquery.c.id)
            .filter(subquery.c.rn <= limit_per_asset)
            .order_by(AssetPrice.asset_id, desc(AssetPrice.date))
            .all()
        )

        # Group by asset_id
        result: dict[int, list[AssetPrice]] = {}
        for price in prices:
            if price.asset_id not in result:
                result[price.asset_id] = []
            result[price.asset_id].append(price)

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
