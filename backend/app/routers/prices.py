"""Prices API router - manage asset price updates."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset
from app.services.market_data.price_fetcher import PriceFetcher
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper

router = APIRouter(prefix="/api/prices", tags=["prices"])


@router.post("/update", response_model=dict[str, Any])
async def update_all_prices(
    background_tasks: BackgroundTasks,
    asset_class: str | None = None,
    run_async: bool = False,
    db: Session = Depends(get_db),
):
    """
    Update prices for all assets (or filtered by asset class).

    Args:
        asset_class: Optional filter for specific asset class (Stock, ETF, Crypto, etc.)
        run_async: If True, run update in background and return immediately

    Returns:
        Update statistics or status message
    """
    if run_async:
        # Run in background
        background_tasks.add_task(PriceFetcher.update_all_asset_prices, db, asset_class)
        return {
            "status": "started",
            "message": "Price update started in background",
            "asset_class": asset_class,
        }
    else:
        # Run synchronously and return results
        stats = PriceFetcher.update_all_asset_prices(db, asset_class)
        return {
            "status": "completed",
            "message": "Price update completed",
            "asset_class": asset_class,
            "stats": stats,
        }


@router.post("/update/{asset_id}", response_model=dict[str, Any])
async def update_asset_price(asset_id: int, db: Session = Depends(get_db)):
    """
    Update price for a specific asset.

    Args:
        asset_id: The asset ID to update

    Returns:
        Updated asset information
    """
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with id {asset_id} not found"
        )

    if not asset.symbol:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Asset {asset.name} has no symbol"
        )

    success = PriceFetcher.update_asset_price(db, asset)

    if success:
        return {
            "status": "success",
            "message": f"Price updated for {asset.symbol}",
            "asset_id": asset.id,
            "symbol": asset.symbol,
            "price": float(asset.last_fetched_price) if asset.last_fetched_price else None,
            "updated_at": asset.last_price_update.isoformat() if asset.last_price_update else None,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch price for {asset.symbol}",
        )


@router.get("/historical/{symbol}")
async def get_historical_prices(
    symbol: str,
    period: str = "1mo",
    display_currency: str = Query(
        default=None, description="Currency for displaying values (converts from native currency)"
    ),
    db: Session = Depends(get_db),
):
    """
    Get historical price data for a symbol.

    Args:
        symbol: The ticker symbol (e.g., 'AAPL', 'BTC-USD')
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        display_currency: Target currency for price conversion (optional)

    Returns:
        Historical price data (converted to display_currency if specified)
    """
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]

    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}",
        )

    data = PriceFetcher.get_historical_prices(symbol, period)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical data found for symbol {symbol}",
        )

    # Convert to display currency if requested
    if display_currency:
        # Determine native currency from symbol
        # .TA = ILS (Tel Aviv Stock Exchange)
        # Default to USD for others
        if symbol.endswith(".TA"):
            native_currency = "ILS"
        else:
            # Look up asset in database to get currency
            asset = db.query(Asset).filter(Asset.symbol == symbol).first()
            native_currency = asset.currency if asset and asset.currency else "USD"

        if native_currency != display_currency:
            # Convert all prices
            for item in data["data"]:
                for price_field in ["open", "high", "low", "close"]:
                    if item.get(price_field) is not None:
                        converted = CurrencyConversionHelper.convert_value(
                            db,
                            Decimal(str(item[price_field])),
                            native_currency,
                            display_currency,
                        )
                        item[price_field] = float(converted)

        data["currency"] = display_currency
    else:
        # Return native currency info
        if symbol.endswith(".TA"):
            data["currency"] = "ILS"
        else:
            asset = db.query(Asset).filter(Asset.symbol == symbol).first()
            data["currency"] = asset.currency if asset and asset.currency else "USD"

    return data
