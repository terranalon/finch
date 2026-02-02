"""Base class for broker import services.

Defines the abstract interface that all broker-specific import services
must implement. The import service registry uses this interface to work
with different broker types uniformly.

This module also provides shared utility methods that all import services need,
following the DRY principle to eliminate code duplication across:
- IsraeliSecuritiesImportService
- CryptoImportService
- IBKRImportService (when converted to proper service class)
"""

import logging
from abc import ABC, abstractmethod
from datetime import date as date_type
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Asset, Holding
    from app.services.brokers.base_broker_parser import BrokerImportData
    from app.services.repositories import AssetRepository, HoldingRepository

logger = logging.getLogger(__name__)


def extract_date_range(dates: list[date_type]) -> dict[str, date_type] | None:
    """Extract min/max date range from a list of dates.

    Args:
        dates: List of date objects (None values are filtered out)

    Returns:
        Dict with 'start_date' and 'end_date' as date objects, or None if no valid dates
    """
    valid_dates = [d for d in dates if d is not None]
    if not valid_dates:
        return None
    return {
        "start_date": min(valid_dates),
        "end_date": max(valid_dates),
    }


def extract_date_range_serializable(dates: list[date_type]) -> dict[str, str] | None:
    """Extract min/max date range as ISO strings (for JSON serialization).

    Args:
        dates: List of date objects (None values are filtered out)

    Returns:
        Dict with 'start_date' and 'end_date' as ISO strings, or None if no valid dates
    """
    date_range = extract_date_range(dates)
    if not date_range:
        return None
    return {
        "start_date": date_range["start_date"].isoformat(),
        "end_date": date_range["end_date"].isoformat(),
    }


def extract_unique_symbols(
    *data_lists: list[dict],
    key: str = "symbol",
) -> set[str]:
    """Extract unique symbols from multiple data lists.

    Args:
        *data_lists: Variable number of lists containing dicts with symbol key
        key: The key to extract from each dict (default: 'symbol')

    Returns:
        Set of unique symbol strings
    """
    symbols = set()
    for data_list in data_lists:
        for item in data_list:
            if symbol := item.get(key):
                symbols.add(symbol)
    return symbols


class BaseBrokerImportService(ABC):
    """Abstract base class for all broker import services.

    Each broker import service (Israeli Securities, Crypto, etc.) should inherit from
    this class to provide consistent import capabilities.

    Provides shared utility methods for:
    - Asset find/create operations via AssetRepository
    - Holding find/create operations via HoldingRepository
    - Standard import stats structure
    - Holdings reconstruction

    Example usage:
        service = IsraeliSecuritiesImportService(db, "meitav")
        stats = service.import_data(account_id, parsed_data, source_id=123)
    """

    def __init__(self, db: "Session", broker_type: str) -> None:
        """Initialize with database session and broker type.

        Args:
            db: SQLAlchemy database session
            broker_type: Broker type identifier (e.g., 'meitav', 'kraken')
        """
        self.db = db
        self.broker_type = broker_type
        # Lazy-initialize repositories to avoid circular imports
        self._asset_repo = None
        self._holding_repo = None

    @property
    def asset_repo(self) -> "AssetRepository":
        """Lazy-loaded AssetRepository instance."""
        if self._asset_repo is None:
            from app.services.repositories import AssetRepository

            self._asset_repo = AssetRepository(self.db)
        return self._asset_repo

    @property
    def holding_repo(self) -> "HoldingRepository":
        """Lazy-loaded HoldingRepository instance."""
        if self._holding_repo is None:
            from app.services.repositories import HoldingRepository

            self._holding_repo = HoldingRepository(self.db)
        return self._holding_repo

    @classmethod
    @abstractmethod
    def supported_broker_types(cls) -> list[str]:
        """Return list of broker types this service handles.

        Returns:
            List of broker type identifiers (e.g., ['kraken', 'bit2c', 'binance'])
        """
        pass

    @abstractmethod
    def import_data(
        self,
        account_id: int,
        data: "BrokerImportData",
        source_id: int | None = None,
    ) -> dict:
        """Import broker data and return statistics dict.

        Args:
            account_id: Account ID to import data into
            data: Parsed broker data from parser
            source_id: Optional broker source ID for tracking import lineage

        Returns:
            Statistics dictionary with import results including:
            - positions: dict with position import stats
            - transactions: dict with transaction import stats
            - cash_transactions: dict with cash transaction import stats
            - dividends: dict with dividend import stats
            - holdings_reconstruction: dict with holdings reconstruction stats
            - errors: list of error messages
            - status: 'completed' or 'failed'
        """
        pass

    # -------------------------------------------------------------------------
    # Shared utility methods - available to all import services
    # -------------------------------------------------------------------------

    def _create_import_stats(self) -> dict:
        """Create standard statistics structure for import operations.

        Returns:
            Dictionary with zeroed counters for all import stat categories.
            Use this as the starting point for tracking import progress.
        """
        return {
            "positions": {"total": 0, "imported": 0, "skipped": 0, "errors": []},
            "transactions": {
                "total": 0,
                "imported": 0,
                "transferred": 0,
                "skipped": 0,
                "errors": [],
            },
            "cash_transactions": {"total": 0, "imported": 0, "skipped": 0, "errors": []},
            "dividends": {"total": 0, "imported": 0, "skipped": 0, "errors": []},
            "holdings_reconstruction": {},
            "errors": [],
            "status": "pending",
        }

    def _find_or_create_holding_for_asset(
        self,
        account_id: int,
        asset: "Asset",
        initial_quantity: Decimal = Decimal("0"),
        initial_cost_basis: Decimal = Decimal("0"),
    ) -> "Holding":
        """Find or create a holding for the given account and asset.

        This is a convenience wrapper around holding_repo.find_or_create
        that takes an Asset object instead of asset_id.

        Args:
            account_id: Account ID
            asset: Asset object (must have id set)
            initial_quantity: Initial quantity if creating new holding
            initial_cost_basis: Initial cost basis if creating new holding

        Returns:
            Holding object (existing or newly created)
        """
        holding, created = self.holding_repo.find_or_create(
            account_id=account_id,
            asset_id=asset.id,
            quantity=initial_quantity,
            cost_basis=initial_cost_basis,
        )
        if created:
            logger.debug(f"Created holding for {asset.symbol} in account {account_id}")
        return holding

    def _reconstruct_holdings(
        self,
        account_id: int,
        data_source_ids: list[int] | None = None,
    ) -> dict:
        """Reconstruct holdings from transactions.

        Replays all transactions to calculate current quantities and cost basis,
        then updates the Holding records accordingly.

        Args:
            account_id: Account ID to reconstruct holdings for
            data_source_ids: Optional list of data source IDs to filter by

        Returns:
            Statistics dictionary from holdings reconstruction
        """
        from app.services.portfolio.holdings_reconstruction import reconstruct_and_update_holdings

        return reconstruct_and_update_holdings(self.db, account_id, data_source_ids=data_source_ids)
