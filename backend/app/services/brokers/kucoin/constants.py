"""KuCoin-specific constants for symbol parsing and asset normalization."""

# Quote assets for symbol parsing (KuCoin uses dash-separated pairs: BTC-USDT)
QUOTE_ASSETS = ["USDT", "USDC", "UST", "USD", "BTC", "ETH", "KCS", "EUR", "GBP"]


def parse_symbol(symbol: str) -> tuple[str, str]:
    """Parse KuCoin symbol into base and quote assets.

    KuCoin uses dash-separated symbols: "BTC-USDT" -> ("BTC", "USDT").
    Falls back to splitting on known quote assets if no dash is present.

    Args:
        symbol: Trading pair symbol (e.g., "BTC-USDT")

    Returns:
        Tuple of (base_asset, quote_asset)
    """
    symbol = symbol.upper().strip()

    # KuCoin standard format: dash-separated
    if "-" in symbol:
        parts = symbol.split("-", 1)
        return parts[0], parts[1]

    # Fallback: try matching known quote assets (for edge cases)
    for quote in QUOTE_ASSETS:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)], quote

    return symbol, "UNKNOWN"
