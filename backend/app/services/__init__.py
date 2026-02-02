"""Services layer - business logic and external integrations.

This module is organized into domain-based subpackages:
- auth/: Authentication and authorization
- brokers/: Broker integrations (IBKR, Kraken, etc.)
- market_data/: External market data providers
- portfolio/: Portfolio management and reconstruction
- repositories/: Data access layer
- shared/: Shared utilities

Common imports for convenience:
    from app.services import AssetRepository, HoldingRepository
    from app.services import MarketDataService, PriceFetcher
    from app.services import BrokerParserRegistry, BrokerImportServiceRegistry
"""

# Re-export commonly used components for convenience
from app.services.repositories import (
    AssetRepository,
    DuplicateError,
    HoldingRepository,
    NotFoundError,
    RepositoryError,
)

__all__ = [
    # Repositories
    "AssetRepository",
    "DuplicateError",
    "HoldingRepository",
    "NotFoundError",
    "RepositoryError",
]
