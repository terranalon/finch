"""Application constants to avoid magic strings."""


class AssetClass:
    """Asset class constants."""

    CASH = "Cash"
    CRYPTO = "Crypto"
    STOCK = "Stock"
    ETF = "ETF"
    BOND = "Bond"
    MUTUAL_FUND = "MutualFund"
    OPTION = "Option"
    UNKNOWN = "Unknown"


class Currency:
    """Common currency constants."""

    USD = "USD"
    EUR = "EUR"
    ILS = "ILS"
    GBP = "GBP"
