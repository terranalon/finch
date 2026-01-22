"""Shared constants for Bit2C parser and client.

Bit2C uses NIS (New Israeli Shekel) which we normalize to ILS.
"""

# Bit2C asset name to standard symbol mapping
# Only includes non-identity mappings; unmapped assets pass through unchanged
ASSET_NAME_MAP: dict[str, str] = {
    "NIS": "ILS",
}

# Trading pairs to (symbol, currency) mapping
TRADING_PAIRS: dict[str, tuple[str, str]] = {
    "BtcNis": ("BTC", "ILS"),
    "EthNis": ("ETH", "ILS"),
    "LtcNis": ("LTC", "ILS"),
    "UsdcNis": ("USDC", "ILS"),
}

# Fiat currencies for determining trade direction
FIAT_CURRENCIES = frozenset({"ILS", "USD", "EUR"})


def normalize_bit2c_asset(asset: str | None) -> str | None:
    """Normalize Bit2C asset names to standard symbols.

    Args:
        asset: Bit2C asset name (e.g., "NIS", "BTC")

    Returns:
        Normalized symbol (e.g., "ILS", "BTC") or None if input is None
    """
    if not asset:
        return None
    asset = str(asset).strip()
    if asset in ("N/A", ""):
        return None
    return ASSET_NAME_MAP.get(asset, asset)
