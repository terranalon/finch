# Historical Performance - Transaction Reconstruction

> This document describes the algorithm and implementation for reconstructing portfolio holdings from transaction history to enable accurate historical performance tracking.

## Problem Statement

**Current Issue:** Historical performance charts use current holdings to calculate past portfolio values. This is fundamentally incorrect because it doesn't reflect what was actually held on historical dates.

**Example of the Problem:**
- Today: You hold 100 shares of AAPL
- 6 months ago: You held 0 shares (bought them 3 months ago)
- Current approach: Shows you owned 100 shares 6 months ago (incorrect)
- Correct approach: Show 0 shares 6 months ago, 100 shares 3 months ago onward

## Solution: Transaction-Based Reconstruction

Reconstruct the exact portfolio composition for any historical date by replaying all transactions chronologically.

## Algorithm Design

### Phase 1: Transaction Replay

**Input:** Account ID, Target Date
**Output:** Holdings as they existed on that date

**Steps:**
1. Query all transactions up to target date
2. Order transactions chronologically (date ASC, id ASC)
3. Initialize empty holdings map
4. For each transaction:
   - If Buy: Add to position, track lot for FIFO
   - If Sell: Reduce position using FIFO
   - If Dividend: Track for income (doesn't affect quantity)
5. Return non-zero holdings

### Phase 2: Portfolio Valuation

**Input:** Reconstructed holdings, Target Date
**Output:** Total portfolio value in USD

**Steps:**
1. For each holding:
   - Get historical price for asset on target date
   - Calculate value in asset's native currency
   - Convert to USD using historical exchange rate
2. Sum all holdings' values

### FIFO Lot Tracking

**Why FIFO?**
- Default tax treatment in most jurisdictions
- Provides accurate cost basis calculations
- Essential for capital gains reporting

**Algorithm:**
```
Buy Transaction:
  1. Create new lot with:
     - quantity
     - cost_per_unit
     - purchase_date
  2. Add to holdings.lots array
  3. Update aggregate quantity and cost_basis

Sell Transaction:
  1. Initialize remaining_to_sell = transaction.quantity
  2. For each lot in holdings.lots (oldest first):
     a. If remaining_to_sell <= 0: break
     b. sold_from_lot = min(lot.remaining, remaining_to_sell)
     c. lot.remaining -= sold_from_lot
     d. holdings.cost_basis -= sold_from_lot * lot.cost_per_unit
     e. remaining_to_sell -= sold_from_lot
  3. Update aggregate quantity
```

## Implementation Components

### PortfolioReconstructionService

**Location:** `backend/app/services/portfolio_reconstruction_service.py`

**Key Methods:**
- `reconstruct_holdings(db, account_id, as_of_date)` - Reconstruct holdings for a date
- `calculate_portfolio_value(db, account_id, as_of_date)` - Calculate total value

### Integration with Snapshot Service

**Location:** `backend/app/services/snapshot_service.py`

**Modified Method:**
```python
def _create_account_snapshot(
    db: Session,
    account: Account,
    snapshot_date: date,
    use_reconstruction: bool = True  # NEW parameter
):
    if use_reconstruction:
        # Use transaction-based reconstruction
        portfolio_value = PortfolioReconstructionService.calculate_portfolio_value(
            db, account.id, snapshot_date
        )
    else:
        # Legacy: Use current holdings (inaccurate)
        # ... existing code ...
```

## Data Requirements

### Historical Price Data

**Table:** `asset_prices`
**Requirement:** Daily closing prices for all assets

**Fetching Strategy:**
1. Daily Airflow job fetches latest prices
2. Backfill historical prices on demand
3. Cache in database for fast reconstruction

### Historical Exchange Rates

**Table:** `exchange_rates`
**Requirement:** Daily rates for all currency pairs

**Fetching Strategy:**
1. Daily Airflow job updates rates
2. Use last available rate if date missing
3. Critical for multi-currency portfolios

## Validation Strategy

### Accuracy Validation

**Endpoint:** `GET /api/snapshots/accounts/{account_id}/validate`

**Process:**
1. Reconstruct holdings for today
2. Compare with current holdings (from holdings table)
3. Report discrepancies (should be 0)

**Success Criteria:** 100% match for today's date

### Performance Testing

**Metrics:**
- Reconstruction time for 1 year of transactions
- Backfill time for 365 days of snapshots
- Memory usage during reconstruction

**Target:** Backfill 365 days in < 5 minutes

## Backfilling Historical Snapshots

**Endpoint:** `POST /api/snapshots/accounts/{account_id}/backfill`

**Process:**
1. For each day from start_date to end_date:
   - Check if snapshot exists
   - If not: Reconstruct holdings and create snapshot
   - Store in historical_snapshots table
2. Return stats (created, skipped)

**Use Cases:**
- Initial setup: Backfill entire account history
- Data corrections: Regenerate snapshots after transaction edits
- New accounts: Generate historical baseline

## Edge Cases

### Handling Missing Data

**Missing Price:**
- Skip asset in valuation for that date
- Log warning for investigation
- Continue with other assets

**Missing Exchange Rate:**
- Use last available rate
- Log warning
- Document as approximation

### Dividend Reinvestment (DRIP)

**Detection:**
- Look for Buy transaction on same date as Dividend
- Mark dividend as "[REINVESTED]" in notes
- Track both cash dividend and reinvested shares

### Stock Splits

**Handling:**
- Adjust historical quantities retroactively
- Update all lots with split ratio
- Ensure cost_per_unit adjusted proportionally

## Performance Optimizations

### Database Indexes

```sql
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_holding ON transactions(holding_id);
CREATE INDEX idx_asset_prices_date ON asset_prices(asset_id, date);
CREATE INDEX idx_exchange_rates_date ON exchange_rates(from_currency, to_currency, date);
```

### Caching Strategy

- Cache reconstructed holdings for frequently accessed dates
- Invalidate cache when transactions are added/edited
- Consider Redis for distributed caching (future)

### Batch Processing

- Process multiple accounts in parallel (Airflow tasks)
- Use connection pooling for database queries
- Limit query result size with pagination

---

## Related Documentation

- [IBKR Import Plan](./IBKR_IMPORT_PLAN.md) - How to get transaction data
- [API Documentation](./API_DOCUMENTATION.md) - Reconstruction endpoints
- [Architecture](./ARCHITECTURE.md) - Overall system design

---

**Last Updated:** 2026-01-09