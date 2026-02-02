"""Asset metadata enrichment service for fetching company information from external sources."""

import logging
from dataclasses import dataclass
from datetime import datetime

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset

logger = logging.getLogger(__name__)


@dataclass
class AssetMetadataResult:
    """Result of a metadata lookup attempt."""

    symbol: str
    name: str | None
    category: str | None  # Sector for stocks, Category for ETFs
    industry: str | None
    source: str  # 'yfinance', 'not_found', 'error'
    error: str | None = None


# Backwards compatibility alias
AssetNameResult = AssetMetadataResult


class AssetMetadataService:
    """Service for enriching asset metadata from external sources."""

    # Asset classes that should be skipped
    SKIP_ASSET_CLASSES = {"Cash"}

    # Fields to try for company name, in order of preference
    NAME_FIELDS = ["longName", "shortName", "name"]

    @staticmethod
    def fetch_name_from_yfinance(
        symbol: str, asset_class: str | None = None
    ) -> AssetMetadataResult:
        """
        Fetch company name and category for a symbol from Yahoo Finance.

        For stocks: category = sector (e.g., "Technology")
        For ETFs: category = category (e.g., "Large Blend")

        Args:
            symbol: The ticker symbol (e.g., 'AAPL', 'MSFT')
            asset_class: Optional asset class to determine which field to use

        Returns:
            AssetMetadataResult with name, category, or error information
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Handle empty response (symbol not found)
            if not info or info.get("regularMarketPrice") is None:
                logger.warning(f"No data found for symbol {symbol}")
                return AssetMetadataResult(
                    symbol=symbol,
                    name=None,
                    category=None,
                    industry=None,
                    source="not_found",
                    error="Symbol not found in Yahoo Finance",
                )

            # Determine if this is an ETF based on asset_class or quoteType
            is_etf = asset_class == "ETF" or info.get("quoteType") == "ETF"

            # Extract category: use 'category' for ETFs, 'sector' for stocks
            if is_etf:
                category = info.get("category")
            else:
                category = info.get("sector")

            # Industry only applies to stocks (not ETFs)
            industry = None if is_etf else info.get("industry")

            # Try different name fields
            name = None
            for field in AssetMetadataService.NAME_FIELDS:
                if field in info and info[field]:
                    name = info[field].strip()
                    if name and name != symbol:  # Avoid setting name to symbol
                        break
                    name = None

            if name:
                logger.info(
                    f"Found metadata for {symbol}: name='{name}', "
                    f"category='{category}', industry='{industry}'"
                )
                return AssetMetadataResult(
                    symbol=symbol,
                    name=name,
                    category=category,
                    industry=industry,
                    source="yfinance",
                )

            logger.warning(f"No name fields found for {symbol}")
            return AssetMetadataResult(
                symbol=symbol,
                name=None,
                category=category,
                industry=industry,
                source="not_found",
                error="No name fields in Yahoo Finance response",
            )

        except Exception as e:
            logger.error(f"Error fetching metadata for {symbol}: {e!s}")
            return AssetMetadataResult(
                symbol=symbol,
                name=None,
                category=None,
                industry=None,
                source="error",
                error=str(e),
            )

    @staticmethod
    def should_update_name(asset: Asset, force: bool = False) -> bool:
        """
        Determine if an asset's name should be updated.

        Args:
            asset: The Asset model instance
            force: If True, update regardless of current name

        Returns:
            True if the name should be updated
        """
        # Never update manual valuation assets
        if asset.is_manual_valuation:
            return False

        # Skip cash assets
        if asset.asset_class in AssetMetadataService.SKIP_ASSET_CLASSES:
            return False

        # Force update overrides other checks
        if force:
            return True

        # Update if name equals symbol (the problem we're solving)
        if asset.name == asset.symbol:
            return True

        # Update if name is empty or None
        if not asset.name or asset.name.strip() == "":
            return True

        return False

    @staticmethod
    def update_asset_metadata(
        db: Session,
        asset: Asset,
        name: str | None = None,
        category: str | None = None,
        industry: str | None = None,
        source: str = "yfinance",
    ) -> None:
        """
        Update an asset's name, category, and/or industry, tracking the source in metadata.

        Args:
            db: Database session
            asset: Asset to update
            name: New name to set (if provided)
            category: New category to set (if provided) - sector for stocks, category for ETFs
            industry: New industry to set (if provided)
            source: Source of the data (e.g., 'yfinance')
        """
        updates = []

        if name:
            asset.name = name
            updates.append(f"name='{name}'")

        if category:
            asset.category = category
            updates.append(f"category='{category}'")

        if industry:
            asset.industry = industry
            updates.append(f"industry='{industry}'")

        # Update metadata to track source
        meta = asset.meta_data or {}
        meta["metadata_source"] = source
        meta["metadata_updated_at"] = datetime.now().isoformat()
        asset.meta_data = meta

        db.commit()
        logger.info(f"Updated {asset.symbol}: {', '.join(updates)} (source: {source})")

    # Backwards compatibility alias
    @staticmethod
    def update_asset_name(db: Session, asset: Asset, name: str, source: str = "yfinance") -> None:
        """Backwards compatible wrapper for update_asset_metadata."""
        AssetMetadataService.update_asset_metadata(db, asset, name=name, source=source)

    @staticmethod
    def update_all_asset_metadata(
        db: Session,
        force: bool = False,
        dry_run: bool = False,
        asset_class: str | None = None,
    ) -> dict[str, int | list[str]]:
        """
        Update names and categories for all assets that need updating.

        Args:
            db: Database session
            force: If True, update all assets regardless of current name
            dry_run: If True, don't actually make changes
            asset_class: Optional filter for specific asset class

        Returns:
            Dictionary with update statistics
        """
        query = select(Asset)

        if asset_class:
            query = query.where(Asset.asset_class == asset_class)

        assets = db.execute(query).scalars().all()

        stats: dict[str, int | list[str]] = {
            "total": len(assets),
            "updated": 0,
            "skipped": 0,
            "not_found": 0,
            "errors": 0,
            "error_symbols": [],
            "not_found_symbols": [],
            "updated_symbols": [],
        }

        for asset in assets:
            if not AssetMetadataService.should_update_name(asset, force):
                stats["skipped"] += 1
                logger.debug(f"Skipping {asset.symbol}: metadata update not needed")
                continue

            result = AssetMetadataService.fetch_name_from_yfinance(asset.symbol, asset.asset_class)

            if result.name or result.category or result.industry:
                if not dry_run:
                    AssetMetadataService.update_asset_metadata(
                        db,
                        asset,
                        name=result.name,
                        category=result.category,
                        industry=result.industry,
                        source=result.source,
                    )
                stats["updated"] += 1
                update_desc = (
                    f"{asset.symbol} -> name='{result.name}', "
                    f"category='{result.category}', industry='{result.industry}'"
                )
                stats["updated_symbols"].append(update_desc)
            elif result.source == "not_found":
                stats["not_found"] += 1
                stats["not_found_symbols"].append(asset.symbol)
            else:
                stats["errors"] += 1
                stats["error_symbols"].append(f"{asset.symbol}: {result.error}")

        logger.info(f"Asset metadata update complete: {stats}")
        return stats

    # Backwards compatibility alias
    update_all_asset_names = update_all_asset_metadata
