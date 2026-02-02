"""Tests for Binance broker parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.services.brokers.binance.parser import BinanceParser, parse_symbol


class TestSymbolParsing:
    """Tests for Binance symbol parsing."""

    def test_parse_btc_usdt(self):
        base, quote = parse_symbol("BTCUSDT")
        assert base == "BTC"
        assert quote == "USDT"

    def test_parse_eth_btc(self):
        base, quote = parse_symbol("ETHBTC")
        assert base == "ETH"
        assert quote == "BTC"

    def test_parse_doge_usdc(self):
        base, quote = parse_symbol("DOGEUSDC")
        assert base == "DOGE"
        assert quote == "USDC"

    def test_parse_bnb_busd(self):
        base, quote = parse_symbol("BNBBUSD")
        assert base == "BNB"
        assert quote == "BUSD"

    def test_parse_lowercase(self):
        base, quote = parse_symbol("btcusdt")
        assert base == "BTC"
        assert quote == "USDT"

    def test_parse_unknown_quote(self):
        base, quote = parse_symbol("BTCXYZ")
        assert base == "BTCXYZ"
        assert quote == "UNKNOWN"

    def test_parse_eur_pair(self):
        base, quote = parse_symbol("BTCEUR")
        assert base == "BTC"
        assert quote == "EUR"


class TestBinanceParserMetadata:
    """Tests for BinanceParser class metadata."""

    def test_broker_type(self):
        assert BinanceParser.broker_type() == "binance"

    def test_broker_name(self):
        assert BinanceParser.broker_name() == "Binance"

    def test_supported_extensions(self):
        assert BinanceParser.supported_extensions() == [".csv"]

    def test_has_api(self):
        assert BinanceParser.has_api() is True


class TestBinanceCSVParsing:
    """Tests for parsing Binance CSV files."""

    @pytest.fixture
    def sample_csv(self) -> bytes:
        """Load the sample Binance trades CSV."""
        fixture_path = Path(__file__).parent / "fixtures" / "binance_trades_sample.csv"
        return fixture_path.read_bytes()

    def test_extract_date_range(self, sample_csv):
        parser = BinanceParser()
        start_date, end_date = parser.extract_date_range(sample_csv)
        assert start_date == date(2024, 1, 15)
        assert end_date == date(2024, 2, 10)

    def test_parse_extracts_trades(self, sample_csv):
        parser = BinanceParser()
        result = parser.parse(sample_csv)
        assert len(result.transactions) == 5

    def test_parse_buy_transaction(self, sample_csv):
        parser = BinanceParser()
        result = parser.parse(sample_csv)

        # First transaction is a BTC buy
        btc_buy = result.transactions[0]
        assert btc_buy.symbol == "BTC"
        assert btc_buy.transaction_type == "Buy"
        assert btc_buy.quantity == Decimal("0.5")
        assert btc_buy.price_per_unit == Decimal("42000.00")
        assert btc_buy.amount == Decimal("21000.00")
        assert btc_buy.fees == Decimal("10.50")
        assert btc_buy.currency == "USDT"

    def test_parse_sell_transaction(self, sample_csv):
        parser = BinanceParser()
        result = parser.parse(sample_csv)

        # Second transaction is a BTC sell
        btc_sell = result.transactions[1]
        assert btc_sell.symbol == "BTC"
        assert btc_sell.transaction_type == "Sell"
        assert btc_sell.quantity == Decimal("0.25")
        assert btc_sell.price_per_unit == Decimal("43500.00")

    def test_parse_eth_btc_pair(self, sample_csv):
        parser = BinanceParser()
        result = parser.parse(sample_csv)

        # Fourth transaction is ETH/BTC pair
        eth_btc = result.transactions[3]
        assert eth_btc.symbol == "ETH"
        assert eth_btc.currency == "BTC"
        assert eth_btc.transaction_type == "Buy"

    def test_parse_returns_broker_import_data(self, sample_csv):
        parser = BinanceParser()
        result = parser.parse(sample_csv)

        assert result.start_date == date(2024, 1, 15)
        assert result.end_date == date(2024, 2, 10)
        assert len(result.transactions) == 5
        assert result.positions == []
        assert result.cash_transactions == []
        assert result.dividends == []


class TestBinanceTransactionHistory:
    """Tests for parsing transaction history (deposits/withdrawals)."""

    @pytest.fixture
    def deposit_csv(self) -> bytes:
        return b"""Date(UTC),Operation,Coin,Amount,TxId
2024-01-10 08:00:00,Deposit,BTC,0.5,abc123
2024-01-15 12:30:00,Deposit,ETH,2.0,def456
2024-02-01 09:00:00,Withdraw,BTC,0.25,ghi789
"""

    def test_parse_deposits(self, deposit_csv):
        parser = BinanceParser()
        result = parser.parse(deposit_csv)

        # Should have 2 deposits and 1 withdrawal
        assert len(result.cash_transactions) == 3

    def test_deposit_amount_positive(self, deposit_csv):
        parser = BinanceParser()
        result = parser.parse(deposit_csv)

        deposits = [t for t in result.cash_transactions if t.transaction_type == "Deposit"]
        assert len(deposits) == 2
        assert deposits[0].amount == Decimal("0.5")
        assert deposits[0].currency == "BTC"

    def test_withdrawal_amount_negative(self, deposit_csv):
        parser = BinanceParser()
        result = parser.parse(deposit_csv)

        withdrawals = [t for t in result.cash_transactions if t.transaction_type == "Withdrawal"]
        assert len(withdrawals) == 1
        assert withdrawals[0].amount == Decimal("-0.25")


class TestBinanceDistributionHistory:
    """Tests for parsing distribution history (staking, airdrops)."""

    @pytest.fixture
    def distribution_csv(self) -> bytes:
        return b"""Date(UTC),Coin,Amount,Distribution Type
2024-01-20 00:00:00,ETH,0.001,Staking Rewards
2024-02-01 00:00:00,BNB,0.5,Airdrop
"""

    def test_parse_distributions(self, distribution_csv):
        parser = BinanceParser()
        result = parser.parse(distribution_csv)

        assert len(result.dividends) == 2

    def test_distribution_details(self, distribution_csv):
        parser = BinanceParser()
        result = parser.parse(distribution_csv)

        staking = result.dividends[0]
        assert staking.symbol == "ETH"
        assert staking.amount == Decimal("0.001")
        assert staking.transaction_type == "Distribution"


class TestBinanceEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_file_raises_error(self):
        parser = BinanceParser()
        with pytest.raises(ValueError, match="Empty CSV"):
            parser.parse(b"")

    def test_headers_only_raises_error(self):
        parser = BinanceParser()
        with pytest.raises(ValueError, match="Empty CSV"):
            parser.parse(b"Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n")

    def test_invalid_date_skipped(self):
        csv_content = b"""Date(UTC),Pair,Side,Price,Executed,Amount,Fee
invalid-date,BTCUSDT,BUY,42000.00,0.5,21000.00,10.50
2024-01-15 10:30:00,BTCUSDT,BUY,42000.00,0.5,21000.00,10.50
"""
        parser = BinanceParser()
        result = parser.parse(csv_content)
        # Should only parse the valid row
        assert len(result.transactions) == 1

    def test_utf8_bom_handled(self):
        # CSV with UTF-8 BOM
        csv_content = b"\xef\xbb\xbfDate(UTC),Pair,Side,Price,Executed,Amount,Fee\n2024-01-15 10:30:00,BTCUSDT,BUY,42000.00,0.5,21000.00,10.50\n"
        parser = BinanceParser()
        result = parser.parse(csv_content)
        assert len(result.transactions) == 1

    def test_alternative_date_format(self):
        csv_content = b"""Date(UTC),Pair,Side,Price,Executed,Amount,Fee
2024/01/15 10:30:00,BTCUSDT,BUY,42000.00,0.5,21000.00,10.50
"""
        parser = BinanceParser()
        result = parser.parse(csv_content)
        assert len(result.transactions) == 1
        assert result.transactions[0].trade_date == date(2024, 1, 15)

    def test_missing_fee_defaults_to_zero(self):
        csv_content = b"""Date(UTC),Pair,Side,Price,Executed,Amount,Fee
2024-01-15 10:30:00,BTCUSDT,BUY,42000.00,0.5,21000.00,
"""
        parser = BinanceParser()
        result = parser.parse(csv_content)
        assert result.transactions[0].fees == Decimal("0")

    def test_lowercase_column_names(self):
        csv_content = b"""date(utc),pair,side,price,executed,amount,fee
2024-01-15 10:30:00,BTCUSDT,BUY,42000.00,0.5,21000.00,10.50
"""
        parser = BinanceParser()
        result = parser.parse(csv_content)
        assert len(result.transactions) == 1
