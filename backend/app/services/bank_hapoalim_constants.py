"""Bank Hapoalim broker constants for column mappings and normalization."""

# Column indices for headers (same positions for both Hebrew and English)
COLUMN_INDICES = {
    "short_security_name": 0,
    "action_type": 2,
    "value_date": 3,
    "security_group": 4,
    "quantity": 5,
    "price": 6,
    "gross_value": 7,
    "trade_currency": 8,
    "net_value_ils": 9,
    "net_value_currency": 10,
    "israel_tax": 13,
    "foreign_tax": 14,
    "commission_ils": 15,
    "security_number": 16,
    "isin": 18,
}

# English header names for detection
ENGLISH_HEADER_NAMES = {
    "Short security name",
    "Action type",
    "Value Date",
    "Security Number",
}

# Hebrew header names for detection
HEBREW_HEADER_NAMES = {
    "שם נייר",
    "סוג פעולה",
    "תאריך נכונות",
    "מספר נייר",
}

# Transaction type mapping (Hebrew to normalized)
ACTION_TYPE_MAP = {
    "קניה": "Buy",
    "מכירה": "Sell",
    "דבידנד תשלום": "Dividend",
    "העברה לזכות הפקדון": "Deposit",
}

# Security group mapping
SECURITY_GROUP_MAP = {
    "מניות": "Stock",
    "קרן נאמנות": "MutualFund",
}

# Currency mapping (Hebrew to ISO code)
CURRENCY_MAP = {
    "שקל חדש": "ILS",
    "דולר ארהב": "USD",
    "אירו": "EUR",
}
