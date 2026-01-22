"""Staging utilities for non-blocking imports.

This module provides PostgreSQL schema-based staging to keep the UI responsive
during long-running import operations. Instead of writing directly to production
tables (which holds locks), data is first imported to staging tables, then
merged to production in a quick atomic operation.

The import logic remains 100% unchanged - only the target tables differ.
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Tables that need staging (in dependency order for merge)
STAGING_TABLES = [
    "assets",
    "holdings",
    "transactions",
    "daily_cash_balance",
]


def create_staging_schema(db: Session) -> None:
    """Create the staging schema if it doesn't exist."""
    db.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
    db.commit()
    logger.info("Staging schema created or verified")


def create_staging_tables(db: Session) -> None:
    """Create staging tables that mirror production tables.

    Uses CREATE TABLE ... LIKE to copy structure including indexes and constraints.
    """
    create_staging_schema(db)

    # Create staging tables with same structure as production
    for table in STAGING_TABLES:
        # Drop if exists (clean slate for each import)
        db.execute(text(f"DROP TABLE IF EXISTS staging.{table} CASCADE"))

        # Create staging table with same structure (without foreign keys for flexibility)
        if table == "assets":
            db.execute(
                text("""
                CREATE TABLE staging.assets (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    asset_class VARCHAR(50) NOT NULL,
                    category VARCHAR(100),
                    currency VARCHAR(3) DEFAULT 'USD',
                    cusip VARCHAR(20),
                    isin VARCHAR(20),
                    conid VARCHAR(50),
                    figi VARCHAR(20),
                    is_manual_valuation BOOLEAN DEFAULT FALSE,
                    data_source VARCHAR(50),
                    last_fetched_price NUMERIC(15, 4),
                    last_fetched_at TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    -- Track original ID for merge mapping
                    original_id INTEGER
                )
            """)
            )
        elif table == "holdings":
            db.execute(
                text("""
                CREATE TABLE staging.holdings (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    asset_id INTEGER NOT NULL,
                    quantity NUMERIC(20, 8) NOT NULL,
                    cost_basis NUMERIC(15, 2) NOT NULL,
                    strategy_horizon VARCHAR(20),
                    tags JSONB,
                    is_active BOOLEAN DEFAULT TRUE,
                    closed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    -- Track original ID for merge mapping
                    original_id INTEGER,
                    -- Track staging asset_id for remapping
                    staging_asset_id INTEGER,
                    UNIQUE(account_id, asset_id)
                )
            """)
            )
        elif table == "transactions":
            db.execute(
                text("""
                CREATE TABLE staging.transactions (
                    id SERIAL PRIMARY KEY,
                    holding_id INTEGER NOT NULL,
                    broker_source_id INTEGER,
                    date DATE NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    quantity NUMERIC(20, 8),
                    price_per_unit NUMERIC(15, 4),
                    amount NUMERIC(15, 2),
                    fees NUMERIC(15, 2) DEFAULT 0,
                    currency_rate_to_usd_at_date NUMERIC(12, 6),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    to_holding_id INTEGER,
                    to_amount NUMERIC(15, 2),
                    exchange_rate NUMERIC(12, 6),
                    -- Track original ID for merge mapping
                    original_id INTEGER,
                    -- Track staging holding_id for remapping
                    staging_holding_id INTEGER,
                    staging_to_holding_id INTEGER
                )
            """)
            )
        elif table == "daily_cash_balance":
            db.execute(
                text("""
                CREATE TABLE staging.daily_cash_balance (
                    id SERIAL PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    balance NUMERIC(15, 2) NOT NULL,
                    activity TEXT,
                    broker_source_id INTEGER,
                    created_at TIMESTAMP DEFAULT NOW(),
                    -- Track original ID for merge mapping
                    original_id INTEGER,
                    UNIQUE(account_id, date, currency)
                )
            """)
            )

    db.commit()
    logger.info("Staging tables created")


def copy_production_to_staging(db: Session, account_id: int) -> dict:
    """Copy relevant production data to staging tables.

    This enables duplicate detection during import - the staging session
    can query existing records that were copied from production.

    Args:
        db: Database session
        account_id: Account being imported (to limit data copied)

    Returns:
        Statistics about copied data
    """
    stats = {"assets": 0, "holdings": 0, "transactions": 0}

    # Copy all assets (needed for symbol lookups)
    result = db.execute(
        text("""
        INSERT INTO staging.assets (
            original_id, symbol, name, asset_class, category, currency,
            cusip, isin, conid, figi, is_manual_valuation, data_source,
            last_fetched_price, last_fetched_at, metadata, created_at, updated_at
        )
        SELECT
            id, symbol, name, asset_class, category, currency,
            cusip, isin, conid, figi, is_manual_valuation, data_source,
            last_fetched_price, last_fetched_at, metadata, created_at, updated_at
        FROM public.assets
    """)
    )
    stats["assets"] = result.rowcount

    # Copy holdings for this account
    result = db.execute(
        text("""
        INSERT INTO staging.holdings (
            original_id, account_id, asset_id, staging_asset_id, quantity, cost_basis,
            strategy_horizon, tags, is_active, closed_at, created_at, updated_at
        )
        SELECT
            h.id, h.account_id, h.asset_id,
            sa.id,  -- staging_asset_id maps to staging.assets.id
            h.quantity, h.cost_basis, h.strategy_horizon, h.tags,
            h.is_active, h.closed_at, h.created_at, h.updated_at
        FROM public.holdings h
        JOIN staging.assets sa ON sa.original_id = h.asset_id
        WHERE h.account_id = :account_id
    """),
        {"account_id": account_id},
    )
    stats["holdings"] = result.rowcount

    # Copy transactions for this account's holdings
    result = db.execute(
        text("""
        INSERT INTO staging.transactions (
            original_id, holding_id, staging_holding_id, broker_source_id, date, type,
            quantity, price_per_unit, amount, fees, currency_rate_to_usd_at_date,
            notes, created_at, to_holding_id, staging_to_holding_id, to_amount, exchange_rate
        )
        SELECT
            t.id, t.holding_id,
            sh.id,  -- staging_holding_id maps to staging.holdings.id
            t.broker_source_id, t.date, t.type,
            t.quantity, t.price_per_unit, t.amount, t.fees, t.currency_rate_to_usd_at_date,
            t.notes, t.created_at, t.to_holding_id,
            sh_to.id,  -- staging_to_holding_id
            t.to_amount, t.exchange_rate
        FROM public.transactions t
        JOIN public.holdings h ON t.holding_id = h.id
        JOIN staging.holdings sh ON sh.original_id = t.holding_id
        LEFT JOIN staging.holdings sh_to ON sh_to.original_id = t.to_holding_id
        WHERE h.account_id = :account_id
    """),
        {"account_id": account_id},
    )
    stats["transactions"] = result.rowcount

    db.commit()
    logger.info(
        "Copied production data to staging: %d assets, %d holdings, %d transactions",
        stats["assets"],
        stats["holdings"],
        stats["transactions"],
    )
    return stats


def merge_staging_to_production(db: Session, account_id: int) -> dict:
    """Merge staging data back to production tables.

    This is the fast operation that briefly locks production tables.
    Uses INSERT ... ON CONFLICT for efficient upserts.

    Args:
        db: Database session
        account_id: Account being imported

    Returns:
        Statistics about merged data
    """
    stats = {
        "assets_inserted": 0,
        "assets_updated": 0,
        "holdings_inserted": 0,
        "holdings_updated": 0,
        "transactions_inserted": 0,
    }

    # Step 1: Merge assets (new assets that were created during import)
    # These are assets with original_id IS NULL (newly created in staging)
    result = db.execute(
        text("""
        INSERT INTO public.assets (
            symbol, name, asset_class, category, currency,
            cusip, isin, conid, figi, is_manual_valuation, data_source,
            last_fetched_price, last_fetched_at, metadata, created_at, updated_at
        )
        SELECT
            symbol, name, asset_class, category, currency,
            cusip, isin, conid, figi, is_manual_valuation, data_source,
            last_fetched_price, last_fetched_at, metadata, created_at, updated_at
        FROM staging.assets
        WHERE original_id IS NULL
        ON CONFLICT (symbol) DO UPDATE SET
            name = EXCLUDED.name,
            cusip = COALESCE(public.assets.cusip, EXCLUDED.cusip),
            isin = COALESCE(public.assets.isin, EXCLUDED.isin),
            conid = COALESCE(public.assets.conid, EXCLUDED.conid),
            figi = COALESCE(public.assets.figi, EXCLUDED.figi),
            last_fetched_price = EXCLUDED.last_fetched_price,
            last_fetched_at = EXCLUDED.last_fetched_at,
            updated_at = NOW()
        RETURNING (xmax = 0) AS inserted
    """)
    )
    for row in result:
        if row.inserted:
            stats["assets_inserted"] += 1
        else:
            stats["assets_updated"] += 1

    # Update existing assets that were modified in staging
    result = db.execute(
        text("""
        UPDATE public.assets pa
        SET
            last_fetched_price = sa.last_fetched_price,
            last_fetched_at = sa.last_fetched_at,
            cusip = COALESCE(pa.cusip, sa.cusip),
            isin = COALESCE(pa.isin, sa.isin),
            conid = COALESCE(pa.conid, sa.conid),
            figi = COALESCE(pa.figi, sa.figi),
            currency = sa.currency,
            updated_at = NOW()
        FROM staging.assets sa
        WHERE sa.original_id = pa.id
        AND sa.original_id IS NOT NULL
        AND (
            sa.last_fetched_price IS DISTINCT FROM pa.last_fetched_price
            OR sa.currency IS DISTINCT FROM pa.currency
            OR (sa.cusip IS NOT NULL AND pa.cusip IS NULL)
            OR (sa.isin IS NOT NULL AND pa.isin IS NULL)
        )
    """)
    )
    stats["assets_updated"] += result.rowcount

    # Step 2: Merge holdings
    # First, create mapping from staging asset symbols to production asset IDs
    # (needed for holdings that reference newly created assets)
    result = db.execute(
        text("""
        INSERT INTO public.holdings (
            account_id, asset_id, quantity, cost_basis,
            strategy_horizon, tags, is_active, closed_at, created_at, updated_at
        )
        SELECT
            sh.account_id,
            COALESCE(sh.asset_id, pa.id),  -- Use original asset_id or find by symbol
            sh.quantity,
            sh.cost_basis,
            sh.strategy_horizon,
            sh.tags,
            sh.is_active,
            sh.closed_at,
            sh.created_at,
            sh.updated_at
        FROM staging.holdings sh
        LEFT JOIN staging.assets sa ON sa.id = sh.staging_asset_id
        LEFT JOIN public.assets pa ON pa.symbol = sa.symbol
        WHERE sh.original_id IS NULL
        AND sh.account_id = :account_id
        ON CONFLICT (account_id, asset_id) DO UPDATE SET
            quantity = EXCLUDED.quantity,
            cost_basis = EXCLUDED.cost_basis,
            is_active = EXCLUDED.is_active,
            updated_at = NOW()
        RETURNING (xmax = 0) AS inserted
    """),
        {"account_id": account_id},
    )
    for row in result:
        if row.inserted:
            stats["holdings_inserted"] += 1
        else:
            stats["holdings_updated"] += 1

    # Update existing holdings that were modified
    result = db.execute(
        text("""
        UPDATE public.holdings ph
        SET
            quantity = sh.quantity,
            cost_basis = sh.cost_basis,
            is_active = sh.is_active,
            updated_at = NOW()
        FROM staging.holdings sh
        WHERE sh.original_id = ph.id
        AND sh.original_id IS NOT NULL
        AND sh.account_id = :account_id
        AND (
            sh.quantity IS DISTINCT FROM ph.quantity
            OR sh.cost_basis IS DISTINCT FROM ph.cost_basis
            OR sh.is_active IS DISTINCT FROM ph.is_active
        )
    """),
        {"account_id": account_id},
    )
    stats["holdings_updated"] += result.rowcount

    # Step 3: Merge transactions (only new ones - transactions are immutable)
    result = db.execute(
        text("""
        INSERT INTO public.transactions (
            holding_id, broker_source_id, date, type,
            quantity, price_per_unit, amount, fees,
            currency_rate_to_usd_at_date, notes, created_at,
            to_holding_id, to_amount, exchange_rate
        )
        SELECT
            COALESCE(st.holding_id, ph.id),  -- Map to production holding
            st.broker_source_id,
            st.date,
            st.type,
            st.quantity,
            st.price_per_unit,
            st.amount,
            st.fees,
            st.currency_rate_to_usd_at_date,
            st.notes,
            st.created_at,
            COALESCE(st.to_holding_id, ph_to.id),  -- Map to_holding to production
            st.to_amount,
            st.exchange_rate
        FROM staging.transactions st
        -- Join to get production holding_id via staging holding
        LEFT JOIN staging.holdings sh ON sh.id = st.staging_holding_id
        LEFT JOIN public.holdings ph ON ph.account_id = sh.account_id
            AND ph.asset_id = (
                SELECT pa.id FROM public.assets pa
                JOIN staging.assets sa ON sa.symbol = pa.symbol
                WHERE sa.id = sh.staging_asset_id
            )
        -- Same for to_holding (forex)
        LEFT JOIN staging.holdings sh_to ON sh_to.id = st.staging_to_holding_id
        LEFT JOIN public.holdings ph_to ON ph_to.account_id = sh_to.account_id
            AND ph_to.asset_id = (
                SELECT pa.id FROM public.assets pa
                JOIN staging.assets sa ON sa.symbol = pa.symbol
                WHERE sa.id = sh_to.staging_asset_id
            )
        WHERE st.original_id IS NULL
    """)
    )
    stats["transactions_inserted"] = result.rowcount

    db.commit()
    logger.info(
        "Merged staging to production: %d/%d assets, %d/%d holdings, %d transactions",
        stats["assets_inserted"],
        stats["assets_updated"],
        stats["holdings_inserted"],
        stats["holdings_updated"],
        stats["transactions_inserted"],
    )
    return stats


def cleanup_staging(db: Session) -> None:
    """Drop staging tables after successful merge."""
    for table in reversed(STAGING_TABLES):
        db.execute(text(f"DROP TABLE IF EXISTS staging.{table} CASCADE"))
    db.commit()
    logger.info("Staging tables cleaned up")


def set_session_to_staging(db: Session) -> None:
    """Configure session to use staging schema for writes.

    Sets search_path so that unqualified table names resolve to staging first.
    """
    db.execute(text("SET search_path TO staging, public"))
    logger.debug("Session search_path set to staging")


def reset_session_to_production(db: Session) -> None:
    """Reset session to use production schema."""
    db.execute(text("SET search_path TO public"))
    logger.debug("Session search_path reset to public")
