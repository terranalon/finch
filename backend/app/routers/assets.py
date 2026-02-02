"""Assets API router."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Asset, AssetPrice, ExchangeRate
from app.schemas.asset import Asset as AssetSchema
from app.schemas.asset import AssetCreate, AssetUpdate
from app.services.shared.asset_metadata_service import AssetMetadataService
from app.services.shared.currency_service import CurrencyService

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=list[AssetSchema])
async def list_assets(
    skip: int = 0, limit: int = 100, asset_class: str = None, db: Session = Depends(get_db)
):
    """
    Get list of assets.

    Query Parameters:
        - skip: Number of records to skip (pagination)
        - limit: Maximum number of records to return
        - asset_class: Filter by asset class
    """
    query = db.query(Asset)

    if asset_class is not None:
        query = query.filter(Asset.asset_class == asset_class)

    assets = query.order_by(Asset.symbol).offset(skip).limit(limit).all()
    return assets


@router.get("/market")
async def list_assets_with_changes(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    asset_class: str = None,
    display_currency: str = Query(default="USD", pattern="^[A-Z]{3}$"),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Get list of assets with price change data.

    Returns assets with computed day/week/month price changes based on
    historical price data from the asset_prices table.

    For Cash/Forex assets, shows exchange rate to the display currency.

    Query Parameters:
        - skip: Number of records to skip (pagination)
        - limit: Maximum number of records to return (max 500)
        - asset_class: Filter by asset class
        - display_currency: Currency for displaying forex rates (default: USD)
    """
    query = db.query(Asset)

    if asset_class is not None:
        query = query.filter(Asset.asset_class == asset_class)

    assets = query.order_by(Asset.symbol).offset(skip).limit(limit).all()

    # Get reference dates for price comparison
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # Collect all asset IDs and identify Cash assets
    asset_ids = [a.id for a in assets]
    cash_currencies = [a.currency for a in assets if a.asset_class == "Cash"]

    # Fetch historical prices for all non-Cash assets in one query
    price_data = {}
    if asset_ids:
        # Get prices for the past month for all assets
        prices = (
            db.query(AssetPrice)
            .filter(
                AssetPrice.asset_id.in_(asset_ids),
                AssetPrice.date >= month_ago,
            )
            .order_by(AssetPrice.asset_id, desc(AssetPrice.date))
            .all()
        )

        # Organize prices by asset_id
        for price in prices:
            if price.asset_id not in price_data:
                price_data[price.asset_id] = []
            price_data[price.asset_id].append(price)

    # Fetch historical exchange rates for Cash/Forex assets
    fx_rate_data = {}
    if cash_currencies:
        # Get exchange rates for the past month for all cash currencies
        fx_rates = (
            db.query(ExchangeRate)
            .filter(
                ExchangeRate.from_currency.in_(cash_currencies),
                ExchangeRate.to_currency == display_currency,
                ExchangeRate.date >= month_ago,
            )
            .order_by(ExchangeRate.from_currency, desc(ExchangeRate.date))
            .all()
        )

        # Organize rates by currency
        for rate in fx_rates:
            if rate.from_currency not in fx_rate_data:
                fx_rate_data[rate.from_currency] = []
            fx_rate_data[rate.from_currency].append(rate)

    result = []
    for asset in assets:
        # Handle Cash/Forex assets specially - use exchange rates
        if asset.asset_class == "Cash":
            asset_currency = asset.currency

            # Skip if this is the same as display currency (rate would be 1.0)
            if asset_currency == display_currency:
                current_price = Decimal("1.0")
                change_1d, change_1d_pct = None, None
                change_1w, change_1w_pct = None, None
                change_1m, change_1m_pct = None, None
            else:
                # Get current exchange rate (this will fetch from Yahoo if not cached)
                current_price = CurrencyService.get_exchange_rate(
                    db, asset_currency, display_currency, today
                )

                # Get historical rates from our cached data
                currency_rates = fx_rate_data.get(asset_currency, [])

                rate_1d_ago = None
                rate_1w_ago = None
                rate_1m_ago = None

                for r in currency_rates:
                    if rate_1d_ago is None and r.date <= yesterday:
                        rate_1d_ago = r.rate
                    if rate_1w_ago is None and r.date <= week_ago:
                        rate_1w_ago = r.rate
                    if rate_1m_ago is None and r.date <= month_ago:
                        rate_1m_ago = r.rate
                    if rate_1d_ago and rate_1w_ago and rate_1m_ago:
                        break

                # Calculate changes
                def calc_fx_change(current: Decimal | None, previous: Decimal | None) -> tuple:
                    if current is None or previous is None or previous == 0:
                        return (None, None)
                    change = current - previous
                    change_pct = (change / previous) * 100
                    return (float(change), float(change_pct))

                change_1d, change_1d_pct = calc_fx_change(current_price, rate_1d_ago)
                change_1w, change_1w_pct = calc_fx_change(current_price, rate_1w_ago)
                change_1m, change_1m_pct = calc_fx_change(current_price, rate_1m_ago)

            # Build result for Cash asset
            result.append(
                {
                    "id": asset.id,
                    "symbol": asset.symbol,
                    "name": f"{asset_currency}/{display_currency}"
                    if asset_currency != display_currency
                    else asset.name,
                    "asset_class": asset.asset_class,
                    "category": asset.category or "Forex",
                    "industry": asset.industry,
                    "currency": display_currency,  # Show in display currency
                    "is_favorite": asset.is_favorite,
                    "last_fetched_price": float(current_price) if current_price else None,
                    "last_fetched_at": asset.last_fetched_at.isoformat()
                    if asset.last_fetched_at
                    else None,
                    "data_source": asset.data_source,
                    "change_1d": change_1d,
                    "change_1d_pct": change_1d_pct,
                    "change_1w": change_1w,
                    "change_1w_pct": change_1w_pct,
                    "change_1m": change_1m,
                    "change_1m_pct": change_1m_pct,
                }
            )
            continue

        # Non-Cash asset handling
        current_price = asset.last_fetched_price
        asset_prices = price_data.get(asset.id, [])

        # Find prices for different time periods
        price_1d_ago = None
        price_1w_ago = None
        price_1m_ago = None

        for p in asset_prices:
            # Find price from ~1 day ago (yesterday or most recent before today)
            if price_1d_ago is None and p.date <= yesterday:
                price_1d_ago = p.closing_price
            # Find price from ~1 week ago
            if price_1w_ago is None and p.date <= week_ago:
                price_1w_ago = p.closing_price
            # Find price from ~1 month ago
            if price_1m_ago is None and p.date <= month_ago:
                price_1m_ago = p.closing_price
            # Once we have all prices, we can stop
            if price_1d_ago and price_1w_ago and price_1m_ago:
                break

        # Calculate changes
        def calc_change(current: Decimal | None, previous: Decimal | None) -> tuple:
            if current is None or previous is None or previous == 0:
                return (None, None)
            change = current - previous
            change_pct = (change / previous) * 100
            return (float(change), float(change_pct))

        change_1d, change_1d_pct = calc_change(current_price, price_1d_ago)
        change_1w, change_1w_pct = calc_change(current_price, price_1w_ago)
        change_1m, change_1m_pct = calc_change(current_price, price_1m_ago)

        result.append(
            {
                "id": asset.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_class": asset.asset_class,
                "category": asset.category,
                "industry": asset.industry,
                "currency": asset.currency,
                "is_favorite": asset.is_favorite,
                "last_fetched_price": float(asset.last_fetched_price)
                if asset.last_fetched_price
                else None,
                "last_fetched_at": asset.last_fetched_at.isoformat()
                if asset.last_fetched_at
                else None,
                "data_source": asset.data_source,
                "change_1d": change_1d,
                "change_1d_pct": change_1d_pct,
                "change_1w": change_1w,
                "change_1w_pct": change_1w_pct,
                "change_1m": change_1m,
                "change_1m_pct": change_1m_pct,
            }
        )

    return result


@router.get("/search", response_model=list[AssetSchema])
async def search_assets(q: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    Search assets by symbol or name (for autocomplete).

    Query Parameters:
        - q: Search query (symbol or name)
        - limit: Maximum number of results to return (default: 10)
    """
    search_term = f"%{q}%"

    assets = (
        db.query(Asset)
        .filter(or_(Asset.symbol.ilike(search_term), Asset.name.ilike(search_term)))
        .order_by(Asset.symbol)
        .limit(limit)
        .all()
    )

    return assets


@router.get("/{asset_id}", response_model=AssetSchema)
async def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """Get a specific asset by ID."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with id {asset_id} not found"
        )

    return asset


@router.post("", response_model=AssetSchema, status_code=status.HTTP_201_CREATED)
async def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    """Create a new asset.

    If the name equals the symbol, automatically fetches the full company name
    from Yahoo Finance. If a custom name is provided, it is used as-is.
    """
    # Check if asset with same symbol already exists
    existing = db.query(Asset).filter(Asset.symbol == asset.symbol).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset with symbol '{asset.symbol}' already exists",
        )

    asset_data = asset.model_dump()

    # Set default category for Cash assets
    if asset.asset_class == "Cash" and not asset.category:
        asset_data["category"] = "Cash"

    # Auto-resolve name/category/industry from Yahoo Finance if user just provided the symbol
    # as name, or if category/industry is not provided
    should_fetch = asset.asset_class != "Cash" and (
        asset.name == asset.symbol or not asset.category or not asset.industry
    )
    if should_fetch:
        metadata_result = AssetMetadataService.fetch_name_from_yfinance(
            asset.symbol, asset.asset_class
        )
        # Only override name if user provided symbol as name
        if asset.name == asset.symbol and metadata_result.name:
            asset_data["name"] = metadata_result.name
        # Set category if available and not provided by user
        if not asset.category and metadata_result.category:
            asset_data["category"] = metadata_result.category
        # Set industry if available and not provided by user
        if not asset.industry and metadata_result.industry:
            asset_data["industry"] = metadata_result.industry
        # Track metadata source
        if metadata_result.name or metadata_result.category or metadata_result.industry:
            meta = asset_data.get("meta_data") or {}
            meta["metadata_source"] = "yfinance"
            asset_data["meta_data"] = meta

    db_asset = Asset(**asset_data)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


@router.put("/{asset_id}", response_model=AssetSchema)
async def update_asset(asset_id: int, asset_update: AssetUpdate, db: Session = Depends(get_db)):
    """Update an existing asset."""
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with id {asset_id} not found"
        )

    # Update only provided fields
    update_data = asset_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_asset, field, value)

    db.commit()
    db.refresh(db_asset)
    return db_asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """Delete an asset."""
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with id {asset_id} not found"
        )

    db.delete(db_asset)
    db.commit()
    return None


@router.post("/{asset_id}/favorite", response_model=AssetSchema)
async def toggle_favorite(asset_id: int, db: Session = Depends(get_db)):
    """Toggle the favorite status of an asset."""
    db_asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset with id {asset_id} not found"
        )

    db_asset.is_favorite = not db_asset.is_favorite
    db.commit()
    db.refresh(db_asset)
    return db_asset


@router.get("/favorites/list", response_model=list[AssetSchema])
async def list_favorites(db: Session = Depends(get_db)):
    """Get all favorite assets."""
    favorites = db.query(Asset).filter(Asset.is_favorite.is_(True)).order_by(Asset.symbol).all()
    return favorites
