"""Service for automatic ticker symbol change detection using permanent identifiers."""

import logging

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Asset

logger = logging.getLogger(__name__)


class TickerChangeDetectionService:
    """
    Automatically detect ticker symbol changes using permanent identifiers.

    When a company changes its ticker symbol (e.g., CEP -> XXI), the permanent
    identifiers (CUSIP, ISIN, CONID) remain the same. This service detects such
    changes by finding assets with matching identifiers but different symbols.
    """

    @staticmethod
    def find_ticker_changes(db: Session) -> list[dict]:
        """
        Find all ticker symbol changes by matching permanent identifiers.

        Returns list of detected changes with format:
        {
            "old_symbol": "CEP",
            "new_symbol": "XXI",
            "cusip": "12345678",
            "isin": "US1234567890",
            "confidence": "high"  # based on number of matching identifiers
        }

        Args:
            db: Database session

        Returns:
            List of ticker change dictionaries
        """
        changes = []

        # Get all assets with at least one identifier
        assets = (
            db.query(Asset)
            .filter(or_(Asset.cusip.isnot(None), Asset.isin.isnot(None), Asset.conid.isnot(None)))
            .all()
        )

        logger.info(f"Checking {len(assets)} assets for ticker changes")

        # Build identifier index for fast lookup
        cusip_map = {}  # cusip -> [asset_id]
        isin_map = {}  # isin -> [asset_id]
        conid_map = {}  # conid -> [asset_id]

        for asset in assets:
            if asset.cusip:
                if asset.cusip not in cusip_map:
                    cusip_map[asset.cusip] = []
                cusip_map[asset.cusip].append(asset)

            if asset.isin:
                if asset.isin not in isin_map:
                    isin_map[asset.isin] = []
                isin_map[asset.isin].append(asset)

            if asset.conid:
                if asset.conid not in conid_map:
                    conid_map[asset.conid] = []
                conid_map[asset.conid].append(asset)

        # Find duplicates (multiple assets with same identifier)
        seen_pairs = set()

        for identifier_map, id_type in [
            (cusip_map, "CUSIP"),
            (isin_map, "ISIN"),
            (conid_map, "CONID"),
        ]:
            for identifier, asset_list in identifier_map.items():
                if len(asset_list) > 1:
                    # Multiple assets share this identifier - likely ticker change!
                    for i in range(len(asset_list)):
                        for j in range(i + 1, len(asset_list)):
                            asset1 = asset_list[i]
                            asset2 = asset_list[j]

                            # Create unique pair key (sorted to avoid duplicates)
                            pair_key = tuple(sorted([asset1.id, asset2.id]))

                            if pair_key in seen_pairs:
                                continue

                            seen_pairs.add(pair_key)

                            # Count matching identifiers for confidence
                            matches = 0
                            if asset1.cusip and asset1.cusip == asset2.cusip:
                                matches += 1
                            if asset1.isin and asset1.isin == asset2.isin:
                                matches += 1
                            if asset1.conid and asset1.conid == asset2.conid:
                                matches += 1

                            # Determine confidence
                            if matches >= 2:
                                confidence = "high"
                            elif matches == 1:
                                confidence = "medium"
                            else:
                                confidence = "low"

                            changes.append(
                                {
                                    "asset1_id": asset1.id,
                                    "asset1_symbol": asset1.symbol,
                                    "asset1_name": asset1.name,
                                    "asset2_id": asset2.id,
                                    "asset2_symbol": asset2.symbol,
                                    "asset2_name": asset2.name,
                                    "cusip": asset1.cusip or asset2.cusip,
                                    "isin": asset1.isin or asset2.isin,
                                    "conid": asset1.conid or asset2.conid,
                                    "matching_identifiers": matches,
                                    "confidence": confidence,
                                    "detected_via": id_type,
                                }
                            )

                            logger.info(
                                f"Detected ticker change: {asset1.symbol} <-> {asset2.symbol} "
                                f"({matches} matching IDs, confidence: {confidence})"
                            )

        return changes

    @staticmethod
    def apply_ticker_changes_to_reconstruction(
        db: Session, reconstructed_holdings: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """
        Apply detected ticker changes to reconstruction results.

        Merges holdings that belong to the same security (same permanent identifiers).

        Args:
            db: Database session
            reconstructed_holdings: Holdings from reconstruction service

        Returns:
            Tuple of (merged_holdings, applied_changes)
        """
        # Detect all ticker changes
        changes = TickerChangeDetectionService.find_ticker_changes(db)

        if not changes:
            logger.debug("No ticker changes detected")
            return (reconstructed_holdings, [])

        # Build merge map: asset_id -> primary_asset_id
        merge_map = {}

        for change in changes:
            if change["confidence"] == "high":
                # Use lexicographically later symbol as primary (XXI > CEP)
                if change["asset1_symbol"] > change["asset2_symbol"]:
                    primary_id = change["asset1_id"]
                    secondary_id = change["asset2_id"]
                else:
                    primary_id = change["asset2_id"]
                    secondary_id = change["asset1_id"]

                merge_map[secondary_id] = primary_id
                logger.info(
                    f"Will merge {change['asset2_symbol'] if primary_id == change['asset1_id'] else change['asset1_symbol']} "
                    f"into {change['asset1_symbol'] if primary_id == change['asset1_id'] else change['asset2_symbol']}"
                )

        # Apply merges
        merged_holdings = {}
        applied_changes = []

        for holding in reconstructed_holdings:
            asset_id = holding["asset_id"]

            # Check if this asset should be merged
            if asset_id in merge_map:
                primary_id = merge_map[asset_id]

                # Find the asset objects for logging
                old_asset = db.query(Asset).get(asset_id)
                new_asset = db.query(Asset).get(primary_id)

                logger.info(
                    f"Merging {old_asset.symbol} ({holding['quantity']} shares) "
                    f"into {new_asset.symbol}"
                )

                # Merge into primary
                if primary_id in merged_holdings:
                    merged_holdings[primary_id]["quantity"] += holding["quantity"]
                    merged_holdings[primary_id]["cost_basis"] += holding["cost_basis"]
                else:
                    merged_holdings[primary_id] = {
                        **holding,
                        "asset_id": primary_id,
                        "symbol": new_asset.symbol,
                        "quantity": holding["quantity"],
                        "cost_basis": holding["cost_basis"],
                    }

                applied_changes.append(
                    {
                        "from_symbol": old_asset.symbol,
                        "to_symbol": new_asset.symbol,
                        "quantity_merged": float(holding["quantity"]),
                    }
                )
            else:
                # No merge needed
                if asset_id in merged_holdings:
                    # Shouldn't happen, but handle just in case
                    merged_holdings[asset_id]["quantity"] += holding["quantity"]
                    merged_holdings[asset_id]["cost_basis"] += holding["cost_basis"]
                else:
                    merged_holdings[asset_id] = holding

        return (list(merged_holdings.values()), applied_changes)
