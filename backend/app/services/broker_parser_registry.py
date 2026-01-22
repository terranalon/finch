"""Parser registry for broker data parsers.

Maps broker types to their parser implementations and provides
factory methods for getting parser instances.
"""

import logging
from dataclasses import dataclass

from app.services.base_broker_parser import BaseBrokerParser

logger = logging.getLogger(__name__)


@dataclass
class BrokerInfo:
    """Information about a supported broker."""

    type: str
    name: str
    supported_formats: list[str]
    has_api: bool
    api_enabled: bool = False


class BrokerParserRegistry:
    """Registry for broker data parsers.

    Provides factory methods to get parser instances based on broker type.
    New parsers are registered by adding them to the _parsers dictionary.

    Example usage:
        parser = BrokerParserRegistry.get_parser('ibkr')
        data = parser.parse(file_content)
    """

    # Registered parsers - add new parser classes here
    # Import is done lazily to avoid circular imports
    _parsers: dict[str, type[BaseBrokerParser]] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Lazily initialize the parser registry."""
        if cls._initialized:
            return

        # Import parsers here to avoid circular imports
        from app.services.binance_parser import BinanceParser
        from app.services.bit2c_parser import Bit2CParser
        from app.services.ibkr_parser_adapter import IBKRParserAdapter
        from app.services.kraken_parser import KrakenParser
        from app.services.meitav_parser import MeitavParser

        cls._parsers = {
            "ibkr": IBKRParserAdapter,
            "meitav": MeitavParser,
            "kraken": KrakenParser,
            "bit2c": Bit2CParser,
            "binance": BinanceParser,
            # Future parsers:
            # 'ibi': IBIParser,
        }
        cls._initialized = True
        logger.info("Parser registry initialized with %d parsers", len(cls._parsers))

    @classmethod
    def get_parser(cls, broker_type: str) -> BaseBrokerParser:
        """Get a parser instance for the specified broker type.

        Args:
            broker_type: Broker type identifier (e.g., 'ibkr')

        Returns:
            Parser instance for the broker

        Raises:
            ValueError: If broker type is not supported
        """
        cls._ensure_initialized()

        if broker_type not in cls._parsers:
            supported = list(cls._parsers.keys())
            raise ValueError(f"Unsupported broker type '{broker_type}'. Supported: {supported}")

        parser_class = cls._parsers[broker_type]
        return parser_class()

    @classmethod
    def get_parser_for_file(cls, broker_type: str, filename: str) -> BaseBrokerParser:
        """Get a parser that supports the given file extension.

        Args:
            broker_type: Broker type identifier
            filename: Filename to check extension

        Returns:
            Parser instance if extension is supported

        Raises:
            ValueError: If broker type or file extension is not supported
        """
        parser = cls.get_parser(broker_type)
        extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if extension not in parser.supported_extensions():
            raise ValueError(
                f"File type '{extension}' not supported for broker '{broker_type}'. "
                f"Supported: {parser.supported_extensions()}"
            )

        return parser

    @classmethod
    def is_supported(cls, broker_type: str) -> bool:
        """Check if a broker type is supported.

        Args:
            broker_type: Broker type to check

        Returns:
            True if broker type has a registered parser
        """
        cls._ensure_initialized()
        return broker_type in cls._parsers

    @classmethod
    def get_supported_brokers(cls) -> list[BrokerInfo]:
        """Get information about all supported brokers.

        Returns:
            List of BrokerInfo objects
        """
        cls._ensure_initialized()

        brokers = []
        for broker_type, parser_class in cls._parsers.items():
            # Create instance to get metadata
            parser = parser_class()
            brokers.append(
                BrokerInfo(
                    type=parser.broker_type(),
                    name=parser.broker_name(),
                    supported_formats=parser.supported_extensions(),
                    has_api=parser.has_api(),
                    api_enabled=True,  # TODO: Check account configuration
                )
            )

        return brokers

    @classmethod
    def get_supported_broker_types(cls) -> list[str]:
        """Get list of supported broker type identifiers.

        Returns:
            List of broker type strings
        """
        cls._ensure_initialized()
        return list(cls._parsers.keys())

    @classmethod
    def register_parser(cls, broker_type: str, parser_class: type[BaseBrokerParser]) -> None:
        """Register a new parser class.

        This can be used to add parsers at runtime, useful for plugins.

        Args:
            broker_type: Broker type identifier
            parser_class: Parser class that extends BaseBrokerParser
        """
        cls._ensure_initialized()

        if not issubclass(parser_class, BaseBrokerParser):
            raise TypeError(f"Parser class must extend BaseBrokerParser, got {parser_class}")

        cls._parsers[broker_type] = parser_class
        logger.info("Registered parser for broker type: %s", broker_type)
