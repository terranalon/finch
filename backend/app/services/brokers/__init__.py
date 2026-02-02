"""Broker integrations - parsers and import services.

This module provides the infrastructure for importing data from various brokers:
- BaseBrokerParser: Abstract base for all broker parsers
- BaseBrokerImportService: Abstract base for all import services
- BrokerParserRegistry: Registry for parser lookup by broker type
- ImportServiceRegistry: Registry for import service lookup by broker type

Each broker (IBKR, Kraken, etc.) has its own subpackage with parser and client.
"""

from .base_broker_parser import BaseBrokerParser, BrokerImportData
from .base_import_service import (
    BaseBrokerImportService,
    extract_date_range,
    extract_date_range_serializable,
    extract_unique_symbols,
)
from .broker_parser_registry import BrokerParserRegistry
from .import_service_registry import BrokerImportServiceRegistry

__all__ = [
    "BaseBrokerImportService",
    "BaseBrokerParser",
    "BrokerImportData",
    "BrokerImportServiceRegistry",
    "BrokerParserRegistry",
    "extract_date_range",
    "extract_date_range_serializable",
    "extract_unique_symbols",
]
