"""Tests for transaction hash service."""

from datetime import date
from decimal import Decimal

from app.services.transaction_hash_service import compute_transaction_hash


class TestComputeTransactionHash:
    def test_same_inputs_produce_same_hash(self):
        hash1 = compute_transaction_hash(
            external_txn_id="TXN123",
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        hash2 = compute_transaction_hash(
            external_txn_id="TXN123",
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        assert hash1 == hash2

    def test_different_external_id_produces_different_hash(self):
        hash1 = compute_transaction_hash(
            external_txn_id="TXN123",
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        hash2 = compute_transaction_hash(
            external_txn_id="TXN456",
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        assert hash1 != hash2

    def test_none_external_id_still_produces_hash(self):
        hash1 = compute_transaction_hash(
            external_txn_id=None,
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        assert hash1 is not None
        assert len(hash1) == 64  # SHA256 hex

    def test_hash_is_64_chars(self):
        result = compute_transaction_hash(
            external_txn_id="X",
            txn_date=date(2024, 1, 1),
            symbol="ETH",
            txn_type="Sell",
            quantity=Decimal("2.0"),
            price=Decimal("2000.00"),
            fees=Decimal("5.00"),
        )
        assert len(result) == 64

    def test_different_quantity_produces_different_hash(self):
        hash1 = compute_transaction_hash(
            external_txn_id="TXN123",
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        hash2 = compute_transaction_hash(
            external_txn_id="TXN123",
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("2.0"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        assert hash1 != hash2

    def test_symbol_case_normalized(self):
        """Symbol should be normalized to uppercase."""
        hash1 = compute_transaction_hash(
            external_txn_id="TXN123",
            txn_date=date(2024, 1, 15),
            symbol="btc",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        hash2 = compute_transaction_hash(
            external_txn_id="TXN123",
            txn_date=date(2024, 1, 15),
            symbol="BTC",
            txn_type="Buy",
            quantity=Decimal("1.5"),
            price=Decimal("40000.00"),
            fees=Decimal("10.00"),
        )
        assert hash1 == hash2
