"""Prices API router - manage asset price updates."""

from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BadRequestError, NotFoundError
from app.models import Asset
from app.schemas.price import (
    HistoricalPriceResponse,
    PriceUpdateResponse,
)
from app.services.market_data.price_fetcher import PriceFetcher
from app.services.shared.currency_conversion_helper import CurrencyConversionHelper

router = APIRouter(prefix="/api/prices", tags=["prices"])


def _native_currency_for(symbol: str, asset: Asset | None) -> str:
    """Return the native trading currency for a symbol.

    Israeli stocks (.TA) always trade in ILS. For other assets, the
    currency is read from the database record, defaulting to USD.
    """
    if symbol.endswith(".TA"):
        return "ILS"
    if asset and asset.currency:
        return asset.currency
    return "USD"


@router.post("", response_model=PriceUpdateResponse)
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
        background_tasks.add_task(PriceFetcher.update_all_asset_prices, db, asset_class)
        return {
            "status": "started",
            "message": "Price update started in background",
            "asset_class": asset_class,
        }

    stats = PriceFetcher.update_all_asset_prices(db, asset_class)
    return {
        "status": "completed",
        "message": "Price update completed",
        "asset_class": asset_class,
        "stats": stats,
    }


@router.get("/historical/{symbol}", response_model=HistoricalPriceResponse)
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
        raise BadRequestError(f"Invalid period. Must be one of: {', '.join(valid_periods)}")

    asset = db.query(Asset).filter(Asset.symbol == symbol).first()
    is_crypto = asset is not None and asset.asset_class == "Crypto"

    data = PriceFetcher.get_historical_prices(symbol, period, is_crypto=is_crypto)

    if not data:
        raise NotFoundError("Historical data", symbol)

    native_currency = _native_currency_for(symbol, asset)

    if display_currency:
        if native_currency != display_currency:
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
        data["currency"] = native_currency

    return data
