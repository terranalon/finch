"""Registry for broker import services.

Maps broker types to their import service implementations and provides
factory methods for getting service instances.
"""

import logging
from typing import TYPE_CHECKING

from app.services.base_import_service import BaseBrokerImportService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class BrokerImportServiceRegistry:
    """Registry for broker import services.

    Provides factory methods to get import service instances based on broker type.
    Services are registered lazily on first access to avoid circular imports.

    Example usage:
        service = BrokerImportServiceRegistry.get_import_service('meitav', db)
        stats = service.import_data(account_id, parsed_data, source_id=123)
    """

    _services: dict[str, type[BaseBrokerImportService]] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Lazily initialize the service registry."""
        if cls._initialized:
            return

        # Import services here to avoid circular imports
        from app.services.crypto_import_service import CryptoImportService
        from app.services.meitav_import_service import MeitavImportService

        # Register services - each service declares which broker types it handles
        for service_class in [MeitavImportService, CryptoImportService]:
            for broker_type in service_class.supported_broker_types():
                cls._services[broker_type] = service_class

        cls._initialized = True
        logger.info("Import service registry initialized with %d broker types", len(cls._services))

    @classmethod
    def get_import_service(cls, broker_type: str, db: "Session") -> BaseBrokerImportService:
        """Get an import service instance for the specified broker type.

        Args:
            broker_type: Broker type identifier (e.g., 'meitav', 'kraken')
            db: SQLAlchemy database session

        Returns:
            Import service instance for the broker

        Raises:
            ValueError: If broker type is not supported
        """
        cls._ensure_initialized()

        if broker_type not in cls._services:
            supported = list(cls._services.keys())
            raise ValueError(
                f"No import service for broker type '{broker_type}'. Supported: {supported}"
            )

        service_class = cls._services[broker_type]
        return service_class(db, broker_type)

    @classmethod
    def is_supported(cls, broker_type: str) -> bool:
        """Check if a broker type has a registered import service.

        Args:
            broker_type: Broker type to check

        Returns:
            True if broker type has a registered import service
        """
        cls._ensure_initialized()
        return broker_type in cls._services

    @classmethod
    def get_supported_broker_types(cls) -> list[str]:
        """Get list of supported broker type identifiers.

        Returns:
            List of broker type strings
        """
        cls._ensure_initialized()
        return list(cls._services.keys())
