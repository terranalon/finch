"""Interactive Brokers integration.

IBKR provides two import methods:
1. Flex Query XML reports (via IBKRFlexImportService)
2. Activity statement CSV files (via IBKRParser)

The Flex client handles API communication for automatic report retrieval.
"""

from .flex_client import IBKRFlexClient
from .flex_import_service import IBKRFlexImportService
from .import_service import IBKRImportService
from .parser import IBKRParser
from .parser_adapter import IBKRParserAdapter
from .validation_service import IBKRValidationService

__all__ = [
    "IBKRFlexClient",
    "IBKRFlexImportService",
    "IBKRImportService",
    "IBKRParser",
    "IBKRParserAdapter",
    "IBKRValidationService",
]
