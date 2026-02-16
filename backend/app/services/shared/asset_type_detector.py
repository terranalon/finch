"""Asset type detection service for distinguishing ETF/MutualFund/MoneyMarket from Stock."""

import logging
from dataclasses import dataclass

from app.services.market_data.yfinance_client import QUOTE_TYPE_MAP, TickerInfo, YFinanceClient

logger = logging.getLogger(__name__)


@dataclass
class AssetTypeResult:
    """Result of asset type detection."""

    symbol: str
    detected_type: str | None
    source: str
    error: str | None = None


class AssetTypeDetector:
    """Service for detecting asset types using Yahoo Finance quoteType."""

    QUOTE_TYPE_MAP = QUOTE_TYPE_MAP

    @staticmethod
    def detect_asset_type(symbol: str) -> AssetTypeResult:
        """Detect asset type (ETF, MutualFund, MoneyMarket, Stock) using Yahoo Finance."""
        try:
            client = YFinanceClient()
            info = client.get_ticker_info(symbol)
            return AssetTypeDetector.detect_from_ticker_info(symbol, info)
        except Exception as e:
            logger.error("Error detecting asset type for %s: %s", symbol, e)
            return AssetTypeResult(symbol=symbol, detected_type=None, source="error", error=str(e))

    @staticmethod
    def detect_from_ticker_info(symbol: str, info: TickerInfo | None) -> AssetTypeResult:
        """Detect asset type from pre-fetched TickerInfo (avoids redundant API call)."""
        if info is None:
            return AssetTypeResult(
                symbol=symbol,
                detected_type=None,
                source="not_found",
                error="Symbol not found in Yahoo Finance",
            )

        detected_type = info.asset_class
        if detected_type:
            logger.info("Detected %s as %s (quoteType=%s)", symbol, detected_type, info.quote_type)
            return AssetTypeResult(symbol=symbol, detected_type=detected_type, source="yfinance")

        logger.warning("Unknown quoteType for %s: %s", symbol, info.quote_type)
        return AssetTypeResult(
            symbol=symbol,
            detected_type=None,
            source="yfinance",
            error=f"Unknown quoteType: {info.quote_type}",
        )


# IBKR category to asset class mapping
IBKR_CATEGORY_MAP = {
    "STK": "Stock",
    "BOND": "Bond",
    "CASH": "Cash",
    "FUT": "Commodity",
    "FOP": "Commodity",
    "OPT": "Other",
    "WAR": "Other",
    "CFD": "Other",
}


def map_ibkr_asset_class(ibkr_category: str, symbol: str | None = None) -> str:
    """Map IBKR asset categories to our asset classes."""
    if ibkr_category == "FUND" and symbol:
        result = AssetTypeDetector.detect_asset_type(symbol)
        if result.detected_type:
            return result.detected_type
        logger.warning("Could not detect fund type for %s, defaulting to Stock", symbol)
        return "Stock"

    return IBKR_CATEGORY_MAP.get(ibkr_category, "Other")
