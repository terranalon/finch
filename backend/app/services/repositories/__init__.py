"""Repository layer - data access abstraction.

Repositories handle all database queries, providing a clean interface
for services. Services should use repositories for data access rather
than directly querying SQLAlchemy models.

The Repository pattern separates data access from business logic:
- Repositories: Pure data access (queries, creates, updates)
- Services: Business logic that uses repositories

Dependency direction: Services -> Repositories -> Models
"""

from .asset_repository import AssetRepository
from .exceptions import DuplicateError, NotFoundError, RepositoryError
from .holding_repository import HoldingRepository

__all__ = [
    "AssetRepository",
    "DuplicateError",
    "HoldingRepository",
    "NotFoundError",
    "RepositoryError",
]
