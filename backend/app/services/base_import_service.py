"""Base class for broker import services.

Defines the abstract interface that all broker-specific import services
must implement. The import service registry uses this interface to work
with different broker types uniformly.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.base_broker_parser import BrokerImportData


class BaseBrokerImportService(ABC):
    """Abstract base class for all broker import services.

    Each broker import service (Meitav, Crypto, etc.) should inherit from
    this class to provide consistent import capabilities.

    Example usage:
        service = MeitavImportService(db, "meitav")
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
