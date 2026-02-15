"""Consolidate legacy forex pairs into single-row format

Revision ID: consolidate_legacy_forex_pairs
Revises: rename_sector_to_category
Create Date: 2026-02-15

Legacy IBKR forex imports created TWO transaction rows per conversion.
This migration consolidates each pair into a single row:
1. Enriches the "from" row with to_holding_id, to_amount, exchange_rate
2. Normalizes amount to positive (matching new-format convention)
3. Deletes the mirror "to" row

Two legacy note formats are handled:
- import_service: "IBKR Import - Convert 1500 ILS to 420 USD @ 0.28"
- parser_adapter: "Convert to USD" / "Convert from ILS"
"""

import re
from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import text

from alembic import op

revision: str = "consolidate_legacy_forex_pairs"
down_revision: str | None = "rename_sector_to_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# import_service format: "Convert 1500 ILS to 420 USD @ 0.28"
_FULL_NOTES_RE = re.compile(r"Convert ([\d.]+) (\w+) to ([\d.]+) (\w+) @ ([\d.]+)")

# parser_adapter format: "Convert to USD" or "Convert from ILS"
_CONVERT_TO_RE = re.compile(r"^Convert to (\w+)$")
_CONVERT_FROM_RE = re.compile(r"^Convert from (\w+)$")


def _update_from_row(
    conn, from_id: int, to_holding_id: int, to_amt: Decimal, rate: Decimal, from_amt: Decimal
) -> None:
    """Enrich the from-row with forex fields and normalize amount to positive."""
    conn.execute(
        text("""
            UPDATE transactions
            SET to_holding_id = :to_holding_id,
                to_amount = :to_amount,
                exchange_rate = :exchange_rate,
                amount = :amount
            WHERE id = :id
        """),
        {
            "id": from_id,
            "to_holding_id": to_holding_id,
            "to_amount": float(to_amt),
            "exchange_rate": float(rate),
            "amount": float(from_amt),
        },
    )


def _delete_mirror(conn, mirror_id: int) -> None:
    """Delete a mirror transaction row."""
    conn.execute(
        text("DELETE FROM transactions WHERE id = :id"),
        {"id": mirror_id},
    )


def _find_holding_by_symbol(conn, account_id: int, symbol: str) -> int | None:
    """Look up a holding ID by account and asset symbol."""
    result = conn.execute(
        text("""
            SELECT h.id FROM holdings h
            JOIN assets a ON h.asset_id = a.id
            WHERE h.account_id = :account_id AND a.symbol = :symbol
            LIMIT 1
        """),
        {"account_id": account_id, "symbol": symbol},
    ).fetchone()
    return result[0] if result else None


def _migrate_full_format(conn, rows: list) -> tuple[int, int, int]:
    """Migrate rows with import_service notes: 'Convert 1500 ILS to 420 USD @ 0.28'."""
    groups: dict[tuple, list] = defaultdict(list)
    for txn_id, txn_date, notes, holding_id, symbol, account_id, _amount in rows:
        match = _FULL_NOTES_RE.search(notes)
        if not match:
            continue
        key = (str(txn_date), notes)
        groups[key].append(
            {
                "id": txn_id,
                "holding_id": holding_id,
                "symbol": symbol,
                "account_id": account_id,
                "from_amt": Decimal(match.group(1)),
                "from_curr": match.group(2),
                "to_amt": Decimal(match.group(3)),
                "to_curr": match.group(4),
                "rate": Decimal(match.group(5)),
            }
        )

    migrated = 0
    deleted = 0
    skipped = 0

    for _key, group in groups.items():
        parsed = group[0]
        from_curr = parsed["from_curr"]
        to_curr = parsed["to_curr"]

        from_row = next((r for r in group if r["symbol"] == from_curr), None)
        to_row = next((r for r in group if r["symbol"] == to_curr), None)

        if from_row is None:
            skipped += 1
            continue

        to_holding_id = (
            to_row["holding_id"]
            if to_row is not None
            else _find_holding_by_symbol(conn, from_row["account_id"], to_curr)
        )
        if to_holding_id is None:
            skipped += 1
            continue

        _update_from_row(
            conn,
            from_row["id"],
            to_holding_id,
            parsed["to_amt"],
            parsed["rate"],
            parsed["from_amt"],
        )
        migrated += 1

        if to_row is not None and to_row["id"] != from_row["id"]:
            _delete_mirror(conn, to_row["id"])
            deleted += 1

    return migrated, deleted, skipped


def _migrate_adapter_format(conn, rows: list) -> tuple[int, int, int]:
    """Migrate rows with parser_adapter notes: 'Convert to USD' / 'Convert from ILS'.

    These pairs share the same (date, account_id) and have complementary notes.
    The 'Convert to X' row is the FROM side (amount = from_amount, holding = from_currency).
    The 'Convert from Y' row is the TO side (amount = to_amount, holding = to_currency).
    """
    from_rows: dict[tuple, list] = defaultdict(list)
    to_rows: dict[tuple, list] = defaultdict(list)

    for txn_id, txn_date, notes, holding_id, symbol, account_id, amount in rows:
        match_to = _CONVERT_TO_RE.search(notes)
        match_from = _CONVERT_FROM_RE.search(notes)
        if match_to:
            target_currency = match_to.group(1)
            key = (str(txn_date), account_id, symbol, target_currency)
            from_rows[key].append(
                {
                    "id": txn_id,
                    "holding_id": holding_id,
                    "symbol": symbol,
                    "account_id": account_id,
                    "amount": abs(Decimal(str(amount))) if amount is not None else None,
                    "target_currency": target_currency,
                }
            )
        elif match_from:
            source_currency = match_from.group(1)
            key = (str(txn_date), account_id, source_currency, symbol)
            to_rows[key].append(
                {
                    "id": txn_id,
                    "holding_id": holding_id,
                    "symbol": symbol,
                    "account_id": account_id,
                    "amount": abs(Decimal(str(amount))) if amount is not None else None,
                }
            )

    migrated = 0
    deleted = 0
    skipped = 0

    for key, from_list in from_rows.items():
        to_list = to_rows.get(key, [])
        from_row = from_list[0]
        from_amt = from_row["amount"]

        if not to_list:
            # Unpaired: look up destination holding
            to_holding_id = _find_holding_by_symbol(
                conn, from_row["account_id"], from_row["target_currency"]
            )
            if to_holding_id is None or from_amt is None:
                skipped += 1
                continue
            # No mirror row means no to_amount or rate available
            skipped += 1
            continue

        to_row = to_list[0]
        to_amt = to_row["amount"]

        if from_amt is None or to_amt is None or from_amt == 0:
            skipped += 1
            continue

        rate = to_amt / from_amt

        _update_from_row(
            conn,
            from_row["id"],
            to_row["holding_id"],
            to_amt,
            rate,
            from_amt,
        )
        migrated += 1

        if to_row["id"] != from_row["id"]:
            _delete_mirror(conn, to_row["id"])
            deleted += 1

    return migrated, deleted, skipped


def upgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(
        text("""
            SELECT t.id, t.date, t.notes, t.holding_id, a.symbol, h.account_id, t.amount
            FROM transactions t
            JOIN holdings h ON t.holding_id = h.id
            JOIN assets a ON h.asset_id = a.id
            WHERE t.type = 'Forex Conversion'
              AND t.to_holding_id IS NULL
              AND t.notes IS NOT NULL
            ORDER BY t.date, t.id
        """)
    ).fetchall()

    if not rows:
        print("No legacy forex pairs to migrate")
        return

    m1, d1, s1 = _migrate_full_format(conn, rows)
    print(f"  import_service format: {m1} migrated, {d1} mirrors deleted, {s1} skipped")

    # Re-fetch remaining unmigrated rows for adapter format pass
    remaining = conn.execute(
        text("""
            SELECT t.id, t.date, t.notes, t.holding_id, a.symbol, h.account_id, t.amount
            FROM transactions t
            JOIN holdings h ON t.holding_id = h.id
            JOIN assets a ON h.asset_id = a.id
            WHERE t.type = 'Forex Conversion'
              AND t.to_holding_id IS NULL
              AND t.notes IS NOT NULL
            ORDER BY t.date, t.id
        """)
    ).fetchall()

    m2, d2, s2 = _migrate_adapter_format(conn, remaining)
    print(f"  parser_adapter format: {m2} migrated, {d2} mirrors deleted, {s2} skipped")

    print(
        f"Forex migration total: {m1 + m2} pairs converted, "
        f"{d1 + d2} mirror rows deleted, {s1 + s2} skipped"
    )


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        text("""
            UPDATE transactions
            SET to_holding_id = NULL, to_amount = NULL, exchange_rate = NULL
            WHERE type = 'Forex Conversion'
              AND to_holding_id IS NOT NULL
              AND (notes LIKE '%Convert % to % @ %'
                   OR notes LIKE 'Convert to %')
        """)
    )
    print(f"Forex downgrade: {result.rowcount} rows reverted (mirrors NOT restored)")
