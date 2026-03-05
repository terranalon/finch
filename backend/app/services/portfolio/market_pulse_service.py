"""Market pulse service - fetches live market index data."""

import logging
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


def get_market_pulse(client: YFinanceClient | None = None) -> list[MarketPulseItem]:
    """Fetch current prices and 5-day sparkline for market indices.

    Accepts an optional client for dependency injection (testing).
    """
    if client is None:
        client = YFinanceClient()

    symbols = list(MARKET_SYMBOLS.keys())

    latest = client.get_batch_prices_threaded(symbols, period="2d")

    items: list[MarketPulseItem] = []
    for symbol, name in MARKET_SYMBOLS.items():
        row = latest.get(symbol)
        if row is None:
            continue

        price = float(row.close)

        day_change = None
        day_change_pct = None
        if row.open and float(row.open) > 0:
            day_change = round(price - float(row.open), 2)
            day_change_pct = round((day_change / float(row.open)) * 100, 2)

        sparkline: list[float] = []
        try:
            history = client.get_historical_data(symbol, period="5d")
            sparkline = [float(r.close) for r in history]
        except Exception:
            logger.debug("Failed sparkline for %s", symbol, exc_info=True)

        items = [
            *items,
            MarketPulseItem(
                symbol=symbol,
                name=name,
                price=round(price, 2),
                day_change=day_change,
                day_change_pct=day_change_pct,
                sparkline=sparkline,
            ),
        ]

    return items
