"""Sparkline service - batch-fetches intraday sparkline data for assets."""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.services.market_data.coingecko_client import CoinGeckoClient
from app.services.market_data.yfinance_client import YFinanceClient
from app.services.repositories.asset_repository import AssetRepository

logger = logging.getLogger(__name__)


def get_batch_sparklines(
    db: Session,
    symbols: list[str],
) -> dict[str, list[float]]:
    """Batch-fetch 1-day intraday sparklines (hourly) for a list of symbols.

    Stocks/ETFs use YFinance (period=1d, interval=1h).
    Crypto uses CoinGecko (1-day range, downsampled to ~hourly).
    Both are fetched in parallel via ThreadPoolExecutor.
    """
    if not symbols:
        return {}

    # Partition symbols into crypto vs non-crypto (via repository)
    assets = AssetRepository(db).find_by_symbols(symbols)
    crypto_symbols = {a.symbol for a in assets if a.asset_class == "Crypto"}
    stock_symbols = [s for s in symbols if s not in crypto_symbols]
    crypto_list = [s for s in symbols if s in crypto_symbols]

    with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as pool:
        futures: dict[str, object] = {}

        # Stock sparklines via YFinance (1D hourly)
        if stock_symbols:
            yf_client = YFinanceClient()
            for sym in stock_symbols:
                futures[sym] = pool.submit(_fetch_stock_sparkline, yf_client, sym)

        # Crypto sparklines via CoinGecko (1-day, downsampled)
        if crypto_list:
            cg_client = CoinGeckoClient()
            for sym in crypto_list:
                futures[sym] = pool.submit(_fetch_crypto_sparkline, cg_client, sym)

        return {sym: fut.result() for sym, fut in futures.items()}


def _fetch_stock_sparkline(client: YFinanceClient, symbol: str) -> list[float]:
    """Fetch 1-day hourly sparkline for a single stock/ETF symbol."""
    try:
        rows = client.get_historical_data(symbol, period="1d", interval="1h")
        return [float(r.close) for r in rows]
    except Exception:
        logger.debug("Failed 1D sparkline for %s", symbol, exc_info=True)
        return []


def _fetch_crypto_sparkline(client: CoinGeckoClient, symbol: str) -> list[float]:
    """Fetch 1-day sparkline for a crypto symbol via CoinGecko."""
    try:
        end = date.today()
        start = end - timedelta(days=1)
        target_points = 7
        history = client.get_price_history(symbol, start, end)
        all_prices = [float(price) for _d, price in history]
        step = max(1, len(all_prices) // target_points)
        return all_prices[::step]
    except Exception:
        logger.debug("CoinGecko sparkline failed for %s", symbol, exc_info=True)
        return []
