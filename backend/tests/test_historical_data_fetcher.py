"""Tests for HistoricalDataFetcher orchestrator."""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Account, Asset, Holding, Portfolio
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.historical_data_fetcher import HistoricalDataFetcher


@pytest.fixture
def test_db():
    """Create a PostgreSQL test database for full compatibility."""
    db_host = os.getenv("DATABASE_HOST", "portfolio_tracker_db")
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        f"postgresql://portfolio_user:dev_password@{db_host}:5432/portfolio_tracker_test",
    )

    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)

    yield engine

    # Clean up test data
    with engine.connect() as conn:
        conn.execute(
            text(
                "DELETE FROM holdings WHERE account_id IN (SELECT id FROM accounts WHERE name LIKE 'Test Hist%')"
            )
        )
        conn.execute(text("DELETE FROM accounts WHERE name LIKE 'Test Hist%'"))
        conn.execute(text("DELETE FROM portfolios WHERE name LIKE 'Test Hist%'"))
        conn.execute(text("DELETE FROM users WHERE email LIKE 'test_hist%'"))
        conn.execute(text("DELETE FROM assets WHERE symbol LIKE 'HIST_TEST_%'"))
        conn.commit()


@pytest.fixture
def db_session(test_db):
    """Create a database session."""
    test_session_maker = sessionmaker(bind=test_db)
    session = test_session_maker()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test_hist_fetch@example.com",
        password_hash=AuthService.hash_password("test123"),
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_portfolio(db_session, test_user):
    """Create a test portfolio."""
    portfolio = Portfolio(user_id=test_user.id, name="Test Hist Portfolio")
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)
    return portfolio


@pytest.fixture
def test_account_with_holdings(db_session, test_portfolio):
    """Create a test account with holdings."""
    account = Account(
        portfolio_id=test_portfolio.id,
        name="Test Hist Account",
        account_type="Brokerage",
        institution="Test",
        currency="USD",
    )
    db_session.add(account)
    db_session.flush()

    # Create test assets
    stock = Asset(symbol="HIST_TEST_AAPL", name="Apple Test", asset_class="Stock", currency="USD")
    crypto = Asset(
        symbol="HIST_TEST_BTC", name="Bitcoin Test", asset_class="Crypto", currency="USD"
    )
    cash = Asset(symbol="HIST_TEST_USD", name="US Dollar Test", asset_class="Cash", currency="USD")
    db_session.add_all([stock, crypto, cash])
    db_session.flush()

    # Create holdings
    db_session.add(
        Holding(
            account_id=account.id,
            asset_id=stock.id,
            quantity=Decimal("10"),
            cost_basis=Decimal("1500"),
            is_active=True,
        )
    )
    db_session.add(
        Holding(
            account_id=account.id,
            asset_id=crypto.id,
            quantity=Decimal("1"),
            cost_basis=Decimal("50000"),
            is_active=True,
        )
    )
    db_session.add(
        Holding(
            account_id=account.id,
            asset_id=cash.id,
            quantity=Decimal("1000"),
            cost_basis=Decimal("1000"),
            is_active=True,
        )
    )
    db_session.commit()

    return {
        "account_id": account.id,
        "stock_id": stock.id,
        "crypto_id": crypto.id,
        "cash_id": cash.id,
    }


class TestEnsureHistoricalData:
    """Tests for the historical data orchestrator."""

    @patch("app.services.historical_data_fetcher.PriceFetcher")
    @patch("app.services.historical_data_fetcher.CurrencyService")
    def test_fetches_prices_for_all_account_assets(
        self, mock_currency, mock_price, db_session, test_account_with_holdings
    ):
        """Should fetch historical prices for all non-cash assets in account."""
        account_id = test_account_with_holdings["account_id"]

        mock_price.fetch_and_store_historical_prices.return_value = 5
        mock_currency.fetch_and_store_historical_rates.return_value = 3

        stats = HistoricalDataFetcher.ensure_historical_data(
            db_session, account_id, date(2024, 1, 1), date(2024, 1, 5)
        )

        # Should fetch prices for stock and crypto (not cash)
        assert mock_price.fetch_and_store_historical_prices.call_count == 2

        # Should fetch exchange rates
        mock_currency.fetch_and_store_historical_rates.assert_called()

        assert "prices_fetched" in stats
        assert "rates_fetched" in stats

    @patch("app.services.historical_data_fetcher.PriceFetcher")
    @patch("app.services.historical_data_fetcher.CurrencyService")
    def test_returns_stats_on_success(
        self, mock_currency, mock_price, db_session, test_account_with_holdings
    ):
        """Should return comprehensive stats."""
        account_id = test_account_with_holdings["account_id"]

        mock_price.fetch_and_store_historical_prices.return_value = 10
        mock_currency.fetch_and_store_historical_rates.return_value = 5

        stats = HistoricalDataFetcher.ensure_historical_data(
            db_session, account_id, date(2024, 1, 1), date(2024, 1, 10)
        )

        assert stats["prices_fetched"] == 20  # 10 per asset * 2 assets
        assert stats["assets_processed"] == 2
        assert stats["errors"] == []

    @patch("app.services.historical_data_fetcher.PriceFetcher")
    @patch("app.services.historical_data_fetcher.CurrencyService")
    def test_handles_price_fetch_errors_gracefully(
        self, mock_currency, mock_price, db_session, test_account_with_holdings
    ):
        """Should continue processing even if one asset fails."""
        account_id = test_account_with_holdings["account_id"]

        # First call fails, second succeeds
        mock_price.fetch_and_store_historical_prices.side_effect = [
            Exception("API error"),
            5,
        ]
        mock_currency.fetch_and_store_historical_rates.return_value = 3

        stats = HistoricalDataFetcher.ensure_historical_data(
            db_session, account_id, date(2024, 1, 1), date(2024, 1, 5)
        )

        assert len(stats["errors"]) == 1
        assert stats["prices_fetched"] == 5
        assert stats["assets_processed"] == 1
