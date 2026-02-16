"""Asset metadata enrichment service for fetching company information from external sources."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset
from app.services.market_data.yfinance_client import TickerInfo, YFinanceClient

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

    @staticmethod
    def fetch_name_from_yfinance(
        symbol: str, asset_class: str | None = None
    ) -> AssetMetadataResult:
        """Fetch company name and category from Yahoo Finance via YFinanceClient."""
        try:
            client = YFinanceClient()
            info = client.get_ticker_info(symbol)
            return AssetMetadataService.from_ticker_info(symbol, info, asset_class)
        except Exception as e:
            logger.error("Error fetching metadata for %s: %s", symbol, e)
            return AssetMetadataResult(
                symbol=symbol,
                name=None,
                category=None,
                industry=None,
                source="error",
                error=str(e),
            )

    @staticmethod
    def from_ticker_info(
        symbol: str, info: TickerInfo | None, asset_class: str | None = None
    ) -> AssetMetadataResult:
        """Build AssetMetadataResult from pre-fetched TickerInfo."""
        if info is None:
            return AssetMetadataResult(
                symbol=symbol,
                name=None,
                category=None,
                industry=None,
                source="not_found",
                error="Symbol not found in Yahoo Finance",
            )

        is_etf = asset_class == "ETF" or info.quote_type == "ETF"
        category = info.category if is_etf else info.sector
        industry = None if is_etf else info.industry

        if info.name:
            logger.info(
                "Found metadata for %s: name='%s', category='%s', industry='%s'",
                symbol,
                info.name,
                category,
                industry,
            )
            return AssetMetadataResult(
                symbol=symbol,
                name=info.name,
                category=category,
                industry=industry,
                source="yfinance",
            )

        logger.warning("No name fields found for %s", symbol)
        return AssetMetadataResult(
            symbol=symbol,
            name=None,
            category=category,
            industry=industry,
            source="not_found",
            error="No name fields in Yahoo Finance response",
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
