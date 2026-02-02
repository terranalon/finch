"""Shared utilities and base classes for services layer.

This module provides foundational components used across multiple services:
- HTTPClient: Base class for all external API clients with retry logic
- HTTPClientError: Exception for HTTP client failures
- Various utility services for transactions, currency, dates, etc.
"""

from .asset_metadata_service import AssetMetadataResult, AssetMetadataService
from .asset_type_detector import AssetTypeDetector, AssetTypeResult, map_ibkr_asset_class
from .broker_file_storage import BrokerFileStorage
from .broker_overlap_detector import BrokerOverlapDetector
from .currency_conversion_helper import CurrencyConversionHelper
from .currency_service import CurrencyService
from .date_range_service import merge_ranges, shrink_date_ranges
from .email_service import EmailService
from .http_client import HTTPClient, HTTPClientError
from .staged_import_service import StagedImportService
from .staging_utils import (
    cleanup_staging,
    copy_production_to_staging,
    create_staging_schema,
    create_staging_tables,
    merge_staging_to_production,
    reset_session_to_production,
    set_session_to_staging,
)
from .ticker_change_detection_service import TickerChangeDetectionService
from .transaction_hash_service import (
    check_and_transfer_ownership,
    compute_transaction_hash,
)

__all__ = [
    "AssetMetadataResult",
    "AssetMetadataService",
    "AssetTypeDetector",
    "AssetTypeResult",
    "BrokerFileStorage",
    "BrokerOverlapDetector",
    "CurrencyConversionHelper",
    "CurrencyService",
    "EmailService",
    "HTTPClient",
    "HTTPClientError",
    "StagedImportService",
    "TickerChangeDetectionService",
    "check_and_transfer_ownership",
    "cleanup_staging",
    "compute_transaction_hash",
    "copy_production_to_staging",
    "create_staging_schema",
    "create_staging_tables",
    "map_ibkr_asset_class",
    "merge_ranges",
    "merge_staging_to_production",
    "reset_session_to_production",
    "set_session_to_staging",
    "shrink_date_ranges",
]
