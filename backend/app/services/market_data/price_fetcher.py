"""Price fetching service for asset prices."""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset
from app.models.asset_price import AssetPrice
from app.services.asset_metrics_service import AssetMetricsService
from app.services.market_data.coingecko_client import CoinGeckoClient
from app.services.market_data.cryptocompare_client import CryptoCompareClient
from app.services.market_data.yfinance_client import TickerMarketData, YFinanceClient

logger = logging.getLogger(__name__)

# Israeli stocks (.TA) prices from Yahoo Finance are in Agorot (1/100 ILS)
_AGOROT_DIVISOR = Decimal("100")

# Minimum age in seconds before re-fetching a price via the manual refresh endpoint
MANUAL_REFRESH_COOLDOWN_SECONDS = 60


def _apply_agorot(v: Decimal | None, divisor: Decimal | None) -> Decimal | None:
    """Divide v by divisor when both are non-None (Agorot → ILS conversion)."""
    return v / divisor if divisor is not None and v is not None else v


# Lazy-loaded CoinGecko client (singleton)
_coingecko_client: CoinGeckoClient | None = None


def _get_coingecko_client() -> CoinGeckoClient:
    """Get or create the CoinGecko client singleton."""
    global _coingecko_client
    if _coingecko_client is None:
        _coingecko_client = CoinGeckoClient()
    return _coingecko_client


class PriceFetcher:
    """Service for fetching and updating asset prices from external sources."""

    @staticmethod
    def _fetch_price_for_asset(asset: Asset) -> tuple[Decimal, datetime] | None:
        """
        Fetch current price for an asset, routing to the appropriate data source.

        Crypto assets use CoinGecko, all others use Yahoo Finance.

        Args:
            asset: Asset model instance

        Returns:
            Tuple of (price, timestamp) or None if fetch failed
        """
        if asset.asset_class == "Crypto":
            return PriceFetcher.fetch_crypto_price(asset.symbol, "usd")
        return PriceFetcher.fetch_price(asset.symbol)

    @staticmethod
    def fetch_price(symbol: str) -> tuple[Decimal, datetime] | None:
        """
        Fetch current price for a single symbol from Yahoo Finance.

        Args:
            symbol: The ticker symbol (e.g., 'AAPL', 'BTC-USD')

        Returns:
            Tuple of (price, timestamp) or None if fetch failed
        """
        try:
            result = YFinanceClient().get_current_price(symbol)
            if result is None:
                logger.warning(f"No valid price found for {symbol}")
                return None

            price, timestamp = result

            # Convert Israeli stocks from Agorot to ILS
            if symbol.endswith(".TA"):
                price = price / _AGOROT_DIVISOR
                logger.debug(f"Converted {symbol} price from Agorot to ILS: {price}")

            return price, timestamp

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    @staticmethod
    def fetch_prices_batch(symbols: list[str]) -> dict[str, tuple[Decimal, datetime]]:
        """Fetch prices for multiple symbols using batch API.

        Args:
            symbols: List of ticker symbols

        Returns:
            Dictionary mapping symbol to (price, timestamp) tuples
        """
        if not symbols:
            return {}
        client = YFinanceClient()
        batch_results = client.get_batch_prices_threaded(symbols)
        now = datetime.now()
        return {
            symbol: (
                row.close / _AGOROT_DIVISOR if symbol.endswith(".TA") else row.close,
                now,
            )
            for symbol, row in batch_results.items()
            if row is not None
        }

    @staticmethod
    def fetch_crypto_price(
        symbol: str, vs_currency: str = "usd"
    ) -> tuple[Decimal, datetime] | None:
        """
        Fetch current price for a cryptocurrency from CoinGecko.

        Args:
            symbol: The crypto symbol (e.g., 'BTC', 'ETH')
            vs_currency: Quote currency (default: 'usd')

        Returns:
            Tuple of (price, timestamp) or None if fetch failed
        """
        try:
            client = _get_coingecko_client()
            price = client.get_current_price(symbol, vs_currency)

            if price and price > 0:
                logger.info(
                    f"Fetched crypto price for {symbol} from CoinGecko: {price} {vs_currency.upper()}"
                )
                return price, datetime.now()

            logger.warning(f"No valid crypto price found for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error fetching crypto price for {symbol}: {str(e)}")
            return None

    @staticmethod
    def update_asset_price(db: Session, asset: Asset) -> bool:
        """
        Update price for a single asset in the database.

        Args:
            db: Database session
            asset: Asset model instance

        Returns:
            True if update was successful, False otherwise
        """
        try:
            result = PriceFetcher._fetch_price_for_asset(asset)
            if result:
                price, timestamp = result
                asset.last_fetched_price = price
                asset.last_fetched_at = timestamp
                db.commit()
                logger.info(f"Updated price for {asset.symbol}: {price}")
                return True

            logger.warning(f"Failed to fetch price for {asset.symbol}")
            return False

        except Exception as e:
            logger.error(f"Error updating price for {asset.symbol}: {str(e)}")
            db.rollback()
            return False

    @staticmethod
    def _write_stock_metrics(
        db: Session,
        asset: Asset,
        data: TickerMarketData,
        today: date,
        price: Decimal | None,
        divisor: Decimal | None,
    ) -> None:
        """Upsert daily metrics and slow-changing fields for a single stock asset."""
        try:
            AssetMetricsService.upsert_daily_metrics(
                db,
                asset_id=asset.id,
                target_date=today,
                open=_apply_agorot(data.open, divisor),
                high=_apply_agorot(data.high, divisor),
                low=_apply_agorot(data.low, divisor),
                close=price,
                volume=data.volume,
                market_cap=data.market_cap,
                pe_ratio=data.pe_ratio,
                forward_pe=data.forward_pe,
                eps=data.eps,
                dividend_rate=_apply_agorot(data.dividend_rate, divisor),
                dividend_yield=data.dividend_yield,
                payout_ratio=data.payout_ratio,
                source="Yahoo Finance",
            )
        except Exception:
            logger.exception("Failed to upsert daily metrics for %s", asset.symbol)

        try:
            AssetMetricsService.update_slow_changing_fields(
                db,
                asset,
                description=data.description,
                exchange=data.exchange,
                website=data.website,
                ceo=data.ceo,
                employees=data.employees,
                beta=data.beta,
                avg_volume=data.avg_volume,
                earnings_date=data.earnings_date,
                ex_dividend_date=data.ex_dividend_date,
                target_est=_apply_agorot(data.target_est, divisor),
                week_52_high=_apply_agorot(data.week_52_high, divisor),
                week_52_low=_apply_agorot(data.week_52_low, divisor),
                peg_ratio=data.peg_ratio,
                expense_ratio=data.expense_ratio,
                fund_family=data.fund_family,
                nav=_apply_agorot(data.nav, divisor),
            )
        except Exception:
            logger.exception("Failed to update slow fields for %s", asset.symbol)

    @staticmethod
    def _update_stock_assets(
        db: Session,
        assets: list[Asset],
        stats: dict[str, int],
    ) -> None:
        """Fetch enriched data from Yahoo Finance and update prices + metrics + slow fields."""
        symbols = [a.symbol for a in assets]
        logger.info("Batch fetching ticker info for %d non-crypto assets", len(symbols))
        processed_before = stats["updated"] + stats["failed"]

        try:
            batch_results = YFinanceClient().get_batch_ticker_info(symbols)
            today = date.today()
            for asset in assets:
                data = batch_results.get(asset.symbol)
                if data is None or data.price is None or data.price <= 0:
                    stats["failed"] += 1
                    logger.warning("No ticker info for %s", asset.symbol)
                    continue

                divisor = _AGOROT_DIVISOR if asset.symbol.endswith(".TA") else None
                price = _apply_agorot(data.price, divisor)
                asset.last_fetched_price = price
                asset.last_fetched_at = datetime.now()
                stats["updated"] += 1
                PriceFetcher._write_stock_metrics(db, asset, data, today, price, divisor)

            db.commit()
        except Exception as e:
            logger.error("Error batch fetching stock ticker info: %s", e)
            already_counted = (stats["updated"] + stats["failed"]) - processed_before
            stats["failed"] += len(assets) - already_counted

    @staticmethod
    def _update_crypto_assets(
        db: Session,
        assets: list[Asset],
        stats: dict[str, int],
    ) -> None:
        """Fetch market data from CoinGecko and update prices + metrics + slow fields."""
        crypto_symbols = [a.symbol for a in assets]
        logger.info("Batch fetching market data for %d crypto assets", len(crypto_symbols))
        processed_before = stats["updated"] + stats["failed"]

        try:
            client = _get_coingecko_client()
            market_data = client.get_market_data(crypto_symbols, "usd")

            today = date.today()
            for asset in assets:
                data = market_data.get(asset.symbol)
                if data is None or data.price is None or data.price <= 0:
                    stats["failed"] += 1
                    logger.warning("No market data for crypto %s", asset.symbol)
                    continue

                asset.last_fetched_price = data.price
                asset.last_fetched_at = datetime.now()
                stats["updated"] += 1

                try:
                    AssetMetricsService.upsert_daily_metrics(
                        db,
                        asset_id=asset.id,
                        target_date=today,
                        high=data.high_24h,
                        low=data.low_24h,
                        close=data.price,
                        volume=int(data.volume) if data.volume is not None else None,
                        market_cap=data.market_cap,
                        circulating_supply=data.circulating_supply,
                        market_cap_rank=data.market_cap_rank,
                        source="CoinGecko",
                    )
                except Exception:
                    logger.exception("Failed to upsert daily metrics for %s", asset.symbol)

                try:
                    AssetMetricsService.update_slow_changing_fields(
                        db,
                        asset,
                        max_supply=data.max_supply,
                        ath=data.ath,
                        ath_date=data.ath_date,
                        atl=data.atl,
                        atl_date=data.atl_date,
                    )
                except Exception:
                    logger.exception("Failed to update slow fields for %s", asset.symbol)

            db.commit()
        except Exception as e:
            logger.error("Error batch fetching crypto market data: %s", e)
            already_counted = (stats["updated"] + stats["failed"]) - processed_before
            stats["failed"] += len(assets) - already_counted

    @staticmethod
    def refresh_if_stale(
        db: Session,
        asset: Asset,
        cooldown_seconds: int = MANUAL_REFRESH_COOLDOWN_SECONDS,
    ) -> tuple[bool, Decimal | None, datetime | None]:
        """Fetch a fresh price only if the cached value is older than cooldown_seconds.

        Uses asset.last_fetched_at as a per-asset, cross-user cooldown backed by
        the DB row — no external cache needed, works across multiple workers.

        Args:
            db: Database session.
            asset: Asset model instance.
            cooldown_seconds: Minimum age in seconds before re-fetching. Default 60.

        Returns:
            (refreshed, price, fetched_at):
            - refreshed=False: cooldown active, cached values returned
            - refreshed=True, price not None: fresh fetch succeeded
            - refreshed=True, price is None: fresh fetch attempted but failed
        """
        if asset.last_fetched_at is not None:
            age_seconds = (datetime.now() - asset.last_fetched_at).total_seconds()
            if age_seconds < cooldown_seconds:
                return False, asset.last_fetched_price, asset.last_fetched_at

        success = PriceFetcher.update_asset_price(db, asset)
        if success:
            return True, asset.last_fetched_price, asset.last_fetched_at
        return True, None, None

    @staticmethod
    def update_all_asset_prices(db: Session, asset_class: str | None = None) -> dict[str, int]:
        """Update prices, daily metrics, and slow-changing fields for all assets."""
        query = select(Asset)
        if asset_class:
            query = query.where(Asset.asset_class == asset_class)

        assets = db.execute(query).scalars().all()
        stats = {"total": len(assets), "updated": 0, "failed": 0, "skipped": 0}

        crypto_assets: list[Asset] = []
        other_assets: list[Asset] = []

        for asset in assets:
            if not asset.symbol or asset.asset_class == "Cash":
                stats["skipped"] += 1
                continue
            if asset.asset_class == "Crypto":
                crypto_assets = [*crypto_assets, asset]
            else:
                other_assets = [*other_assets, asset]

        if crypto_assets:
            PriceFetcher._update_crypto_assets(db, crypto_assets, stats)

        if other_assets:
            PriceFetcher._update_stock_assets(db, other_assets, stats)

        logger.info("Price update complete: %s", stats)
        return stats

    @staticmethod
    def get_historical_prices(symbol: str, period: str = "1mo") -> dict | None:
        """
        Get historical price data for a symbol.

        Args:
            symbol: The ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            Dictionary with historical data or None if fetch failed
        """
        try:
            rows = YFinanceClient().get_historical_data(symbol, period=period)

            if not rows:
                logger.warning(f"No historical data found for {symbol}")
                return None

            is_israeli_stock = symbol.endswith(".TA")
            divisor = _AGOROT_DIVISOR if is_israeli_stock else Decimal("1")

            data = {
                "symbol": symbol,
                "period": period,
                "data": [
                    {
                        "date": row.date.strftime("%Y-%m-%d")
                        if isinstance(row.date, date)
                        else str(row.date),
                        "open": float(row.open / divisor),
                        "high": float(row.high / divisor),
                        "low": float(row.low / divisor),
                        "close": float(row.close / divisor),
                        "volume": int(row.volume),
                    }
                    for row in rows
                ],
            }

            if is_israeli_stock:
                logger.debug(f"Converted {symbol} historical prices from Agorot to ILS")

            return data

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None

    @staticmethod
    def _fetch_crypto_historical_prices(
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[tuple[date, Decimal]]:
        """Fetch historical crypto prices using CoinGecko or CryptoCompare.

        Uses CoinGecko for dates within 365 days (free tier limit).
        Uses CryptoCompare for dates older than 365 days.

        Args:
            symbol: Crypto symbol (e.g., "BTC", "ETH")
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of (date, price) tuples
        """
        prices: list[tuple[date, Decimal]] = []
        cutoff_date = date.today() - timedelta(days=365)

        # Old dates (>365 days ago) -> CryptoCompare
        if start_date < cutoff_date:
            cc_end = min(end_date, cutoff_date - timedelta(days=1))
            try:
                cc_client = CryptoCompareClient()
                cc_prices = cc_client.get_price_history(symbol, start_date, cc_end, "USD")
                prices = [*prices, *cc_prices]
            except Exception as e:
                logger.error(f"CryptoCompare failed for {symbol}: {e}")

        # Recent dates (<=365 days ago) -> CoinGecko
        if end_date >= cutoff_date:
            cg_start = max(start_date, cutoff_date)
            try:
                cg_client = CoinGeckoClient()
                cg_prices = cg_client.get_price_history(symbol, cg_start, end_date, "usd")
                prices = [*prices, *cg_prices]
            except Exception as e:
                logger.error(f"CoinGecko failed for {symbol}: {e}")

        return prices

    @staticmethod
    def fetch_and_store_historical_prices(
        db: Session,
        asset_id: int,
        start_date: date,
        end_date: date,
    ) -> int:
        """Fetch historical prices and store in asset_prices table.

        For stocks: uses yfinance for the full date range in one API call.
        For crypto: uses CoinGecko (<365 days) or CryptoCompare (>365 days).
        Skips dates that already have prices in the database.

        Args:
            db: Database session
            asset_id: Asset to fetch prices for
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Number of new prices inserted
        """
        asset = db.get(Asset, asset_id)
        if not asset:
            logger.warning(f"Asset {asset_id} not found")
            return 0

        # Skip cash assets
        if asset.asset_class == "Cash":
            return 0

        # Get existing dates to skip
        existing_dates = set(
            row[0]
            for row in db.query(AssetPrice.date)
            .filter(
                AssetPrice.asset_id == asset_id,
                AssetPrice.date >= start_date,
                AssetPrice.date <= end_date,
            )
            .all()
        )

        prices_to_insert: list[tuple[date, Decimal]] = []

        if asset.asset_class == "Crypto":
            prices_to_insert = PriceFetcher._fetch_crypto_historical_prices(
                asset.symbol, start_date, end_date
            )

        else:
            # Stocks: use yfinance
            try:
                client = YFinanceClient()
                rows = client.get_history_for_range(asset.symbol, start_date, end_date)
                is_israeli = asset.symbol.endswith(".TA")
                divisor = Decimal("100") if is_israeli else Decimal("1")

                prices_to_insert = [
                    (row.date, Decimal(str(row.close / divisor)))
                    for row in rows
                    if row.close is not None and row.close > 0
                ]

            except Exception as e:
                logger.error(f"yfinance failed for {asset.symbol}: {e}")

        # Insert prices that don't exist
        count = 0
        for price_date, price_value in prices_to_insert:
            if price_date in existing_dates:
                continue
            if price_date < start_date or price_date > end_date:
                continue

            price_record = AssetPrice(
                asset_id=asset_id,
                date=price_date,
                closing_price=price_value,
                currency=asset.currency,
                source="CoinGecko/CryptoCompare"
                if asset.asset_class == "Crypto"
                else "Yahoo Finance",
            )
            db.add(price_record)
            existing_dates.add(price_date)  # Prevent duplicates within batch
            count += 1

        if count > 0:
            db.commit()
            logger.info(f"Inserted {count} historical prices for {asset.symbol}")

        return count

    @staticmethod
    def get_price_for_date(db: Session, asset_id: int, target_date: date) -> Decimal | None:
        """
        Get asset price for a specific date.

        - For past dates: Returns closing price from asset_prices table
        - For today: Returns current price from Asset.last_fetched_price (fetches if stale)
        - For future dates: Returns None

        Args:
            db: Database session
            asset_id: Asset ID
            target_date: Date for price lookup

        Returns:
            Price as Decimal, or None if not found
        """
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            logger.warning(f"Asset {asset_id} not found")
            return None

        if target_date < date.today():
            # Historical date - use closing price from asset_prices table
            asset_price = (
                db.query(AssetPrice)
                .filter(AssetPrice.asset_id == asset_id, AssetPrice.date == target_date)
                .first()
            )

            if asset_price:
                return asset_price.closing_price

            # Forward-fill: use most recent historical price before target_date
            # This handles weekends, holidays, and gaps in historical data
            most_recent_price = (
                db.query(AssetPrice)
                .filter(AssetPrice.asset_id == asset_id, AssetPrice.date < target_date)
                .order_by(AssetPrice.date.desc())
                .first()
            )

            if most_recent_price:
                logger.debug(
                    f"No price for {asset.symbol} on {target_date}, "
                    f"forward-filling from {most_recent_price.date}"
                )
                return most_recent_price.closing_price

            # Only fall back to last_fetched_price if no historical data exists at all
            logger.warning(
                f"No historical price data for {asset.symbol} before {target_date}, "
                f"using last_fetched_price"
            )
            return asset.last_fetched_price

        elif target_date == date.today():
            # Current day - use last_fetched_price (fetch if stale)
            is_stale = (
                not asset.last_fetched_at
                or (datetime.now() - asset.last_fetched_at).total_seconds() > 300
            )
            if is_stale:
                logger.info(f"Fetching fresh price for {asset.symbol}")
                result = PriceFetcher._fetch_price_for_asset(asset)
                if result:
                    asset.last_fetched_price, asset.last_fetched_at = result
                    db.commit()

            return asset.last_fetched_price

        else:
            # Future date
            logger.warning(f"Cannot get price for future date: {target_date}")
            return None
