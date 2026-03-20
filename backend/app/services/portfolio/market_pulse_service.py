"""Market pulse and benchmark services - live market data for the dashboard."""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

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
    Price and day change are derived from the sparkline data (last 2 entries),
    eliminating a redundant batch price fetch.
    """
    if client is None:
        client = YFinanceClient()

    symbols = list(MARKET_SYMBOLS.keys())

    # Single fetch: 5-day sparklines in parallel (provides price + prev_close + chart)
    with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as pool:
        futures = {symbol: pool.submit(_fetch_sparkline, client, symbol) for symbol in symbols}
        sparklines = {symbol: fut.result() for symbol, fut in futures.items()}

    items: list[MarketPulseItem] = []
    for symbol, name in MARKET_SYMBOLS.items():
        spark = sparklines.get(symbol, [])
        if not spark:
            continue

        price = round(spark[-1], 2)

        # Day change from previous close (spark[-2])
        day_change = None
        day_change_pct = None
        if len(spark) >= 2:
            prev_close = spark[-2]
            if prev_close > 0:
                day_change = round(price - prev_close, 2)
                day_change_pct = round((day_change / prev_close) * 100, 2)

        items.append(
            MarketPulseItem(
                symbol=symbol,
                name=name,
                price=price,
                day_change=day_change,
                day_change_pct=day_change_pct,
                sparkline=spark,
            ),
        )

    return items


# ------------------------------------------------------------------
# Benchmark
# ------------------------------------------------------------------

_DEFAULT_BENCHMARK_NAME = "S&P 500 ETF"


@dataclass
class BenchmarkDataPoint:
    """Single benchmark data point with cumulative performance."""

    date: str
    price: float
    performance: float


@dataclass
class BenchmarkResult:
    """Result of a benchmark data fetch."""

    symbol: str
    name: str
    data: list[BenchmarkDataPoint] = field(default_factory=list)
    error: str | None = None


def get_benchmark_data(
    symbol: str = "SPY",
    period: str = "1mo",
    start_date: date | None = None,
    end_date: date | None = None,
) -> BenchmarkResult:
    """Fetch benchmark historical performance data.

    Returns daily closing prices and cumulative % change from period start,
    designed to align with portfolio TWR calculations.

    Accepts either a named period or a custom date range via start_date/end_date.
    """
    try:
        client = YFinanceClient()
        if start_date and end_date:
            rows = client.get_history_for_range(symbol, start_date, end_date)
        else:
            rows = client.get_historical_data(symbol, period=period)

        if not rows:
            logger.warning("No historical data found for benchmark %s", symbol)
            return BenchmarkResult(
                symbol=symbol, name=_DEFAULT_BENCHMARK_NAME, error="No data available"
            )

        try:
            info = client.get_ticker_info(symbol)
            name = info.name if info and info.name else _DEFAULT_BENCHMARK_NAME
        except Exception:
            name = _DEFAULT_BENCHMARK_NAME

        start_price = float(rows[0].close)
        data = [
            BenchmarkDataPoint(
                date=row.date.isoformat(),
                price=round(float(row.close), 2),
                performance=(
                    round(((float(row.close) - start_price) / start_price) * 100, 2)
                    if start_price > 0
                    else 0.0
                ),
            )
            for row in rows
        ]

        return BenchmarkResult(symbol=symbol, name=name, data=data)

    except Exception as e:
        logger.error("Error fetching benchmark data for %s: %s", symbol, e)
        return BenchmarkResult(symbol=symbol, name=_DEFAULT_BENCHMARK_NAME, error=str(e))
