"""Asset type detection service for distinguishing ETF/MutualFund/MoneyMarket from Stock."""

import logging
from dataclasses import dataclass

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class AssetTypeResult:
    """Result of asset type detection."""

    symbol: str
    detected_type: str | None  # "ETF", "MutualFund", "MoneyMarket", "Stock", or None
    source: str  # "yfinance", "not_found", "error"
    error: str | None = None


class AssetTypeDetector:
    """Service for detecting asset types using Yahoo Finance quoteType."""

    # Map Yahoo Finance quoteType to our asset classes
    QUOTE_TYPE_MAP = {
        "ETF": "ETF",
        "MUTUALFUND": "MutualFund",
        "MONEYMARKET": "MoneyMarket",
        "EQUITY": "Stock",
    }

    @staticmethod
    def detect_asset_type(symbol: str) -> AssetTypeResult:
        """
        Detect asset type (ETF, MutualFund, MoneyMarket, Stock) using Yahoo Finance.

        Args:
            symbol: The ticker symbol (e.g., 'SPY', 'VFIAX')

        Returns:
            AssetTypeResult with detected type or error information
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                logger.warning(f"No data found for symbol {symbol}")
                return AssetTypeResult(
                    symbol=symbol,
                    detected_type=None,
                    source="not_found",
                    error="Symbol not found in Yahoo Finance",
                )

            quote_type = info.get("quoteType")
            detected_type = AssetTypeDetector.QUOTE_TYPE_MAP.get(quote_type)

            if detected_type:
                logger.info(f"Detected {symbol} as {detected_type} (quoteType={quote_type})")
                return AssetTypeResult(
                    symbol=symbol,
                    detected_type=detected_type,
                    source="yfinance",
                )

            # Unknown quote type
            logger.warning(f"Unknown quoteType for {symbol}: {quote_type}")
            return AssetTypeResult(
                symbol=symbol,
                detected_type=None,
                source="yfinance",
                error=f"Unknown quoteType: {quote_type}",
            )

        except Exception as e:
            logger.error(f"Error detecting asset type for {symbol}: {e}")
            return AssetTypeResult(
                symbol=symbol,
                detected_type=None,
                source="error",
                error=str(e),
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
    """
    Map IBKR asset categories to our asset classes.

    For FUND category, uses Yahoo Finance to detect actual type (ETF, MutualFund, MoneyMarket).

    Args:
        ibkr_category: IBKR assetCategory field (STK, BOND, FUND, etc.)
        symbol: Yahoo Finance symbol (required for FUND detection)

    Returns:
        Asset class: Stock, Bond, ETF, MutualFund, MoneyMarket, Cash, Commodity, or Other
    """
    if ibkr_category == "FUND" and symbol:
        result = AssetTypeDetector.detect_asset_type(symbol)
        if result.detected_type:
            return result.detected_type
        logger.warning(f"Could not detect fund type for {symbol}, defaulting to Stock")
        return "Stock"

    return IBKR_CATEGORY_MAP.get(ibkr_category, "Other")
