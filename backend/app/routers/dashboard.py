"""Dashboard API router."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models.user import User
from app.schemas.dashboard import BenchmarkResponse, DashboardSummaryResponse, MoversResponse
from app.services.market_data.yfinance_client import YFinanceClient
from app.services.portfolio.dashboard_service import DashboardService
from app.services.portfolio.types import (
    AccountValue,
    DashboardSummary,
    TopHolding,
)
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper
from app.services.shared.response_formatters import to_float

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_EMPTY_SUMMARY = {
    "total_value": 0,
    "display_currency": "USD",
    "total_value_usd": 0,
    "total_value_ils": 0,
    "day_change": None,
    "day_change_pct": None,
    "previous_close_value": None,
    "accounts": [],
    "asset_allocation": [],
    "top_holdings": [],
    "historical_performance": [],
}


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    display_currency: str = Query(
        "USD", description="Currency for displaying values", pattern="^[A-Z]{3}$"
    ),
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get portfolio dashboard summary with aggregated data."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return {**_EMPTY_SUMMARY, "display_currency": display_currency}

    summary = DashboardService(db).get_summary(allowed_account_ids)
    return _format_summary(db, summary, display_currency)


@router.get("/movers", response_model=MoversResponse)
async def get_movers(
    limit: int = Query(3, ge=1, le=10, description="Number of gainers/losers to return"),
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top daily gainers and losers from portfolio positions."""
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return {"gainers": [], "losers": []}

    gainers, losers = DashboardService(db).get_movers(allowed_account_ids, limit=limit)
    return {"gainers": gainers, "losers": losers}


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark_performance(
    period: str = Query("1mo", description="Time period: 1mo, 3mo, 6mo, 1y, ytd, max"),
    symbol: str = Query("SPY", description="Benchmark symbol (default: SPY for S&P 500)"),
):
    """
    Get benchmark historical performance data.

    Returns daily closing prices and cumulative % change from period start,
    designed to align with portfolio TWR calculations.
    """
    default_name = "S&P 500 ETF"

    try:
        client = YFinanceClient()
        rows = client.get_historical_data(symbol, period=period)

        if not rows:
            logger.warning(f"No historical data found for benchmark {symbol}")
            return {
                "symbol": symbol,
                "name": default_name,
                "data": [],
                "error": "No data available",
            }

        # Get benchmark name from ticker info
        try:
            info = client.get_ticker_info(symbol)
            name = info.name if info and info.name else default_name
        except Exception:
            name = default_name

        # Calculate performance relative to first data point
        start_price = float(rows[0].close)
        data = [
            {
                "date": row.date.isoformat(),
                "price": round(float(row.close), 2),
                "performance": round(((float(row.close) - start_price) / start_price) * 100, 2)
                if start_price > 0
                else 0,
            }
            for row in rows
        ]

        return {"symbol": symbol, "name": name, "data": data}

    except Exception as e:
        logger.error(f"Error fetching benchmark data for {symbol}: {e}")
        return {"symbol": symbol, "name": default_name, "data": [], "error": str(e)}


# ------------------------------------------------------------------
# Response formatting (display-currency conversion at API boundary)
# ------------------------------------------------------------------


def _convert(db: Session, value: Decimal, display_currency: str) -> float:
    """Convert a USD Decimal to display_currency float."""
    return float(CurrencyConversionHelper.convert_value(db, value, "USD", display_currency))


def _format_account(db: Session, a: AccountValue, display_currency: str) -> dict:
    """Format a single account with display-currency value."""
    value_usd = float(a.value_usd)
    value_ils = float(a.value_ils)

    if display_currency == "USD":
        value = value_usd
    elif display_currency == "ILS":
        value = value_ils
    else:
        value = _convert(db, a.value_usd, display_currency)

    return {
        "id": a.account_id,
        "name": a.name,
        "type": a.account_type,
        "institution": a.institution,
        "currency": a.currency,
        "value": value,
        "value_usd": value_usd,
        "value_ils": value_ils,
        "display_currency": display_currency,
    }


def _format_top_holding(h: TopHolding) -> dict:
    """Format a single top-holding entry (always USD)."""
    return {
        "id": h.holding_id,
        "symbol": h.symbol,
        "name": h.name,
        "asset_class": h.asset_class,
        "account_name": h.account_name,
        "quantity": float(h.quantity),
        "cost_basis": float(h.cost_basis),
        "current_price": to_float(h.current_price),
        "currency": h.currency,
        "market_value": float(h.market_value_usd),
    }


def _format_summary(db: Session, s: DashboardSummary, display_currency: str) -> dict:
    """Convert a DashboardSummary (all USD) to the API response dict."""
    if s.day_change_usd is not None and s.previous_close_value_usd is not None:
        day_change = _convert(db, s.day_change_usd, display_currency)
        previous_close_value = _convert(db, s.previous_close_value_usd, display_currency)
    else:
        day_change = None
        previous_close_value = None

    return {
        "total_value": _convert(db, s.total_value_usd, display_currency),
        "display_currency": display_currency,
        "total_value_usd": float(s.total_value_usd),
        "total_value_ils": float(s.total_value_ils),
        "day_change": day_change,
        "day_change_pct": to_float(s.day_change_pct),
        "previous_close_value": previous_close_value,
        "accounts": [_format_account(db, a, display_currency) for a in s.accounts],
        "asset_allocation": [
            {
                "asset_class": item.asset_class,
                "total_value": _convert(db, item.total_value, display_currency),
                "holding_count": item.holding_count,
                "display_currency": display_currency,
            }
            for item in s.asset_allocation
        ],
        "top_holdings": [_format_top_holding(h) for h in s.top_holdings],
        "historical_performance": [
            CurrencyConversionHelper.convert_snapshot_dict(
                db,
                {"date": p.date, "value_usd": p.value_usd, "value_ils": p.value_ils},
                display_currency,
            )
            for p in s.historical_performance
        ],
    }
