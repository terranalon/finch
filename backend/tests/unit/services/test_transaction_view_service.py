"""Tests for TransactionViewService."""

from datetime import date
from decimal import Decimal

import pytest

from app.models import Asset, Holding, Transaction
from app.services.portfolio.transaction_view_service import TransactionViewService
from app.services.repositories.transaction_repository import TransactionRepository


@pytest.fixture
def cash_usd(db):
    asset = Asset(
        symbol="USD",
        name="US Dollar",
        asset_class="Cash",
        currency="USD",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@pytest.fixture
def cash_holding(db, test_account, cash_usd):
    """Holding for a cash asset, used by forex and cash activity tests."""
    holding = Holding(
        account_id=test_account.id,
        asset_id=cash_usd.id,
        quantity=Decimal("5000"),
        cost_basis=Decimal("0"),
        is_active=True,
    )
    db.add(holding)
    db.flush()
    return holding


def _create_txn(db, holding, **kwargs):
    """Helper to create a transaction with defaults."""
    defaults = {
        "holding_id": holding.id,
        "date": date(2024, 6, 15),
        "type": "Buy",
        "quantity": Decimal("10"),
        "price_per_unit": Decimal("150"),
        "fees": Decimal("5"),
        "amount": None,
        "notes": None,
    }
    defaults.update(kwargs)
    txn = Transaction(**defaults)
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def _create_forex_holdings(db, test_account, cash_usd, test_asset, *, from_qty="1000", to_qty="0"):
    """Create from/to holding pair for forex tests. Returns (from_holding, to_holding)."""
    from_holding = Holding(
        account_id=test_account.id,
        asset_id=cash_usd.id,
        quantity=Decimal(from_qty),
        cost_basis=Decimal("0"),
        is_active=True,
    )
    db.add(from_holding)
    db.flush()

    to_holding = Holding(
        account_id=test_account.id,
        asset_id=test_asset.id,
        quantity=Decimal(to_qty),
        cost_basis=Decimal("0"),
        is_active=True,
    )
    db.add(to_holding)
    db.flush()

    return from_holding, to_holding


class TestGetTrades:
    def test_computes_total(self, db, test_account, test_asset, test_holding):
        _create_txn(
            db,
            test_holding,
            type="Buy",
            quantity=Decimal("10"),
            price_per_unit=Decimal("150"),
            fees=Decimal("5"),
        )
        svc = TransactionViewService(db)
        trades, total = svc.get_trades([test_account.id])
        assert len(trades) == 1
        assert total == 1
        assert trades[0].total == Decimal("1505")  # 10*150 + 5

    def test_bit2c_currency_override(self, db, test_account, test_asset, test_holding):
        _create_txn(
            db,
            test_holding,
            type="Buy",
            notes="Bit2C Import - some info",
        )
        svc = TransactionViewService(db)
        trades, total = svc.get_trades([test_account.id])
        assert total == 1
        assert trades[0].currency == "ILS"

    def test_empty_accounts_returns_empty(self, db):
        svc = TransactionViewService(db)
        items, total = svc.get_trades([])
        assert items == []
        assert total == 0


class TestGetDividends:
    def test_returns_dividend_transactions(self, db, test_account, test_asset, test_holding):
        _create_txn(
            db,
            test_holding,
            type="Dividend",
            amount=Decimal("25.50"),
            quantity=None,
            price_per_unit=None,
        )
        svc = TransactionViewService(db)
        divs, total = svc.get_dividends([test_account.id])
        assert len(divs) == 1
        assert total == 1
        assert divs[0].amount == Decimal("25.50")
        assert divs[0].symbol == "AAPL"


class TestGetForex:
    def test_new_format_with_to_holding(self, db, test_account, test_asset, cash_usd):
        from_holding, to_holding = _create_forex_holdings(
            db, test_account, cash_usd, test_asset, to_qty="280"
        )
        _create_txn(
            db,
            from_holding,
            type="Forex Conversion",
            amount=Decimal("1000"),
            to_holding_id=to_holding.id,
            to_amount=Decimal("280"),
            exchange_rate=Decimal("0.28"),
            quantity=None,
            price_per_unit=None,
        )
        svc = TransactionViewService(db)
        forex, total = svc.get_forex([test_account.id])
        assert len(forex) == 1
        assert total == 1
        assert forex[0].from_currency == "USD"

    def test_legacy_rows_without_to_holding_excluded(self, db, test_account, cash_holding):
        """Legacy rows (to_holding_id=NULL) are excluded from forex view."""
        _create_txn(
            db,
            cash_holding,
            type="Forex Conversion",
            notes="IBKR Import - Convert 1500 ILS to 420 USD @ 0.28",
            amount=Decimal("1500"),
            quantity=None,
            price_per_unit=None,
        )
        svc = TransactionViewService(db)
        forex, total = svc.get_forex([test_account.id])
        assert total == 0
        assert len(forex) == 0

    def test_migrated_legacy_uses_abs_amount(self, db, test_account, test_asset, cash_usd):
        """Migrated legacy rows with negative amount display abs(amount)."""
        from_holding, to_holding = _create_forex_holdings(
            db, test_account, cash_usd, test_asset, to_qty="280"
        )
        _create_txn(
            db,
            from_holding,
            type="Forex Conversion",
            amount=Decimal("-1500"),
            to_holding_id=to_holding.id,
            to_amount=Decimal("420"),
            exchange_rate=Decimal("0.28"),
            quantity=None,
            price_per_unit=None,
        )
        svc = TransactionViewService(db)
        forex, total = svc.get_forex([test_account.id])
        assert total == 1
        assert forex[0].from_amount == Decimal("1500")

    def test_pagination_at_db_level(self, db, test_account, test_asset, cash_usd):
        """Pagination uses DB offset/limit, not Python slicing."""
        from_holding, to_holding = _create_forex_holdings(
            db, test_account, cash_usd, test_asset, from_qty="5000"
        )
        for i in range(3):
            _create_txn(
                db,
                from_holding,
                type="Forex Conversion",
                date=date(2024, 6, 15 + i),
                amount=Decimal("100") * (i + 1),
                to_holding_id=to_holding.id,
                to_amount=Decimal("28") * (i + 1),
                exchange_rate=Decimal("0.28"),
                quantity=None,
                price_per_unit=None,
            )

        svc = TransactionViewService(db)
        page1, total = svc.get_forex([test_account.id], limit=2, offset=0)
        assert total == 3
        assert len(page1) == 2

        page2, total2 = svc.get_forex([test_account.id], limit=2, offset=2)
        assert total2 == 3
        assert len(page2) == 1


class TestGetCashActivity:
    def test_returns_cash_transactions(self, db, test_account, cash_holding):
        _create_txn(
            db,
            cash_holding,
            type="Deposit",
            amount=Decimal("5000"),
            quantity=None,
            price_per_unit=None,
        )
        svc = TransactionViewService(db)
        cash, total = svc.get_cash_activity([test_account.id])
        assert len(cash) == 1
        assert total == 1
        assert cash[0].amount == Decimal("5000")
        assert cash[0].type == "Deposit"


class TestCountTrades:
    def test_counts_trade_transactions(self, db, test_account, test_asset, test_holding):
        _create_txn(db, test_holding, type="Buy")
        _create_txn(db, test_holding, type="Sell")
        repo = TransactionRepository(db)
        assert repo.count_trades([test_account.id]) == 2

    def test_excludes_non_trade_types(self, db, test_account, test_asset, test_holding):
        _create_txn(db, test_holding, type="Buy")
        _create_txn(
            db,
            test_holding,
            type="Dividend",
            amount=Decimal("10"),
            quantity=None,
            price_per_unit=None,
        )
        repo = TransactionRepository(db)
        assert repo.count_trades([test_account.id]) == 1

    def test_filters_by_symbol(self, db, test_account, test_asset, test_holding):
        _create_txn(db, test_holding, type="Buy")
        repo = TransactionRepository(db)
        assert repo.count_trades([test_account.id], symbol="AAPL") == 1
        assert repo.count_trades([test_account.id], symbol="MSFT") == 0


class TestCountDividends:
    def test_counts_dividend_transactions(self, db, test_account, test_asset, test_holding):
        _create_txn(
            db,
            test_holding,
            type="Dividend",
            amount=Decimal("25"),
            quantity=None,
            price_per_unit=None,
        )
        repo = TransactionRepository(db)
        assert repo.count_dividends([test_account.id]) == 1


class TestCountForex:
    def test_counts_forex_with_to_holding(self, db, test_account, test_asset, cash_usd):
        from_holding, to_holding = _create_forex_holdings(db, test_account, cash_usd, test_asset)
        _create_txn(
            db,
            from_holding,
            type="Forex Conversion",
            amount=Decimal("1000"),
            to_holding_id=to_holding.id,
            to_amount=Decimal("280"),
            exchange_rate=Decimal("0.28"),
            quantity=None,
            price_per_unit=None,
        )
        repo = TransactionRepository(db)
        assert repo.count_forex([test_account.id]) == 1

    def test_excludes_mirror_rows(self, db, test_account, cash_holding):
        """Mirror rows (to_holding_id=NULL) are not counted."""
        _create_txn(
            db,
            cash_holding,
            type="Forex Conversion",
            amount=Decimal("1500"),
            quantity=None,
            price_per_unit=None,
        )
        repo = TransactionRepository(db)
        assert repo.count_forex([test_account.id]) == 0


class TestCountCashActivity:
    def test_counts_cash_transactions(self, db, test_account, cash_holding):
        _create_txn(
            db,
            cash_holding,
            type="Deposit",
            amount=Decimal("5000"),
            quantity=None,
            price_per_unit=None,
        )
        repo = TransactionRepository(db)
        assert repo.count_cash_activity([test_account.id]) == 1


class TestParseLegacyForexNotes:
    def test_valid_format(self):
        result = TransactionViewService.parse_legacy_forex_notes(
            "IBKR Import - Convert 1500 ILS to 420 USD @ 0.28"
        )
        assert result is not None
        from_amt, from_curr, to_amt, to_curr, rate = result
        assert from_amt == Decimal("1500")
        assert from_curr == "ILS"
        assert to_amt == Decimal("420")
        assert to_curr == "USD"

    def test_invalid_format_returns_none(self):
        assert TransactionViewService.parse_legacy_forex_notes("random notes") is None

    def test_none_returns_none(self):
        assert TransactionViewService.parse_legacy_forex_notes(None) is None
