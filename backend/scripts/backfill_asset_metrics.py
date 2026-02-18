"""One-time backfill script to populate asset daily metrics and slow-changing fields.

Usage:
    docker compose exec backend python scripts/backfill_asset_metrics.py
    # or locally:
    DATABASE_HOST=localhost uv run python scripts/backfill_asset_metrics.py
"""

import logging
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Asset  # noqa: E402
from app.services.asset_metrics_service import AssetMetricsService  # noqa: E402
from app.services.market_data.coingecko_client import CoinGeckoClient  # noqa: E402
from app.services.market_data.yfinance_client import YFinanceClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_AGOROT_DIVISOR = Decimal("100")


def backfill_stocks(db: Session, assets: list[Asset]) -> dict[str, int]:
    """Backfill stock/ETF assets using ticker.info."""
    stats: dict[str, int] = {"updated": 0, "failed": 0}
    if not assets:
        return stats

    symbols = [a.symbol for a in assets]
    logger.info("Backfilling %d stock/ETF assets", len(symbols))

    client = YFinanceClient()
    batch_results = client.get_batch_ticker_info(symbols, rate=5.0)
    today = date.today()

    for asset in assets:
        data = batch_results.get(asset.symbol)
        if data is None:
            stats["failed"] += 1
            logger.warning("No data for %s", asset.symbol)
            continue

        try:
            divisor = _AGOROT_DIVISOR if asset.symbol.endswith(".TA") else None
            price = data.close / divisor if divisor and data.close else data.close
            open_ = data.open / divisor if divisor and data.open else data.open
            high_ = data.high / divisor if divisor and data.high else data.high
            low_ = data.low / divisor if divisor and data.low else data.low

            AssetMetricsService.upsert_daily_metrics(
                db,
                asset_id=asset.id,
                target_date=today,
                open=open_,
                high=high_,
                low=low_,
                close=price,
                volume=data.volume,
                market_cap=data.market_cap,
                pe_ratio=data.pe_ratio,
                forward_pe=data.forward_pe,
                eps=data.eps,
                dividend_rate=data.dividend_rate,
                dividend_yield=data.dividend_yield,
                payout_ratio=data.payout_ratio,
                source="Yahoo Finance",
            )
            AssetMetricsService.update_slow_changing_fields(
                db,
                asset,
                description=data.description,
                exchange=data.exchange,
                website=data.website,
                ceo=data.ceo,
                employees=data.employees,
                beta=data.beta,
                avg_volume=data.avg_volume,
                earnings_date=data.earnings_date,
                ex_dividend_date=data.ex_dividend_date,
                target_est=data.target_est,
                week_52_high=data.week_52_high,
                week_52_low=data.week_52_low,
                peg_ratio=data.peg_ratio,
                expense_ratio=data.expense_ratio,
                fund_family=data.fund_family,
                nav=data.nav,
            )
            stats["updated"] += 1
        except Exception:
            stats["failed"] += 1
            logger.exception("Failed to backfill %s", asset.symbol)

    return stats


def backfill_crypto(db: Session, assets: list[Asset]) -> dict[str, int]:
    """Backfill crypto assets using CoinGecko /coins/markets."""
    stats: dict[str, int] = {"updated": 0, "failed": 0}
    if not assets:
        return stats

    symbols = [a.symbol for a in assets]
    logger.info("Backfilling %d crypto assets", len(symbols))

    client = CoinGeckoClient()
    market_data = client.get_market_data(symbols, "usd")
    today = date.today()

    for asset in assets:
        data = market_data.get(asset.symbol)
        if data is None:
            stats["failed"] += 1
            logger.warning("No market data for %s", asset.symbol)
            continue

        try:
            AssetMetricsService.upsert_daily_metrics(
                db,
                asset_id=asset.id,
                target_date=today,
                high=data.high_24h,
                low=data.low_24h,
                close=data.price,
                volume=int(data.volume) if data.volume is not None else None,
                market_cap=data.market_cap,
                circulating_supply=data.circulating_supply,
                market_cap_rank=data.market_cap_rank,
                source="CoinGecko",
            )
            AssetMetricsService.update_slow_changing_fields(
                db,
                asset,
                max_supply=data.max_supply,
                ath=data.ath,
                ath_date=data.ath_date,
                atl=data.atl,
                atl_date=data.atl_date,
            )
            stats["updated"] += 1
        except Exception:
            stats["failed"] += 1
            logger.exception("Failed to backfill %s", asset.symbol)

    return stats


def main() -> None:
    db = SessionLocal()
    try:
        all_assets = (
            db.query(Asset).filter(Asset.symbol.isnot(None), Asset.asset_class != "Cash").all()
        )

        stock_assets = [a for a in all_assets if a.asset_class != "Crypto"]
        crypto_assets = [a for a in all_assets if a.asset_class == "Crypto"]

        logger.info(
            "Found %d stock/ETF and %d crypto assets",
            len(stock_assets),
            len(crypto_assets),
        )

        stock_stats = backfill_stocks(db, stock_assets)
        crypto_stats = backfill_crypto(db, crypto_assets)

        logger.info("Backfill complete:")
        logger.info(
            "  Stocks: %d updated, %d failed",
            stock_stats["updated"],
            stock_stats["failed"],
        )
        logger.info(
            "  Crypto: %d updated, %d failed",
            crypto_stats["updated"],
            crypto_stats["failed"],
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
