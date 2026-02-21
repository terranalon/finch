"""Constants for Mizrahi Tefahot broker parser.

Mizrahi Tefahot exports .xls files that are actually UTF-16 LE encoded HTML.
This module maps Hebrew column names and action types to normalized values.
"""

# Map Hebrew action types to normalized transaction types.
# Note: "קניה  רצף" (double space) is a known variant in Mizrahi files.
ACTION_TYPE_MAP: dict[str, str] = {
    "קניה": "Buy",
    "מכירה": "Sell",
    "קניה רצף": "Buy",
    "מכירה רצף": "Sell",
    "קניה  רצף": "Buy",
    "מכירה  רצף": "Sell",
    "הטבה": "Buy",
    "פדיון": "Sell",
    "החלפה/גריעה": "Sell",
}

# Currency code mapping (from קוד מטבע column)
CURRENCY_CODE_MAP: dict[str, str] = {
    "000": "ILS",
    "001": "USD",
}

# Israeli tax codes use security numbers starting with 999
TAX_CODE_PREFIX = "999"
