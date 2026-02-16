"""Repository layer - data access abstraction.

Repositories handle all database queries, providing a clean interface
for services. Services should use repositories for data access rather
than directly querying SQLAlchemy models.

The Repository pattern separates data access from business logic:
- Repositories: Pure data access (queries, creates, updates)
- Services: Business logic that uses repositories

Dependency direction: Services -> Repositories -> Models
"""

from .account_repository import AccountRepository
from .asset_repository import AssetRepository
from .cash_balance_repository import CashBalanceRepository
from .corporate_action_repository import CorporateActionRepository
from .exchange_rate_repository import ExchangeRateRepository
from .holding_repository import HoldingRepository
from .price_repository import PriceRepository
from .snapshot_repository import SnapshotRepository
from .transaction_repository import TransactionRepository
from .user_repository import UserRepository

__all__ = [
    "AccountRepository",
    "AssetRepository",
    "CashBalanceRepository",
    "CorporateActionRepository",
    "ExchangeRateRepository",
    "HoldingRepository",
    "PriceRepository",
    "SnapshotRepository",
    "TransactionRepository",
    "UserRepository",
]
