"""Tests for KuCoin broker parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.brokers.kucoin.constants import parse_symbol


class TestKuCoinSymbolParsing:
    """Tests for KuCoin symbol parsing."""

    def test_parse_btc_usdt(self):
        base, quote = parse_symbol("BTC-USDT")
        assert base == "BTC"
        assert quote == "USDT"

    def test_parse_eth_btc(self):
        base, quote = parse_symbol("ETH-BTC")
        assert base == "ETH"
        assert quote == "BTC"

    def test_parse_sol_usdt(self):
        base, quote = parse_symbol("SOL-USDT")
        assert base == "SOL"
        assert quote == "USDT"

    def test_parse_lowercase(self):
        base, quote = parse_symbol("btc-usdt")
        assert base == "BTC"
        assert quote == "USDT"

    def test_parse_no_dash_fallback(self):
        base, quote = parse_symbol("BTCUSDT")
        assert base == "BTC"
        assert quote == "USDT"

    def test_parse_unknown_symbol(self):
        base, quote = parse_symbol("XYZ")
        assert base == "XYZ"
        assert quote == "UNKNOWN"


class TestKuCoinParserMetadata:
    """Tests for KuCoinParser class metadata."""

    def test_broker_type(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        assert KuCoinParser.broker_type() == "kucoin"

    def test_broker_name(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        assert KuCoinParser.broker_name() == "KuCoin"

    def test_supported_extensions(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        assert KuCoinParser.supported_extensions() == [".csv"]

    def test_has_api(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        assert KuCoinParser.has_api() is True


class TestKuCoinTradeCSVParsing:
    """Tests for parsing KuCoin trade history CSV."""

    @pytest.fixture
    def sample_csv(self) -> bytes:
        fixture_path = Path(__file__).parent / "fixtures" / "kucoin_trades_sample.csv"
        return fixture_path.read_bytes()

    def test_extract_date_range(self, sample_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        start_date, end_date = parser.extract_date_range(sample_csv)
        assert start_date == date(2024, 1, 15)
        assert end_date == date(2024, 2, 10)

    def test_parse_extracts_trades(self, sample_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(sample_csv)
        assert len(result.transactions) == 5

    def test_parse_buy_transaction(self, sample_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(sample_csv)

        btc_buy = result.transactions[0]
        assert btc_buy.symbol == "BTC"
        assert btc_buy.transaction_type == "Buy"
        assert btc_buy.quantity == Decimal("0.5")
        assert btc_buy.price_per_unit == Decimal("42000.00")
        assert btc_buy.amount == Decimal("21000.00")
        assert btc_buy.fees == Decimal("10.50")
        assert btc_buy.currency == "USDT"

    def test_parse_sell_transaction(self, sample_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(sample_csv)

        btc_sell = result.transactions[1]
        assert btc_sell.symbol == "BTC"
        assert btc_sell.transaction_type == "Sell"
        assert btc_sell.quantity == Decimal("0.25")
        assert btc_sell.price_per_unit == Decimal("43500.00")

    def test_parse_eth_btc_pair(self, sample_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(sample_csv)

        eth_btc = result.transactions[3]
        assert eth_btc.symbol == "ETH"
        assert eth_btc.currency == "BTC"
        assert eth_btc.transaction_type == "Buy"

    def test_parse_returns_broker_import_data(self, sample_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(sample_csv)

        assert result.start_date == date(2024, 1, 15)
        assert result.end_date == date(2024, 2, 10)
        assert len(result.transactions) == 5
        assert result.positions == []
        assert result.cash_transactions == []
        assert result.dividends == []


class TestKuCoinDepositCSVParsing:
    """Tests for parsing deposit/withdrawal CSV."""

    @pytest.fixture
    def deposit_csv(self) -> bytes:
        fixture_path = Path(__file__).parent / "fixtures" / "kucoin_deposits_sample.csv"
        return fixture_path.read_bytes()

    def test_parse_deposits(self, deposit_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(deposit_csv)

        # Only 2 completed (Processing is filtered out)
        assert len(result.cash_transactions) == 2

    def test_deposit_amount_positive(self, deposit_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(deposit_csv)

        deposits = [t for t in result.cash_transactions if t.transaction_type == "Deposit"]
        assert len(deposits) == 1
        assert deposits[0].amount == Decimal("0.5")
        assert deposits[0].currency == "BTC"

    def test_withdrawal_amount_negative(self, deposit_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(deposit_csv)

        withdrawals = [t for t in result.cash_transactions if t.transaction_type == "Withdrawal"]
        assert len(withdrawals) == 1
        assert withdrawals[0].amount == Decimal("-1000")


class TestKuCoinStakingCSVParsing:
    """Tests for parsing staking/bonus history CSV."""

    @pytest.fixture
    def staking_csv(self) -> bytes:
        return b"""Time,Currency,Amount,Remarks
2024-02-01 00:00:00,SOL,0.05,Staking Rewards
2024-02-15 00:00:00,KCS,1.2,KCS Bonus
"""

    def test_parse_staking_rewards(self, staking_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(staking_csv)

        assert len(result.dividends) == 2

    def test_staking_details(self, staking_csv):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        result = parser.parse(staking_csv)

        staking = result.dividends[0]
        assert staking.symbol == "SOL"
        assert staking.amount == Decimal("0.05")
        assert staking.transaction_type == "Staking"


class TestKuCoinEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_file_raises_error(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        with pytest.raises(ValueError, match="Empty CSV"):
            parser.parse(b"")

    def test_headers_only_raises_error(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        with pytest.raises(ValueError, match="Empty CSV"):
            parser.parse(
                b"tradeCreatedAt,orderId,symbol,side,price,size,funds,fee,liquidity,feeCurrency\n"
            )

    def test_invalid_date_skipped(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        csv_content = b"""tradeCreatedAt,orderId,symbol,side,price,size,funds,fee,liquidity,feeCurrency
invalid-date,order1,BTC-USDT,buy,42000,0.5,21000,10.50,taker,USDT
2024-01-15T10:30:00.000Z,order2,BTC-USDT,buy,42000,0.5,21000,10.50,taker,USDT
"""
        parser = KuCoinParser()
        result = parser.parse(csv_content)
        assert len(result.transactions) == 1

    def test_utf8_bom_handled(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        csv_content = b"\xef\xbb\xbftradeCreatedAt,orderId,symbol,side,price,size,funds,fee,liquidity,feeCurrency\n2024-01-15T10:30:00.000Z,order1,BTC-USDT,buy,42000,0.5,21000,10.50,taker,USDT\n"
        parser = KuCoinParser()
        result = parser.parse(csv_content)
        assert len(result.transactions) == 1

    def test_missing_fee_defaults_to_zero(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        csv_content = b"""tradeCreatedAt,orderId,symbol,side,price,size,funds,fee,liquidity,feeCurrency
2024-01-15T10:30:00.000Z,order1,BTC-USDT,buy,42000,0.5,21000,,taker,USDT
"""
        parser = KuCoinParser()
        result = parser.parse(csv_content)
        assert result.transactions[0].fees == Decimal("0")

    def test_validate_file_rejects_json(self):
        from app.services.brokers.kucoin.parser import KuCoinParser

        parser = KuCoinParser()
        is_valid, error = parser.validate_file(b"{}", "data.json")
        assert is_valid is False
        assert error is not None
        assert ".json" in error
