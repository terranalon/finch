"""Market pulse service - fetches live market index data."""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.services.market_data.yfinance_client import YFinanceClient

logger = logging.getLogger(__name__)

MARKET_SYMBOLS: dict[str, str] = {
    "SPY": "S&P 500",
    "QQQ": "NASDAQ 100",
    "DIA": "Dow Jones",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "GC=F": "Gold",
    "^VIX": "VIX",
    "^TNX": "10Y Treasury",
}


@dataclass
class MarketPulseItem:
    """Single market pulse data point."""

    symbol: str
    name: str
    price: float | None
    day_change: float | None
    day_change_pct: float | None
    sparkline: list[float]


def _fetch_sparkline(client: YFinanceClient, symbol: str) -> list[float]:
    """Fetch 5-day sparkline for a single symbol."""
    try:
        history = client.get_historical_data(symbol, period="5d")
        return [float(r.close) for r in history]
    except Exception:
        logger.debug("Failed sparkline for %s", symbol, exc_info=True)
        return []


def get_market_pulse(client: YFinanceClient | None = None) -> list[MarketPulseItem]:
    """Fetch current prices and 5-day sparkline for market indices.

    Accepts an optional client for dependency injection (testing).
    Sparklines are fetched in parallel to avoid sequential HTTP round-trips.
    """
    if client is None:
        client = YFinanceClient()

    symbols = list(MARKET_SYMBOLS.keys())

    latest = client.get_batch_prices_threaded(symbols, period="2d")

    # Fetch all sparklines in parallel
    symbols_with_data = [s for s in symbols if s in latest]
    sparklines: dict[str, list[float]] = {}
    if symbols_with_data:
        with ThreadPoolExecutor(max_workers=min(len(symbols_with_data), 8)) as pool:
            sparkline_futures = {
                symbol: pool.submit(_fetch_sparkline, client, symbol)
                for symbol in symbols_with_data
            }
            sparklines = {symbol: fut.result() for symbol, fut in sparkline_futures.items()}

    items: list[MarketPulseItem] = []
    for symbol, name in MARKET_SYMBOLS.items():
        row = latest.get(symbol)
        if row is None:
            continue

        price = float(row.close)

        # Compute day change from previous close (sparkline[-2]) instead of
        # intraday open, matching the standard (current - prev_close) convention.
        day_change = None
        day_change_pct = None
        spark = sparklines.get(symbol, [])
        if len(spark) >= 2:
            prev_close = spark[-2]
            if prev_close > 0:
                day_change = round(price - prev_close, 2)
                day_change_pct = round((day_change / prev_close) * 100, 2)

        items.append(
            MarketPulseItem(
                symbol=symbol,
                name=name,
                price=round(price, 2),
                day_change=day_change,
                day_change_pct=day_change_pct,
                sparkline=spark,
            ),
        )

    return items
