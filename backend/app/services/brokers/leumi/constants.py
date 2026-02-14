"""Constants for Bank Leumi parser."""

# Transaction type mapping (Hebrew to normalized)
ACTION_TYPE_MAP: dict[str, str] = {
    "קניה": "Buy",
    "מכירה": "Sell",
    "דיבידנד": "Dividend",
    "הטבה": "Bonus",
    "זיכוי שברים": "Sell",
    "חישוב רווח/הפסד ו/או ניכוי המס": "Tax",
}

# Action types to ignore (informational or cancelled transactions)
SKIP_ACTION_TYPES: set[str] = {
    "מידע-הטבה",
    "קניה וביטול",
    "מכירה וביטול",
}

# Currency mapping (Hebrew to ISO code)
CURRENCY_MAP: dict[str, str] = {
    'ש"ח': "ILS",
    'דולר ארה"ב': "USD",
}

# SpreadsheetML XML namespace used by Leumi .xls exports
SPREADSHEET_NS = "urn:schemas-microsoft-com:office:spreadsheet"
