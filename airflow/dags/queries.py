"""SQL queries for daily portfolio pipeline DAG."""

# Exchange rate queries
CHECK_EXCHANGE_RATE_EXISTS = """
    SELECT rate FROM exchange_rates
    WHERE from_currency = :from_curr
    AND to_currency = :to_curr
    AND date = :date
"""

INSERT_EXCHANGE_RATE = """
    INSERT INTO exchange_rates
    (from_currency, to_currency, rate, date, created_at)
    VALUES (:from_curr, :to_curr, :rate, :date, NOW())
    ON CONFLICT (from_currency, to_currency, date)
    DO UPDATE SET rate = :rate
"""

# Asset price queries
GET_ACTIVE_HOLDINGS_ASSETS = """
    SELECT DISTINCT a.id, a.symbol, a.currency
    FROM assets a
    INNER JOIN holdings h ON h.asset_id = a.id
    WHERE h.is_active = true
      AND a.asset_class != 'Cash'
"""

GET_ALL_HOLDINGS_ASSETS = """
    SELECT DISTINCT a.id, a.symbol, a.currency
    FROM assets a
    INNER JOIN holdings h ON h.asset_id = a.id
    WHERE a.asset_class != 'Cash'
"""

GET_CRYPTO_ASSETS = """
    SELECT DISTINCT a.id, a.symbol, a.currency
    FROM assets a
    INNER JOIN holdings h ON h.asset_id = a.id
    WHERE a.asset_class = 'Crypto'
"""

GET_NON_CRYPTO_ASSETS = """
    SELECT DISTINCT a.id, a.symbol, a.currency
    FROM assets a
    INNER JOIN holdings h ON h.asset_id = a.id
    WHERE a.asset_class NOT IN ('Cash', 'Crypto')
"""

CHECK_ASSET_PRICE_EXISTS = """
    SELECT closing_price FROM asset_prices
    WHERE asset_id = :asset_id AND date = :date
"""

INSERT_ASSET_PRICE = """
    INSERT INTO asset_prices
    (asset_id, date, closing_price, currency, source, created_at)
    VALUES (:asset_id, :date, :closing_price, :currency, :source, NOW())
    ON CONFLICT (asset_id, date)
    DO NOTHING
"""

# Broker data import queries
GET_ACCOUNTS_WITH_BROKER_API = """
    SELECT a.id, a.metadata
    FROM accounts a
    WHERE a.is_active = true
    AND a.metadata IS NOT NULL
    AND (
        a.metadata->'ibkr'->>'flex_token' IS NOT NULL
        OR a.metadata->'binance'->>'api_key' IS NOT NULL
    )
"""

# TASE securities cache queries
UPSERT_TASE_SECURITY = """
    INSERT INTO tase_securities (
        security_id, symbol, yahoo_symbol, isin,
        security_name, security_name_en, security_type_code,
        company_name, company_sector, company_sub_sector, last_synced_at
    ) VALUES (
        :security_id, :symbol, :yahoo_symbol, :isin,
        :security_name, :security_name_en, :security_type_code,
        :company_name, :company_sector, :company_sub_sector, NOW()
    )
    ON CONFLICT (security_id) DO UPDATE SET
        symbol = EXCLUDED.symbol,
        yahoo_symbol = EXCLUDED.yahoo_symbol,
        isin = EXCLUDED.isin,
        security_name = EXCLUDED.security_name,
        security_name_en = EXCLUDED.security_name_en,
        security_type_code = EXCLUDED.security_type_code,
        company_name = EXCLUDED.company_name,
        company_sector = EXCLUDED.company_sector,
        company_sub_sector = EXCLUDED.company_sub_sector,
        last_synced_at = NOW()
"""

# Alias for batch upsert (used with executemany for single round-trip)
BATCH_UPSERT_TASE_SECURITIES = UPSERT_TASE_SECURITY

GET_TASE_CACHE_STATS = """
    SELECT
        COUNT(*) as total_securities,
        MAX(last_synced_at) as last_synced_at
    FROM tase_securities
"""

# Active accounts query for snapshot creation
GET_ACTIVE_ACCOUNTS = """
    SELECT id, name FROM accounts WHERE is_active = true
"""
