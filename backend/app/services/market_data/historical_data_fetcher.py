"""Historical data fetcher - orchestrates bulk price and rate fetching."""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.services.market_data.price_fetcher import PriceFetcher
from app.services.shared.currency_service import CurrencyService

logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """Orchestrates fetching of all historical data needed for snapshot generation."""

    @staticmethod
    def ensure_historical_data(
        db: Session,
        account_id: int,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Ensure historical prices and exchange rates exist for date range.

        Fetches:
        1. Prices for all non-cash assets in the account's holdings
        2. Exchange rates for all asset currencies to USD
        3. USD/ILS rate (always needed for ILS conversion)

        Args:
            db: Database session
            account_id: Account to fetch data for
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Stats dict with prices_fetched, rates_fetched counts
        """
        from app.models import Asset, Holding

        stats = {
            "account_id": account_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "prices_fetched": 0,
            "rates_fetched": 0,
            "assets_processed": 0,
            "errors": [],
        }

        # Get all active holdings for this account
        holdings = (
            db.query(Holding, Asset)
            .join(Asset)
            .filter(Holding.account_id == account_id, Holding.is_active == True)  # noqa: E712
            .all()
        )

        currencies_needed = set()

        # Fetch prices for non-cash assets
        for holding, asset in holdings:
            if asset.asset_class == "Cash":
                continue

            currencies_needed.add(asset.currency)

            try:
                count = PriceFetcher.fetch_and_store_historical_prices(
                    db, asset.id, start_date, end_date
                )
                stats["prices_fetched"] += count
                stats["assets_processed"] += 1
            except Exception as e:
                logger.error(f"Failed to fetch prices for {asset.symbol}: {e}")
                stats["errors"].append(f"Price fetch failed for {asset.symbol}: {e}")

        # Fetch exchange rates for all needed currency pairs
        # Always need USD/ILS for final conversion
        currencies_needed.add("USD")
        rate_pairs = []

        for currency in currencies_needed:
            if currency != "USD":
                rate_pairs.append((currency, "USD"))

        rate_pairs.append(("USD", "ILS"))

        for from_curr, to_curr in rate_pairs:
            try:
                count = CurrencyService.fetch_and_store_historical_rates(
                    db, from_curr, to_curr, start_date, end_date
                )
                stats["rates_fetched"] += count
            except Exception as e:
                logger.error(f"Failed to fetch rates for {from_curr}/{to_curr}: {e}")
                stats["errors"].append(f"Rate fetch failed for {from_curr}/{to_curr}: {e}")

        logger.info(
            f"Historical data fetch complete for account {account_id}: "
            f"{stats['prices_fetched']} prices, {stats['rates_fetched']} rates"
        )

        return stats
