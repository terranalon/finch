"""Market data refresh endpoints for Airflow DAG integration."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.market_data import (
    ExchangeRateRefreshResponse,
    PriceRefreshResponse,
)
from app.services.market_data.daily_price_service import DailyPriceService
from app.services.market_data.exchange_rate_service import ExchangeRateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


def _get_target_date(date_param: date | None) -> date:
    """Get target date, defaulting to yesterday."""
    return date_param if date_param is not None else date.today() - timedelta(days=1)


def _require_service_account(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency that verifies the current user is a service account."""
    if not current_user.is_service_account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires service account access",
        )
    return current_user


@router.post("/exchange-rates/refresh", response_model=ExchangeRateRefreshResponse)
def refresh_exchange_rates(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_service_account),
) -> ExchangeRateRefreshResponse:
    """Refresh exchange rates for all supported currency pairs.

    Fetches rates from yfinance and stores them in the database.
    Idempotent: skips pairs that already have rates for the target date.
    """
    resolved_date = _get_target_date(target_date)

    logger.info("Refreshing exchange rates for %s", resolved_date)
    result = ExchangeRateService.refresh(db, resolved_date)

    return ExchangeRateRefreshResponse.model_validate(result)


@router.post("/stock-prices/refresh", response_model=PriceRefreshResponse)
def refresh_stock_prices(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_service_account),
) -> PriceRefreshResponse:
    """Refresh closing prices for non-crypto assets.

    Fetches prices from Yahoo Finance and stores them in the database.
    Idempotent: skips assets that already have prices for the target date.
    """
    resolved_date = _get_target_date(target_date)

    logger.info("Refreshing stock prices for %s", resolved_date)
    result = DailyPriceService.refresh_stock_prices(db, resolved_date)

    return PriceRefreshResponse.model_validate(result)


@router.post("/crypto-prices/refresh", response_model=PriceRefreshResponse)
def refresh_crypto_prices(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(_require_service_account),
) -> PriceRefreshResponse:
    """Refresh prices for crypto assets.

    Uses CoinGecko for recent dates (<1 year), CryptoCompare for older dates.
    Idempotent: skips assets that already have prices for the target date.
    """
    resolved_date = _get_target_date(target_date)

    logger.info("Refreshing crypto prices for %s", resolved_date)
    result = DailyPriceService.refresh_crypto_prices(db, resolved_date)

    return PriceRefreshResponse.model_validate(result)
