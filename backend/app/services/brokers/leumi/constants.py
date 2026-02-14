"""Constants for Bank Leumi parser."""

ACTION_TYPE_MAP: dict[str, str] = {
    "קניה": "Buy",
    "מכירה": "Sell",
    "דיבידנד": "Dividend",
    "הטבה": "Bonus",
    "זיכוי שברים": "Sell",
    "חישוב רווח/הפסד ו/או ניכוי המס": "Tax",
}

SKIP_ACTION_TYPES: set[str] = {
    "מידע-הטבה",
    "קניה וביטול",
    "מכירה וביטול",
}

CURRENCY_MAP: dict[str, str] = {
    'ש"ח': "ILS",
    'דולר ארה"ב': "USD",
}

SS_NS = "urn:schemas-microsoft-com:office:spreadsheet"
