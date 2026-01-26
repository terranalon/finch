"""Positions API router - aggregated holdings by asset."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.user_scope import get_user_account_ids
from app.models import Account, Asset, AssetPrice, Holding
from app.models.user import User
from app.services.currency_conversion_helper import CurrencyConversionHelper
from app.services.currency_service import CurrencyService
from app.services.trading_calendar_service import TradingCalendarService

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("")
async def list_positions(
    display_currency: str = Query(
        "USD", description="Currency for displaying values", pattern="^[A-Z]{3}$"
    ),
    portfolio_id: str | None = Query(None, description="Filter by portfolio ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Get positions aggregated by asset across all user's accounts.

    Args:
        display_currency: Currency code for displaying values (default: USD)
        portfolio_id: Filter by specific portfolio (must belong to user)

    Returns:
        Consolidated view of holdings grouped by asset,
        showing total quantity, total cost basis, and account breakdown.
    """
    # Get user's account IDs (optionally filtered by portfolio)
    allowed_account_ids = get_user_account_ids(current_user, db, portfolio_id)
    if not allowed_account_ids:
        return []

    # Get all active holdings with account and asset details (filtered by user)
    holdings_query = (
        db.query(Holding, Account, Asset)
        .join(Account, Holding.account_id == Account.id)
        .join(Asset, Holding.asset_id == Asset.id)
        .filter(Holding.is_active.is_(True), Holding.account_id.in_(allowed_account_ids))
        .all()
    )

    # Group by asset
    positions_map = {}
    for holding, account, asset in holdings_query:
        asset_id = asset.id

        if asset_id not in positions_map:
            # For Cash assets, price is 1.0 (1 unit = 1 unit in native currency)
            price = Decimal("1") if asset.asset_class == "Cash" else asset.last_fetched_price
            positions_map[asset_id] = {
                "asset_id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_class": asset.asset_class,
                "category": asset.category,
                "industry": asset.industry,
                "current_price": price,
                "currency": asset.currency or "USD",
                "is_favorite": asset.is_favorite,
                "total_quantity": Decimal("0"),
                "total_cost_basis": Decimal("0"),
                "total_cost_basis_native": Decimal("0"),  # Native currency accumulator
                "account_count": 0,
                "accounts": [],
            }

        # Calculate P&L for this account holding
        asset_currency = asset.currency or "USD"

        # For Cash assets, price is 1.0 (1 unit = 1 unit in native currency)
        # For other assets, use the fetched price
        if asset.asset_class == "Cash":
            current_price = Decimal("1")
            market_value_native = holding.quantity  # Value equals quantity for cash
        else:
            current_price = asset.last_fetched_price or Decimal("0")
            market_value_native = (
                holding.quantity * current_price if current_price else Decimal("0")
            )

        # Store native currency values (before conversion)
        cost_basis_native = holding.cost_basis
        pnl_native = (market_value_native - cost_basis_native) if current_price else None
        pnl_pct = (
            (pnl_native / cost_basis_native * 100)
            if (current_price and cost_basis_native > 0)
            else None
        )

        # Convert cost_basis and market_value to USD for portfolio aggregation
        if asset_currency != "USD":
            rate_to_usd = CurrencyService.get_exchange_rate(db, asset_currency, "USD")
            if rate_to_usd:
                cost_basis_usd = holding.cost_basis * rate_to_usd
                market_value = market_value_native * rate_to_usd if current_price else Decimal("0")
            else:
                cost_basis_usd = holding.cost_basis
                market_value = market_value_native
        else:
            cost_basis_usd = holding.cost_basis
            market_value = market_value_native

        pnl = market_value - cost_basis_usd if current_price else None

        # Accumulate totals (USD for portfolio aggregation, native for per-asset display)
        positions_map[asset_id]["total_quantity"] += holding.quantity
        positions_map[asset_id]["total_cost_basis"] += cost_basis_usd
        positions_map[asset_id]["total_cost_basis_native"] += cost_basis_native

        # Add account breakdown with both native and USD values
        positions_map[asset_id]["accounts"].append(
            {
                "holding_id": holding.id,
                "account_id": account.id,
                "account_name": account.name,
                "account_type": account.account_type,
                "institution": account.institution,
                "quantity": float(holding.quantity),
                # Native currency values (for per-holding display)
                "cost_basis_native": float(cost_basis_native),
                "market_value_native": float(market_value_native) if current_price else None,
                "pnl_native": float(pnl_native) if pnl_native is not None else None,
                # USD values (for portfolio aggregation)
                "cost_basis": float(cost_basis_usd),
                "market_value": float(market_value) if current_price else None,
                "pnl": float(pnl) if pnl is not None else None,
                "pnl_pct": float(pnl_pct) if pnl_pct is not None else None,
                "strategy_horizon": holding.strategy_horizon,
            }
        )
        positions_map[asset_id]["account_count"] = len(positions_map[asset_id]["accounts"])

    # Get closing prices for day change calculation (per-asset market detection)
    asset_ids = list(positions_map.keys())
    today = date.today()

    # Fetch the two most recent closing prices for each asset
    # This covers both market-open and market-closed scenarios
    latest_prices_map: dict[int, list[AssetPrice]] = {}
    for asset_id in asset_ids:
        prices = (
            db.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset_id)
            .order_by(desc(AssetPrice.date))
            .limit(2)
            .all()
        )
        if prices:
            latest_prices_map[asset_id] = prices

    # Also fetch previous close for market-open scenario (price before today)
    latest_date_subquery = (
        db.query(AssetPrice.asset_id, func.max(AssetPrice.date).label("max_date"))
        .filter(AssetPrice.asset_id.in_(asset_ids), AssetPrice.date < today)
        .group_by(AssetPrice.asset_id)
        .subquery()
    )
    previous_prices = (
        db.query(AssetPrice)
        .join(
            latest_date_subquery,
            (AssetPrice.asset_id == latest_date_subquery.c.asset_id)
            & (AssetPrice.date == latest_date_subquery.c.max_date),
        )
        .all()
    )
    previous_close_map = {price.asset_id: price.closing_price for price in previous_prices}

    # Convert to list and format
    positions = []
    for position in positions_map.values():
        current_price = position["current_price"]
        total_quantity = position["total_quantity"]
        total_cost_basis = position["total_cost_basis"]
        total_cost_basis_native = position["total_cost_basis_native"]
        asset_currency = position["currency"]

        # Calculate total market value in asset's native currency
        total_market_value_native = (total_quantity * current_price) if current_price else None

        # Calculate P&L in native currency
        total_pnl_native = (
            (total_market_value_native - total_cost_basis_native)
            if total_market_value_native is not None
            else None
        )
        total_pnl_pct = (
            (total_pnl_native / total_cost_basis_native * 100)
            if (total_pnl_native is not None and total_cost_basis_native > 0)
            else None
        )

        # Convert to USD if needed (for portfolio aggregation)
        if total_market_value_native is not None and asset_currency != "USD":
            rate_to_usd = CurrencyService.get_exchange_rate(db, asset_currency, "USD")
            if rate_to_usd:
                total_market_value = total_market_value_native * rate_to_usd
            else:
                total_market_value = total_market_value_native
        else:
            total_market_value = total_market_value_native

        total_pnl = (
            (total_market_value - total_cost_basis) if total_market_value is not None else None
        )

        # Calculate day change from closing prices (per-asset market detection)
        # Skip Cash assets - they don't have market prices (1 USD = 1 USD always)
        asset_id = position["asset_id"]
        symbol = position["symbol"]

        if position["asset_class"] == "Cash":
            day_change = None
            day_change_pct = None
            previous_close_price = None
            day_change_date = None
            is_asset_market_closed = False
        elif position["asset_class"] == "Crypto":
            # Crypto markets are 24/7 - always use "market open" logic (current price vs previous close)
            is_asset_market_closed = False
        else:
            # Determine which market this asset belongs to
            market = TradingCalendarService.get_market_for_symbol(symbol)
            is_asset_market_closed = TradingCalendarService.is_market_closed(today, market)

            if is_asset_market_closed:
                # Market closed: compare two most recent closing prices
                prices = latest_prices_map.get(asset_id, [])
                if len(prices) >= 2:
                    price_for_day_change = prices[0].closing_price
                    previous_close_price = prices[1].closing_price
                    day_change_date = prices[0].date
                elif len(prices) == 1:
                    price_for_day_change = prices[0].closing_price
                    previous_close_price = None
                    day_change_date = prices[0].date
                else:
                    price_for_day_change = None
                    previous_close_price = None
                    day_change_date = None
            else:
                # Market open: compare current price vs previous closing price
                price_for_day_change = current_price
                previous_close_price = previous_close_map.get(asset_id)
                day_change_date = today

            if previous_close_price and price_for_day_change:
                day_change = price_for_day_change - previous_close_price
                day_change_pct = (day_change / previous_close_price) * 100
            else:
                day_change = None
                day_change_pct = None
                previous_close_price = None

        positions.append(
            {
                "asset_id": position["asset_id"],
                "symbol": position["symbol"],
                "name": position["name"],
                "asset_class": position["asset_class"],
                "category": position["category"],
                "industry": position["industry"],
                "currency": asset_currency,
                "is_favorite": position["is_favorite"],
                "current_price": float(current_price) if current_price else None,
                "previous_close_price": float(previous_close_price)
                if previous_close_price
                else None,
                "day_change": float(day_change) if day_change is not None else None,
                "day_change_pct": float(day_change_pct) if day_change_pct is not None else None,
                "day_change_date": str(day_change_date) if day_change_date else None,
                "is_market_closed": is_asset_market_closed,
                "total_quantity": float(total_quantity),
                # Native currency values (for per-holding display)
                "total_cost_basis_native": float(total_cost_basis_native),
                "total_market_value_native": float(total_market_value_native)
                if total_market_value_native is not None
                else None,
                "total_pnl_native": float(total_pnl_native)
                if total_pnl_native is not None
                else None,
                "avg_cost_per_unit_native": float(total_cost_basis_native / total_quantity)
                if total_quantity > 0
                else 0,
                # Display currency values (for portfolio aggregation)
                "total_cost_basis": float(total_cost_basis),
                "total_market_value": float(total_market_value)
                if total_market_value is not None
                else None,
                "total_pnl": float(total_pnl) if total_pnl is not None else None,
                "total_pnl_pct": float(total_pnl_pct) if total_pnl_pct is not None else None,
                "account_count": position["account_count"],
                "accounts": position["accounts"],
                "avg_cost_per_unit": float(total_cost_basis / total_quantity)
                if total_quantity > 0
                else 0,
            }
        )

    # Sort by total market value descending (or cost basis if market value not available)
    positions.sort(
        key=lambda x: x["total_market_value"]
        if x["total_market_value"] is not None
        else x["total_cost_basis"],
        reverse=True,
    )

    # Convert to display currency if requested
    if display_currency != "USD":
        positions = [
            CurrencyConversionHelper.convert_position_dict(db, pos, display_currency)
            for pos in positions
        ]
    else:
        # Add display_currency field even for USD
        for pos in positions:
            pos["display_currency"] = "USD"

    # Add current_value and current_price in display currency
    for pos in positions:
        # Current value is the same as total market value (already in display currency after conversion)
        pos["current_value"] = pos["total_market_value"]

        # Convert current_price to display currency
        if pos["current_price"] is not None:
            asset_currency = pos["currency"]
            if display_currency != asset_currency:
                rate = CurrencyService.get_exchange_rate(db, asset_currency, display_currency)
                if rate:
                    pos["current_price_display"] = float(Decimal(str(pos["current_price"])) * rate)
                else:
                    pos["current_price_display"] = pos["current_price"]
            else:
                pos["current_price_display"] = pos["current_price"]
        else:
            pos["current_price_display"] = None

    return positions
