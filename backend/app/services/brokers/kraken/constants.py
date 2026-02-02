"""Shared constants for Kraken parser and client.

Kraken uses non-standard asset naming with X prefix for crypto
(XXBT, XETH) and Z prefix for fiat (ZUSD, ZEUR).
"""

import re

# Kraken asset name to standard symbol mapping
ASSET_NAME_MAP: dict[str, str] = {
    # Crypto with X prefix
    "XXBT": "BTC",
    "XBT": "BTC",
    "XETH": "ETH",
    "XXRP": "XRP",
    "XXLM": "XLM",
    "XLTC": "LTC",
    "XXMR": "XMR",
    "XZEC": "ZEC",
    "XREP": "REP",
    "XXDG": "DOGE",
    # Fiat with Z prefix
    "ZUSD": "USD",
    "ZEUR": "EUR",
    "ZGBP": "GBP",
    "ZCAD": "CAD",
    "ZJPY": "JPY",
    "ZAUD": "AUD",
    # Special cases (version identifiers, not unstaking days)
    "ETH2": "ETH",  # Ethereum 2.0 staking
}

# Standard fiat currencies for determining trade direction
FIAT_CURRENCIES = frozenset({"USD", "EUR", "GBP", "CAD", "JPY", "AUD", "ILS"})

# Pattern to detect staked asset variants with unstaking-day suffixes (e.g., SOL03, DOT28)
# Kraken uses 2-digit numbers to represent unstaking days (more days = higher APY)
# Only matches 2+ digits to avoid false positives like ETH2 (Ethereum 2.0 version identifier)
_UNSTAKING_DAYS_PATTERN = re.compile(r"^([A-Z]{2,})(\d{2,})$")


def normalize_kraken_asset(asset: str) -> str:
    """Normalize Kraken asset names to standard symbols.

    Handles multiple Kraken naming conventions:
    1. X prefix for crypto (XXBT -> BTC, XETH -> ETH)
    2. Z prefix for fiat (ZUSD -> USD, ZEUR -> EUR)
    3. Dot suffixes for staking variants (.S, .F, .B, .M, .P)
    4. Numeric suffixes for staked assets (SOL03 -> SOL, ETH2 -> ETH)

    Args:
        asset: Kraken asset name (e.g., "XXBT", "ZUSD", "ETH.S", "SOL03")

    Returns:
        Normalized symbol (e.g., "BTC", "USD", "ETH", "SOL")
    """
    if not asset:
        return asset

    # Remove common suffixes (.S for staked, .F for flex, .B for bonded, etc.)
    base_asset = asset.split(".")[0]

    # Check direct mapping first
    if base_asset in ASSET_NAME_MAP:
        return ASSET_NAME_MAP[base_asset]

    # Try removing X or Z prefix for 4-char assets
    if len(base_asset) == 4 and base_asset[0] in ("X", "Z"):
        return base_asset[1:]

    # Try detecting staked assets with unstaking-day suffixes (e.g., SOL03 -> SOL, DOT28 -> DOT)
    # Kraken uses 2-digit numbers for unstaking days (more days = higher APY)
    # Only matches 2+ digits to avoid false positives like ETH2 (handled in ASSET_NAME_MAP)
    match = _UNSTAKING_DAYS_PATTERN.match(base_asset)
    if match:
        base_symbol = match.group(1)
        return base_symbol

    return base_asset
