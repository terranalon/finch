"""Dashboard API router."""

import logging
from datetime import date, timedelta
from decimal import Decimal

import yfinance as yf
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Account, Asset, HistoricalSnapshot, Holding
from app.models.user import User
from app.services.currency_conversion_helper import CurrencyConversionHelper
from app.services.currency_service import CurrencyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary(
    display_currency: str = Query(
        "USD", description="Currency for displaying values", pattern="^[A-Z]{3}$"
    ),
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get portfolio dashboard summary with aggregated data.

    Args:
        display_currency: Currency code for displaying values (default: USD)
        portfolio_id: Filter by specific portfolio (must belong to user)

    Returns:
        - Total portfolio value across all accounts
        - Account breakdown with individual values
        - Asset class allocation
        - Top holdings by value
        - Recent performance data
    """
    # Calculate current portfolio value based on current holdings and prices
    accounts_data = []
    total_value_usd = Decimal("0")
    total_value_ils = Decimal("0")

    # Get only user's accounts (optionally filtered by portfolio)
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return {
            "total_value": 0,
            "display_currency": display_currency,
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

    accounts = (
        db.query(Account)
        .filter(Account.is_active.is_(True), Account.id.in_(allowed_account_ids))
        .all()
    )

    for account in accounts:
        # Calculate current account value from holdings
        account_value_usd = Decimal("0")

        holdings = (
            db.query(Holding)
            .filter(Holding.account_id == account.id, Holding.is_active.is_(True))
            .all()
        )

        for holding in holdings:
            # Get current price for this asset
            asset = holding.asset
            asset_currency = asset.currency or "USD"

            # Handle Cash assets differently - value is the quantity itself
            if asset.asset_class == "Cash":
                # Skip negative cash balances (liabilities)
                if holding.quantity <= 0:
                    continue
                # For cash, value = quantity (1 ILS = 1 ILS, 1 USD = 1 USD)
                market_value_native = holding.quantity
            else:
                current_price = asset.last_fetched_price or Decimal("0")
                if not current_price:
                    continue
                # Calculate market value in asset's native currency
                market_value_native = holding.quantity * current_price

            # Convert to USD using current exchange rate
            if asset_currency != "USD":
                rate_to_usd = CurrencyService.get_exchange_rate(db, asset_currency, "USD")
                market_value_usd = (
                    market_value_native * rate_to_usd if rate_to_usd else market_value_native
                )
            else:
                market_value_usd = market_value_native

            account_value_usd += market_value_usd

        # Convert to ILS for display
        usd_to_ils_rate = CurrencyService.get_exchange_rate(db, "USD", "ILS")
        account_value_ils = (
            account_value_usd * usd_to_ils_rate if usd_to_ils_rate else account_value_usd
        )

        accounts_data.append(
            {
                "id": account.id,
                "name": account.name,
                "type": account.account_type,
                "institution": account.institution,
                "currency": account.currency,
                "value_usd": float(account_value_usd),
                "value_ils": float(account_value_ils),
            }
        )

        total_value_usd += account_value_usd
        total_value_ils += account_value_ils

    # Calculate day change by comparing with previous day's snapshot
    yesterday = date.today() - timedelta(days=1)
    previous_snapshot = (
        db.query(func.sum(HistoricalSnapshot.total_value_usd).label("total_usd"))
        .filter(HistoricalSnapshot.date == yesterday)
        .first()
    )

    previous_close_value_usd = (
        Decimal(str(previous_snapshot.total_usd or 0)) if previous_snapshot else None
    )

    if previous_close_value_usd and previous_close_value_usd > 0:
        day_change_usd = total_value_usd - previous_close_value_usd
        day_change_pct = (day_change_usd / previous_close_value_usd) * 100
    else:
        day_change_usd = None
        day_change_pct = None

    # Calculate asset class allocation by current market value (user's holdings only)
    holdings_with_assets = (
        db.query(Holding, Asset)
        .join(Asset, Holding.asset_id == Asset.id)
        .filter(Holding.is_active.is_(True), Holding.account_id.in_(allowed_account_ids))
        .all()
    )

    # Group by asset class and calculate total market values
    asset_class_values = {}
    for holding, asset in holdings_with_assets:
        asset_class = asset.asset_class or "Unknown"
        asset_currency = asset.currency or "USD"

        # Handle Cash assets differently
        if asset_class == "Cash":
            if holding.quantity <= 0:
                continue
            market_value_native = holding.quantity
        else:
            current_price = asset.last_fetched_price or Decimal("0")
            if not current_price:
                continue
            market_value_native = holding.quantity * current_price

        if asset_currency != "USD":
            rate_to_usd = CurrencyService.get_exchange_rate(db, asset_currency, "USD")
            market_value_usd = (
                market_value_native * rate_to_usd if rate_to_usd else market_value_native
            )
        else:
            market_value_usd = market_value_native

        if asset_class not in asset_class_values:
            asset_class_values[asset_class] = {"total_value": Decimal("0"), "count": 0}

        asset_class_values[asset_class]["total_value"] += market_value_usd
        asset_class_values[asset_class]["count"] += 1

    asset_allocation_data = [
        {
            "asset_class": asset_class,
            "total_value": float(data["total_value"]),
            "holding_count": data["count"],
        }
        for asset_class, data in asset_class_values.items()
    ]

    # Sort by value descending
    asset_allocation_data.sort(key=lambda x: x["total_value"], reverse=True)

    # Convert asset allocation to display currency
    if display_currency != "USD":
        for item in asset_allocation_data:
            converted_value = CurrencyConversionHelper.convert_value(
                db, Decimal(str(item["total_value"])), "USD", display_currency
            )
            item["total_value"] = float(converted_value)
            item["display_currency"] = display_currency
    else:
        for item in asset_allocation_data:
            item["display_currency"] = "USD"

    # Get top holdings by current market value (user's holdings only)
    holdings_query = (
        db.query(Holding, Asset, Account.name.label("account_name"))
        .join(Asset, Holding.asset_id == Asset.id)
        .join(Account, Holding.account_id == Account.id)
        .filter(Holding.is_active.is_(True), Holding.account_id.in_(allowed_account_ids))
        .all()
    )

    # Calculate market value for each holding and sort
    top_holdings_data = []
    for holding, asset, account_name in holdings_query:
        asset_currency = asset.currency or "USD"

        # Handle Cash assets differently
        if asset.asset_class == "Cash":
            if holding.quantity <= 0:
                continue
            current_price = Decimal("1")  # 1 unit = 1 unit for cash
            market_value_native = holding.quantity
        else:
            current_price = asset.last_fetched_price or Decimal("0")
            if not current_price:
                market_value_usd = Decimal("0")
                market_value_native = Decimal("0")
            else:
                market_value_native = holding.quantity * current_price

        # Convert to USD
        if current_price and market_value_native:
            if asset_currency != "USD":
                rate_to_usd = CurrencyService.get_exchange_rate(db, asset_currency, "USD")
                market_value_usd = (
                    market_value_native * rate_to_usd if rate_to_usd else market_value_native
                )
            else:
                market_value_usd = market_value_native
        else:
            market_value_usd = Decimal("0")

        top_holdings_data.append(
            {
                "id": holding.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_class": asset.asset_class,
                "account_name": account_name,
                "quantity": float(holding.quantity),
                "cost_basis": float(holding.cost_basis),
                "current_price": float(current_price) if current_price else None,
                "currency": asset.currency or "USD",
                "market_value": float(market_value_usd),
            }
        )

    # Sort by market value and take top 10
    top_holdings_data.sort(key=lambda x: x["market_value"], reverse=True)
    top_holdings_data = top_holdings_data[:10]

    # Get historical performance (last 30 days) - filtered by user's accounts
    historical_data = (
        db.query(
            HistoricalSnapshot.date,
            func.sum(HistoricalSnapshot.total_value_usd).label("total_usd"),
            func.sum(HistoricalSnapshot.total_value_ils).label("total_ils"),
        )
        .filter(HistoricalSnapshot.account_id.in_(allowed_account_ids))
        .group_by(HistoricalSnapshot.date)
        .order_by(HistoricalSnapshot.date.desc())
        .limit(30)
        .all()
    )

    historical_performance = [
        {
            "date": str(snapshot.date),
            "value_usd": float(snapshot.total_usd or 0),
            "value_ils": float(snapshot.total_ils or 0),
        }
        for snapshot in reversed(historical_data)  # Reverse to show oldest to newest
    ]

    # Convert total values to display currency
    if display_currency != "USD":
        total_value = CurrencyConversionHelper.convert_value(
            db, total_value_usd, "USD", display_currency
        )
    else:
        total_value = total_value_usd

    # Convert account values to display currency
    for account in accounts_data:
        if display_currency == "USD":
            account["value"] = account["value_usd"]
        elif display_currency == "ILS":
            account["value"] = account["value_ils"]
        else:
            account["value"] = float(
                CurrencyConversionHelper.convert_value(
                    db, Decimal(str(account["value_usd"])), "USD", display_currency
                )
            )
        # Keep original values for reference
        account["display_currency"] = display_currency

    # Convert historical performance
    converted_performance = []
    for snapshot in historical_performance:
        converted_snapshot = CurrencyConversionHelper.convert_snapshot_dict(
            db, snapshot, display_currency
        )
        converted_performance.append(converted_snapshot)

    # Convert day change to display currency
    if day_change_usd is not None:
        if display_currency != "USD":
            day_change = float(
                CurrencyConversionHelper.convert_value(db, day_change_usd, "USD", display_currency)
            )
            previous_close_value = float(
                CurrencyConversionHelper.convert_value(
                    db, previous_close_value_usd, "USD", display_currency
                )
            )
        else:
            day_change = float(day_change_usd)
            previous_close_value = float(previous_close_value_usd)
    else:
        day_change = None
        previous_close_value = None

    return {
        "total_value": float(total_value),
        "display_currency": display_currency,
        "total_value_usd": float(total_value_usd),  # Keep for reference
        "total_value_ils": float(total_value_ils),  # Keep for reference
        "day_change": day_change,
        "day_change_pct": float(day_change_pct) if day_change_pct is not None else None,
        "previous_close_value": previous_close_value,
        "accounts": accounts_data,
        "asset_allocation": asset_allocation_data,
        "top_holdings": top_holdings_data,
        "historical_performance": converted_performance,
    }


@router.get("/benchmark")
async def get_benchmark_performance(
    period: str = Query("1mo", description="Time period: 1mo, 3mo, 6mo, 1y, ytd, max"),
    symbol: str = Query("SPY", description="Benchmark symbol (default: SPY for S&P 500)"),
) -> dict:
    """
    Get benchmark historical performance data.

    Returns daily closing prices and cumulative % change from period start,
    designed to align with portfolio TWR calculations.
    """
    default_name = "S&P 500 ETF"

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            logger.warning(f"No historical data found for benchmark {symbol}")
            return {
                "symbol": symbol,
                "name": default_name,
                "data": [],
                "error": "No data available",
            }

        # Get benchmark name, falling back to default
        try:
            info = ticker.info
            name = info.get("shortName") or info.get("longName") or default_name
        except Exception:
            name = default_name

        # Calculate performance relative to first data point
        start_price = float(hist.iloc[0]["Close"])
        data = [
            {
                "date": dt.strftime("%Y-%m-%d"),
                "price": round(float(row["Close"]), 2),
                "performance": round(((float(row["Close"]) - start_price) / start_price) * 100, 2)
                if start_price > 0
                else 0,
            }
            for dt, row in hist.iterrows()
        ]

        return {"symbol": symbol, "name": name, "data": data}

    except Exception as e:
        logger.error(f"Error fetching benchmark data for {symbol}: {e}")
        return {"symbol": symbol, "name": default_name, "data": [], "error": str(e)}
