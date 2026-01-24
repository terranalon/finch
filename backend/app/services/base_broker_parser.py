"""Base class for broker data parsers.

This module defines the abstract interface that all broker-specific parsers must implement.
The parser registry uses this interface to work with different broker types uniformly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class ParsedTransaction:
    """Normalized transaction data from any broker."""

    trade_date: date
    symbol: str
    transaction_type: str  # 'Buy', 'Sell', 'Dividend', etc.
    quantity: Decimal | None = None
    price_per_unit: Decimal | None = None
    amount: Decimal | None = None
    fees: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USD"
    notes: str | None = None
    external_transaction_id: str | None = None  # Broker's unique transaction ID
    raw_data: dict | None = None  # Original broker data for debugging


@dataclass
class ParsedPosition:
    """Normalized position data from any broker."""

    symbol: str
    quantity: Decimal
    cost_basis: Decimal | None = None
    currency: str = "USD"
    asset_class: str | None = None  # 'Stock', 'ETF', 'Cash', etc.
    raw_data: dict | None = None


@dataclass
class ParsedCashTransaction:
    """Normalized cash transaction (deposit, withdrawal, forex)."""

    date: date
    transaction_type: str  # 'Deposit', 'Withdrawal', 'Forex Conversion', etc.
    amount: Decimal
    currency: str
    fees: Decimal = field(default_factory=lambda: Decimal("0"))
    notes: str | None = None
    raw_data: dict | None = None


@dataclass
class BrokerImportData:
    """Complete parsed data from a broker file or API response."""

    start_date: date
    end_date: date
    transactions: list[ParsedTransaction] = field(default_factory=list)
    positions: list[ParsedPosition] = field(default_factory=list)
    cash_transactions: list[ParsedCashTransaction] = field(default_factory=list)
    dividends: list[ParsedTransaction] = field(default_factory=list)
    raw_metadata: dict | None = None  # Original file metadata

    @property
    def total_records(self) -> int:
        """Total number of records parsed."""
        return (
            len(self.transactions)
            + len(self.positions)
            + len(self.cash_transactions)
            + len(self.dividends)
        )


class BaseBrokerParser(ABC):
    """Abstract base class for all broker parsers.

    Each broker (IBKR, Binance, IBI, etc.) should implement this interface
    to provide consistent parsing capabilities.

    Example usage:
        parser = IBKRParser()
        date_range = parser.extract_date_range(xml_bytes)
        data = parser.parse(xml_bytes)
    """

    @classmethod
    @abstractmethod
    def broker_type(cls) -> str:
        """Return the broker type identifier (e.g., 'ibkr', 'binance')."""
        pass

    @classmethod
    @abstractmethod
    def broker_name(cls) -> str:
        """Return the human-readable broker name (e.g., 'Interactive Brokers')."""
        pass

    @classmethod
    @abstractmethod
    def supported_extensions(cls) -> list[str]:
        """Return list of supported file extensions (e.g., ['.xml', '.csv'])."""
        pass

    @classmethod
    @abstractmethod
    def has_api(cls) -> bool:
        """Return True if this broker has API support for automated fetching."""
        pass

    @abstractmethod
    def extract_date_range(self, file_content: bytes) -> tuple[date, date]:
        """Extract the date range covered by this file without full parsing.

        This is a lightweight operation used for overlap detection before
        committing to a full parse.

        Args:
            file_content: Raw file content as bytes

        Returns:
            Tuple of (start_date, end_date)

        Raises:
            ValueError: If date range cannot be determined
        """
        pass

    @abstractmethod
    def parse(self, file_content: bytes) -> BrokerImportData:
        """Parse file content into normalized import data.

        Args:
            file_content: Raw file content as bytes

        Returns:
            BrokerImportData containing all parsed records

        Raises:
            ValueError: If parsing fails
        """
        pass

    def validate_file(self, file_content: bytes, filename: str) -> tuple[bool, str | None]:
        """Validate that file content is parseable.

        Default implementation checks file extension and attempts date extraction.

        Args:
            file_content: Raw file content
            filename: Original filename for extension checking

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check extension
        extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in self.supported_extensions():
            return (
                False,
                f"Unsupported file type '{extension}'. Expected: {self.supported_extensions()}",
            )

        # Try to extract date range as validation
        try:
            self.extract_date_range(file_content)
            return True, None
        except Exception as e:
            return False, f"Failed to parse file: {e}"
