"""Integration tests for enriched transaction responses."""

from datetime import date
from decimal import Decimal

from app.models import Transaction


class TestTransactionEnrichment:
    """Test that GET /api/transactions returns symbol, asset_name, account_name."""

    def test_transaction_includes_symbol_and_names(
        self, auth_client, db, test_holding, test_asset, test_account
    ):
        """Transaction response includes symbol, asset_name, account_name."""
        txn = Transaction(
            holding_id=test_holding.id,
            date=date.today(),
            type="Buy",
            quantity=Decimal("5"),
            price_per_unit=Decimal("150.00"),
            fees=Decimal("0"),
        )
        db.add(txn)
        db.commit()

        response = auth_client.get("/api/transactions?limit=1")
        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["symbol"] == test_asset.symbol
        assert item["asset_name"] == test_asset.name
        assert item["account_name"] == test_account.name

    def test_single_transaction_includes_enrichment(
        self, auth_client, db, test_holding, test_asset, test_account
    ):
        """GET /api/transactions/{id} also includes enriched fields."""
        txn = Transaction(
            holding_id=test_holding.id,
            date=date.today(),
            type="Dividend",
            amount=Decimal("10.00"),
            fees=Decimal("0"),
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        response = auth_client.get(f"/api/transactions/{txn.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == test_asset.symbol
        assert data["asset_name"] == test_asset.name
        assert data["account_name"] == test_account.name

    def test_transaction_enrichment_nullable(self, auth_client):
        """Without transactions, empty list is returned fine."""
        response = auth_client.get("/api/transactions")
        assert response.status_code == 200
        assert response.json()["items"] == []
