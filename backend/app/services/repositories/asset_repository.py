"""Asset data access layer.

Centralizes all Asset queries to eliminate duplication across import services.
Each import service was implementing its own _find_or_create_asset method with
~100+ lines of duplicated query logic.
"""

import logging
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models import Asset

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class AssetRepository:
    """Centralized asset data access.

    Naming conventions (from API Design Principles):
    - find_* : Query that may return None
    - get_* : Query that raises NotFoundError if missing
    - create_* : Insert new record
    - update_* : Modify existing record
    - find_or_create_* : Upsert pattern
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, asset_id: int) -> Asset | None:
        """Find asset by primary key."""
        return self._db.query(Asset).filter(Asset.id == asset_id).first()

    def find_by_symbol(self, symbol: str) -> Asset | None:
        """Find asset by ticker symbol (exact match, case-sensitive)."""
        return self._db.query(Asset).filter(Asset.symbol == symbol).first()

    def find_by_symbol_insensitive(self, symbol: str) -> Asset | None:
        """Find asset by ticker symbol (case-insensitive)."""
        return self._db.query(Asset).filter(Asset.symbol.ilike(symbol)).first()

    def find_by_symbols(self, symbols: list[str]) -> "Sequence[Asset]":
        """Find multiple assets by symbols."""
        return self._db.query(Asset).filter(Asset.symbol.in_(symbols)).all()

    def find_by_tase_security_number(self, tase_security_number: str) -> Asset | None:
        """Find asset by Israeli security number (TASE)."""
        return (
            self._db.query(Asset).filter(Asset.tase_security_number == tase_security_number).first()
        )

    def find_by_conid(self, conid: str) -> Asset | None:
        """Find asset by IBKR contract ID."""
        return self._db.query(Asset).filter(Asset.conid == conid).first()

    def find_by_cusip(self, cusip: str) -> Asset | None:
        """Find asset by CUSIP identifier."""
        return self._db.query(Asset).filter(Asset.cusip == cusip).first()

    def find_by_isin(self, isin: str) -> Asset | None:
        """Find asset by ISIN identifier."""
        return self._db.query(Asset).filter(Asset.isin == isin).first()

    def find_or_create(
        self,
        symbol: str,
        *,
        name: str | None = None,
        asset_class: str | None = None,
        currency: str = "USD",
        category: str | None = None,
        industry: str | None = None,
        cusip: str | None = None,
        isin: str | None = None,
        conid: str | None = None,
        figi: str | None = None,
        tase_security_number: str | None = None,
        data_source: str | None = None,
    ) -> tuple[Asset, bool]:
        """Find existing asset or create new one.

        This is the basic find_or_create - it does NOT fetch metadata from
        external sources. That responsibility belongs to the import services
        which know what data source is appropriate for each asset type.

        Returns:
            Tuple of (asset, created) where created is True if new record.
        """
        existing = self.find_by_symbol(symbol)
        if existing:
            return existing, False

        asset = Asset(
            symbol=symbol.upper() if symbol else symbol,
            name=name or symbol,
            asset_class=asset_class,
            currency=currency,
            category=category,
            industry=industry,
            cusip=cusip,
            isin=isin,
            conid=conid,
            figi=figi,
            tase_security_number=tase_security_number,
            data_source=data_source,
        )
        self._db.add(asset)
        self._db.flush()
        logger.info(f"Created asset {symbol} with ID {asset.id}")
        return asset, True

    def update_identifiers(
        self,
        asset: Asset,
        *,
        cusip: str | None = None,
        isin: str | None = None,
        conid: str | None = None,
        figi: str | None = None,
        tase_security_number: str | None = None,
    ) -> bool:
        """Update permanent identifiers if they're missing.

        Returns:
            True if any field was updated.
        """
        updated = False

        if cusip and not asset.cusip:
            asset.cusip = cusip
            updated = True
        if isin and not asset.isin:
            asset.isin = isin
            updated = True
        if conid and not asset.conid:
            asset.conid = conid
            updated = True
        if figi and not asset.figi:
            asset.figi = figi
            updated = True
        if tase_security_number and not asset.tase_security_number:
            asset.tase_security_number = tase_security_number
            updated = True

        if updated:
            self._db.flush()
            logger.debug(f"Updated identifiers for {asset.symbol}")

        return updated

    def update_metadata(
        self,
        asset: Asset,
        *,
        name: str | None = None,
        asset_class: str | None = None,
        category: str | None = None,
        industry: str | None = None,
        currency: str | None = None,
    ) -> Asset:
        """Update asset metadata fields (only non-None values)."""
        if name is not None:
            asset.name = name
        if asset_class is not None:
            asset.asset_class = asset_class
        if category is not None:
            asset.category = category
        if industry is not None:
            asset.industry = industry
        if currency is not None:
            asset.currency = currency
        self._db.flush()
        return asset

    def update_symbol(self, asset: Asset, new_symbol: str) -> Asset:
        """Update asset symbol (e.g., for ticker changes)."""
        old_symbol = asset.symbol
        asset.symbol = new_symbol
        self._db.flush()
        logger.info(f"Updated symbol: {old_symbol} -> {new_symbol}")
        return asset
