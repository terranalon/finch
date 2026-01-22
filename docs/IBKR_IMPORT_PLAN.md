# IBKR Import Fixes & Transaction-Based Historical Performance

## Implementation Status

**✅ Phase 1 COMPLETED (Jan 9, 2026):**
- ✅ Phase 1.1-1.3: Flex Query import service fully implemented
- ✅ Phase 1.4: Tested with real IBKR account - **64 transactions imported** (was 0 with TWS)
- ✅ Phase 1.5: Validated Flex Query superiority over TWS API
- ✅ Phase 1.6: **TWS API DEPRECATED** - All TWS code removed from codebase

**Current Focus:** Ready to proceed with Phase 2 (Dividend DRIP detection)

---

## Executive Summary

Fix IBKR import to properly import transactions and dividends, then enable accurate historical performance tracking using transaction reconstruction.

**Issues (RESOLVED):**
- ✅ Transactions show "0 imported" - **FIXED** with Flex Query API
- ✅ Dividends never imported - **FIXED** with Flex Query API (7 dividends imported)
- ✅ TWS API requires local IB Gateway - **REMOVED** in favor of cloud-ready Flex Query API
- ⏳ Historical performance uses current holdings - **IN PROGRESS** (Phase 4)

**Solution:**
Migrated from TWS API to **Flex Query API** for cloud-ready, complete historical data import.

## Root Cause Analysis

### Transaction Import Failure

**Location:** `backend/app/services/ibkr_tws_client.py:174-231`

**Root Cause:** TWS API's `reqExecutions()` only returns executions from current trading session, NOT full historical data.

**Evidence:**
- Line 198: Uses time filter `strftime("%Y%m%d-00:00:00")`
- TWS API limitation: Historical executions not accessible via this method
- Returns empty list silently

**Fix:** Use Flex Query API which provides complete transaction history.

### Dividend Import Missing

**Location:** `backend/app/services/ibkr_import_service.py:127`

**Root Cause:**
- No TWS client method to fetch dividends
- `_import_dividends()` exists (lines 465-555) but never called
- TWS parser lacks `parse_dividends()` method

**Available Solution:**
- Legacy `ibkr_parser.py:extract_dividends()` (lines 167-236) ALREADY EXISTS
- Flex Query parser has complete dividend support
- Just needs to be wired up!

## Implementation Plan

---

## PHASE 0: DOCUMENTATION STRUCTURE (30 minutes)

**Goal:** Organize project documentation before implementation

### 0.1 Create Documentation Directory

**New Directory Structure:**
```
docs/
  IBKR_IMPORT_PLAN.md          # This plan (moved from Claude plans)
  ARCHITECTURE.md               # Overall system architecture reference
  API_DOCUMENTATION.md          # API endpoints and usage guide
  HISTORICAL_PERFORMANCE.md     # Transaction reconstruction algorithm design
```

**Files to Create:**
- `docs/IBKR_IMPORT_PLAN.md` - Copy this plan into project (version controlled)
- `docs/ARCHITECTURE.md` - Placeholder for architecture patterns and design decisions
- `docs/API_DOCUMENTATION.md` - Placeholder for API endpoint documentation
- `docs/HISTORICAL_PERFORMANCE.md` - Placeholder for reconstruction algorithm details

**Benefits:**
- Version controlled documentation
- Accessible to future developers and AI assistants
- Separate concerns into focused documents
- Easier to maintain and reference

---

## PHASE 1: FIX TRANSACTION IMPORT (2-3 days)

**Goal:** Get all transactions importing using Flex Query API

**IMPORTANT:** This phase will thoroughly test Flex Query API. **TWS API support will only be deprecated AFTER validation** confirms Flex Query provides all required functionality.

### 1.1 Create Flex Query Import Service

**File:** `backend/app/services/ibkr_flex_import_service.py` (NEW)

```python
class IBKRFlexImportService:
    """Cloud-ready import using Flex Query API."""

    @staticmethod
    def import_all(db: Session, account_id: int,
                   flex_token: str, flex_query_id: str) -> Dict:
        """
        Import IBKR data using Flex Query API.

        Steps:
        1. Fetch Flex Query XML report
        2. Parse using existing IBKRParser
        3. Import positions, transactions, dividends, cash
        """
        # Fetch report
        xml_data = IBKRFlexClient.fetch_flex_report(flex_token, flex_query_id)

        # Parse (reuse existing parser!)
        root = IBKRParser.parse_xml(xml_data)
        positions = IBKRParser.extract_positions(root)
        transactions = IBKRParser.extract_transactions(root)
        dividends = IBKRParser.extract_dividends(root)  # Already exists!
        cash = IBKRParser.extract_cash_balances(root)

        # Import (reuse existing methods!)
        pos_stats = _import_positions(db, account_id, positions)
        txn_stats = _import_transactions(db, account_id, transactions)
        div_stats = _import_dividends(db, account_id, dividends)  # Already exists!
        cash_stats = _import_cash_balances(db, account_id, cash)

        return {
            "status": "completed",
            "positions": pos_stats,
            "transactions": txn_stats,
            "dividends": div_stats,
            "cash": cash_stats
        }
```

**Complexity:** LOW - mostly wiring existing components

### 1.2 Add Flex Query Import Endpoint

**File:** `backend/app/routers/ibkr.py`

```python
@router.post("/import-flex/{account_id}")
async def import_ibkr_flex_data(
    account_id: int,
    flex_token: str,
    flex_query_id: str,
    db: Session = Depends(get_db)
):
    """Import using Flex Query API (cloud-ready)."""
    stats = IBKRFlexImportService.import_all(
        db, account_id, flex_token, flex_query_id
    )

    # Store credentials for future auto-import
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account.meta_data:
        account.meta_data = {}
    account.meta_data["ibkr"] = {
        "flex_token": flex_token,
        "flex_query_id": flex_query_id,
        "last_import": datetime.now().isoformat()
    }
    db.commit()

    return stats
```

### 1.3 User Setup: Create Flex Query

**IBKR Portal Setup:**
1. Login to IBKR Account Management
2. Navigate to Reports → Flex Queries → Custom Flex Queries
3. Create new query with:
   - **Sections:** Trades, CashTransactions, OpenPositions, SecuritiesInfo
   - **Date Range:** Since account opening (or specific start date)
   - **Format:** XML
4. Generate Flex Token and Query ID

### 1.4 Database Migration

**File:** `backend/alembic/versions/add_transaction_amount.py` (NEW)

```sql
-- Add amount field for cash dividends
ALTER TABLE transactions ADD COLUMN amount NUMERIC(15, 2);

-- Index for faster dividend queries
CREATE INDEX idx_transactions_type_date ON transactions(type, date);
```

**Testing:**
1. Create Flex Query in IBKR Account Management
2. Test import with `POST /import-flex/{account_id}`
3. Verify transactions table populated
4. Check for duplicates (should be 0)
5. Validate date range (complete history)

---

## PHASE 2: ENABLE DIVIDEND IMPORT (1 day)

**Goal:** Import all dividend data from Flex Query

### 2.1 Wire Up Dividend Import

**File:** `backend/app/services/ibkr_flex_import_service.py`

Already included in Phase 1.1 - just need to ensure it's called:
```python
dividends = IBKRParser.extract_dividends(root)  # Already exists!
div_stats = _import_dividends(db, account_id, dividends)  # Already exists!
```

### 2.2 Support DRIP Detection

**File:** `backend/app/services/ibkr_import_service.py`

Enhance `_import_dividends()` (lines 465-555):
```python
def _import_dividends(db: Session, account_id: int, dividends: List[Dict]) -> Dict:
    """Import dividends with DRIP detection."""

    for div in dividends:
        # Create dividend transaction
        transaction = Transaction(
            holding_id=holding.id,
            date=div["date"],
            type="Dividend",
            quantity=None,
            price_per_unit=None,
            amount=div["amount"],  # NEW: Use amount field
            fees=Decimal("0"),
            notes=f"Dividend: ${div['amount']} ({div['description']})"
        )

        # Check for DRIP (reinvested dividends)
        same_day_buy = db.query(Transaction).filter(
            Transaction.holding_id == holding.id,
            Transaction.date == div["date"],
            Transaction.type == "Buy"
        ).first()

        if same_day_buy:
            transaction.notes += " [REINVESTED]"
```

### 2.3 Update Transaction Model

**File:** `backend/app/models/transaction.py`

Add amount field:
```python
class Transaction(Base):
    # Existing fields...
    quantity: Mapped[Optional[Decimal]]  # None for dividends
    price_per_unit: Mapped[Optional[Decimal]]  # None for dividends

    # NEW: For cash dividends
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
```

**Testing:**
1. Import account with dividend history
2. Verify `type="Dividend"` transactions created
3. Check DRIP detection for reinvested dividends
4. Validate dividend amounts match IBKR records

---

## PHASE 3: SIMPLIFIED CREDENTIAL STORAGE (1 day)

**Goal:** Store IBKR credentials for easy re-import (no encryption for now)

### 3.1 Store IBKR Credentials in Environment

**File:** `.env`

```bash
# IBKR Flex Query Credentials
IBKR_FLEX_TOKEN=your_flex_token_here
IBKR_FLEX_QUERY_ID=123456
```

**OR** store in account metadata for multi-account support:

**File:** `backend/app/models/account.py`

Use existing `meta_data` JSONB field (plaintext for now):
```python
# Stored in meta_data:
{
  "ibkr": {
    "account_id": "U1234567",
    "flex_token": "plain_token_here",  # Plaintext for now
    "flex_query_id": "123456",
    "last_import_date": "2026-01-09"
  }
}
```

**Note:** Add encryption later before multi-tenant deployment.

### 3.2 Auto-Import Endpoint (Optional)

**File:** `backend/app/routers/ibkr.py`

```python
@router.post("/accounts/{account_id}/import-auto")
async def auto_import_ibkr(account_id: int, db: Session = Depends(get_db)):
    """Import using stored credentials from environment or metadata."""

    # Try account metadata first
    account = db.query(Account).filter(Account.id == account_id).first()
    ibkr_creds = account.meta_data.get("ibkr") if account.meta_data else None

    if ibkr_creds:
        flex_token = ibkr_creds["flex_token"]
        flex_query_id = ibkr_creds["flex_query_id"]
    else:
        # Fall back to environment variables
        flex_token = os.getenv("IBKR_FLEX_TOKEN")
        flex_query_id = os.getenv("IBKR_FLEX_QUERY_ID")

        if not flex_token or not flex_query_id:
            raise HTTPException(400, "No IBKR credentials configured")

    # Import
    stats = IBKRFlexImportService.import_all(db, account_id, flex_token, flex_query_id)

    # Update timestamp if using metadata
    if ibkr_creds:
        account.meta_data["ibkr"]["last_import_date"] = date.today().isoformat()
        db.commit()

    return stats
```

**Testing:**
1. Set credentials in `.env` file
2. Test import: `POST /accounts/{id}/import-auto`
3. Verify transactions imported

---

## PHASE 4: TRANSACTION-BASED HISTORICAL PERFORMANCE (5-7 days)

**Goal:** Reconstruct portfolio for any date from transaction history

### 4.1 Portfolio Reconstruction Service

**File:** `backend/app/services/portfolio_reconstruction_service.py` (NEW)

```python
class PortfolioReconstructionService:
    """Rebuild portfolio from transaction history."""

    @staticmethod
    def reconstruct_holdings(
        db: Session,
        account_id: int,
        as_of_date: date
    ) -> List[Dict]:
        """
        Reconstruct holdings for a specific date.

        Algorithm:
        1. Get all transactions up to as_of_date
        2. Replay in chronological order
        3. Track quantities using FIFO
        4. Return holdings as they existed on that date
        """
        # Get transactions up to date
        transactions = db.query(Transaction, Holding, Asset).join(
            Holding, Transaction.holding_id == Holding.id
        ).join(
            Asset, Holding.asset_id == Asset.id
        ).filter(
            Holding.account_id == account_id,
            Transaction.date <= as_of_date
        ).order_by(Transaction.date, Transaction.id).all()

        # Reconstruct holdings
        holdings_map = {}  # {asset_id: {quantity, cost_basis, lots}}

        for txn, holding, asset in transactions:
            if asset.id not in holdings_map:
                holdings_map[asset.id] = {
                    "asset": asset,
                    "quantity": Decimal("0"),
                    "cost_basis": Decimal("0"),
                    "lots": []
                }

            h = holdings_map[asset.id]

            if txn.type == "Buy":
                # Add to position
                h["quantity"] += txn.quantity
                cost = (txn.quantity * txn.price_per_unit) + txn.fees
                h["cost_basis"] += cost

                # Track lot for FIFO
                h["lots"].append({
                    "quantity": txn.quantity,
                    "remaining": txn.quantity,
                    "cost_per_unit": txn.price_per_unit,
                    "date": txn.date
                })

            elif txn.type == "Sell":
                # Reduce using FIFO
                h["quantity"] -= txn.quantity
                remaining_to_sell = txn.quantity

                for lot in h["lots"]:
                    if remaining_to_sell <= 0:
                        break

                    sold = min(lot["remaining"], remaining_to_sell)
                    lot["remaining"] -= sold
                    h["cost_basis"] -= sold * lot["cost_per_unit"]
                    remaining_to_sell -= sold

        # Return non-zero holdings
        return [
            {
                "asset_id": asset_id,
                "symbol": h["asset"].symbol,
                "quantity": h["quantity"],
                "cost_basis": h["cost_basis"]
            }
            for asset_id, h in holdings_map.items()
            if h["quantity"] > 0
        ]

    @staticmethod
    def calculate_portfolio_value(
        db: Session,
        account_id: int,
        as_of_date: date
    ) -> Dict:
        """Calculate total portfolio value for a date."""
        holdings = PortfolioReconstructionService.reconstruct_holdings(
            db, account_id, as_of_date
        )

        total_value_usd = Decimal("0")

        for holding in holdings:
            # Get historical price
            price = PriceFetcher.get_price_for_date(
                db, holding["asset_id"], as_of_date
            )

            if not price:
                continue

            asset = db.query(Asset).get(holding["asset_id"])
            value_native = holding["quantity"] * price

            # Convert to USD
            if asset.currency != "USD":
                rate = CurrencyService.get_exchange_rate(
                    db, asset.currency, "USD", as_of_date
                )
                value_usd = value_native * rate if rate else value_native
            else:
                value_usd = value_native

            total_value_usd += value_usd

        return {
            "date": as_of_date.isoformat(),
            "total_value_usd": float(total_value_usd)
        }
```

### 4.2 Update Snapshot Service

**File:** `backend/app/services/snapshot_service.py`

Add reconstruction option:
```python
@staticmethod
def _create_account_snapshot(
    db: Session,
    account: Account,
    snapshot_date: date,
    use_reconstruction: bool = True  # NEW
) -> dict | None:
    """Create snapshot using transaction reconstruction."""

    if use_reconstruction:
        # Use transaction-based reconstruction
        portfolio_value = PortfolioReconstructionService.calculate_portfolio_value(
            db, account.id, snapshot_date
        )
        total_value_usd = Decimal(str(portfolio_value["total_value_usd"]))
    else:
        # Existing method (current holdings)
        # ... existing code ...

    # Convert to ILS
    usd_to_ils_rate = CurrencyService.get_exchange_rate(
        db, "USD", "ILS", snapshot_date
    )
    total_value_ils = total_value_usd * usd_to_ils_rate if usd_to_ils_rate else total_value_usd

    # Create snapshot
    snapshot = HistoricalSnapshot(
        account_id=account.id,
        date=snapshot_date,
        total_value_usd=total_value_usd,
        total_value_ils=total_value_ils
    )
    db.add(snapshot)
    db.commit()

    return {...}
```

### 4.3 Backfill Historical Snapshots

**File:** `backend/app/services/snapshot_service.py`

```python
@staticmethod
def backfill_historical_snapshots(
    db: Session,
    account_id: int,
    start_date: date,
    end_date: date
) -> Dict:
    """Generate historical snapshots from transactions."""
    account = db.query(Account).get(account_id)
    stats = {"created": 0, "skipped": 0}

    current_date = start_date
    while current_date <= end_date:
        # Check if exists
        existing = db.query(HistoricalSnapshot).filter(
            HistoricalSnapshot.account_id == account_id,
            HistoricalSnapshot.date == current_date
        ).first()

        if existing:
            stats["skipped"] += 1
        else:
            SnapshotService._create_account_snapshot(
                db, account, current_date, use_reconstruction=True
            )
            stats["created"] += 1

        current_date += timedelta(days=1)

    return stats
```

### 4.4 Validation Endpoint

**File:** `backend/app/routers/snapshots.py`

```python
@router.get("/accounts/{account_id}/validate")
async def validate_reconstruction(
    account_id: int,
    as_of_date: date = None,
    db: Session = Depends(get_db)
):
    """Validate reconstruction accuracy."""
    if not as_of_date:
        as_of_date = date.today()

    # Get current holdings
    current = db.query(Holding, Asset).join(Asset).filter(
        Holding.account_id == account_id,
        Holding.is_active == True
    ).all()

    # Get reconstructed
    reconstructed = PortfolioReconstructionService.reconstruct_holdings(
        db, account_id, as_of_date
    )

    # Compare
    discrepancies = []
    for holding, asset in current:
        recon = next((h for h in reconstructed if h["asset_id"] == asset.id), None)

        if not recon or abs(holding.quantity - recon["quantity"]) > Decimal("0.0001"):
            discrepancies.append({
                "symbol": asset.symbol,
                "current": float(holding.quantity),
                "reconstructed": float(recon["quantity"]) if recon else 0
            })

    return {
        "is_valid": len(discrepancies) == 0,
        "discrepancies": discrepancies
    }


@router.post("/accounts/{account_id}/backfill")
async def backfill_snapshots(
    account_id: int,
    start_date: date,
    end_date: date = None,
    db: Session = Depends(get_db)
):
    """Backfill historical snapshots."""
    if not end_date:
        end_date = date.today()

    stats = SnapshotService.backfill_historical_snapshots(
        db, account_id, start_date, end_date
    )
    return stats
```

**Testing:**
1. Import complete transaction history
2. Reconstruct holdings for today
3. Validate matches current holdings (100% accuracy)
4. Reconstruct for 6 months ago
5. Backfill snapshots for past year
6. Verify FIFO accuracy

---

## PHASE 5: UPDATE AIRFLOW DAG (1 day)

**Goal:** Automate daily snapshot creation using reconstruction

**File:** `airflow/dags/daily_portfolio_pipeline.py`

Update `create_snapshots` task:
```python
@task(task_id='create_snapshots')
def create_snapshots(exchange_rate_stats: dict, asset_price_stats: dict) -> dict:
    """Create snapshots using transaction reconstruction."""
    session = SessionLocal()

    try:
        accounts = session.execute(
            text("SELECT id FROM accounts WHERE is_active = true")
        ).fetchall()

        yesterday = date.today() - timedelta(days=1)
        stats = {"created": 0, "total_value_usd": 0}

        for (account_id,) in accounts:
            try:
                snapshot = SnapshotService._create_account_snapshot(
                    session,
                    session.query(Account).get(account_id),
                    yesterday,
                    use_reconstruction=True  # Use transaction history!
                )

                if snapshot:
                    stats["created"] += 1
                    stats["total_value_usd"] += float(snapshot["value_usd"])

            except Exception as e:
                logger.error(f"Failed for account {account_id}: {e}")

        return stats
    finally:
        session.close()
```

---

## CRITICAL FILES

### New Documentation Files
- `docs/IBKR_IMPORT_PLAN.md` - This plan (moved from Claude plans, version controlled)
- `docs/ARCHITECTURE.md` - System architecture reference
- `docs/API_DOCUMENTATION.md` - API endpoints documentation
- `docs/HISTORICAL_PERFORMANCE.md` - Transaction reconstruction algorithm

### New Backend Files
- `backend/app/services/ibkr_flex_import_service.py` - Flex Query import orchestration
- `backend/app/services/portfolio_reconstruction_service.py` - Transaction-based reconstruction
- `backend/alembic/versions/add_transaction_amount.py` - Database migration for amount field

### Modified Backend Files
- `backend/app/models/transaction.py` - Add amount field for dividends
- `backend/app/services/ibkr_import_service.py` - Enhance _import_dividends()
- `backend/app/services/snapshot_service.py` - Add reconstruction support
- `backend/app/routers/ibkr.py` - Add Flex Query endpoints
- `backend/app/routers/snapshots.py` - Add validation/backfill endpoints
- `airflow/dags/daily_portfolio_pipeline.py` - Use reconstruction in snapshots

### Existing Files (Reused)
- `backend/app/services/ibkr_flex_client.py` - Already exists!
- `backend/app/services/ibkr_parser.py` - Already has extract_dividends()!

### Files to Deprecate (After Validation)
- `backend/app/services/ibkr_tws_client.py` - Remove TWS API client (after Flex Query validation)
- `backend/app/services/ibkr_tws_parser.py` - Remove TWS parser (after Flex Query validation)

---

## TESTING STRATEGY

### Phase 0: Documentation Setup
1. Create `docs/` directory
2. Copy plan to `docs/IBKR_IMPORT_PLAN.md`
3. Create placeholder documentation files
4. Verify files are readable and properly formatted

### Phase 1: Transaction Import (Flex Query API Validation)
1. Create Flex Query in IBKR portal
2. Import test account using Flex Query API
3. **CRITICAL VALIDATION**: Compare with TWS API results:
   - Verify transaction count (Flex Query should show actual count vs TWS "0")
   - Compare transaction details (dates, amounts, symbols)
   - Confirm Flex Query provides dividend data (TWS does not)
   - Validate complete historical data (TWS only shows current session)
4. Check for duplicates (should be 0)
5. Validate date range (complete history since account opening)
6. **Decision Point**: If validation passes, approve TWS API deprecation

### Phase 2: Dividend Import
1. Import account with dividend history
2. Verify dividend transactions created with correct amounts
3. Check DRIP detection accuracy (match against IBKR records)
4. Validate dividend amounts match IBKR statements

### Phase 3: Credential Storage
1. Test storing credentials in `.env` file
2. Test storing credentials in account metadata
3. Test auto-import endpoint
4. Verify credentials persist across restarts

### Phase 4: Historical Performance
1. Reconstruct today's holdings from transaction history
2. **CRITICAL**: Validate 100% match with current holdings
3. Reconstruct holdings for 6 months ago
4. Backfill 365 days of historical snapshots
5. Verify FIFO accuracy for sold positions
6. Test performance with large transaction volumes

### Phase 5: TWS API Deprecation (After Phase 1 Validation)
1. Remove references to TWS client in import service
2. Delete TWS client and parser files
3. Update frontend to remove TWS import option
4. Update documentation to reflect Flex Query as sole method
5. Test that nothing breaks after removal

---

## SUCCESS CRITERIA

- [x] Documentation structure created and version controlled
- [ ] 100% of transactions imported via Flex Query API (no more "0 transactions")
- [ ] All dividends imported with correct amounts
- [ ] DRIP detection 95%+ accurate
- [ ] **Flex Query API validated against TWS API** (proves superiority)
- [ ] TWS API code removed after validation
- [ ] Reconstruction matches current holdings (100% accuracy for today)
- [ ] Backfill of 365 days completes in <5 minutes
- [ ] Credential storage working (plaintext for now)
- [ ] Automated daily snapshots using reconstruction

---

## MIGRATION PATH

1. **Phase 0**: Create documentation structure (30 minutes) ✅
2. **Phase 1**: Deploy Flex Query import alongside TWS (no data loss, new feature)
3. **Phase 1.5**: **VALIDATE** Flex Query vs TWS (critical decision point)
4. **Phase 1.6**: Deprecate TWS API after validation passes
5. **Phase 2**: Enable dividends (adds new transactions)
6. **Phase 3**: Deploy credential storage (plaintext for now)
7. **Phase 4**: Validate reconstruction, then backfill historical snapshots
8. **Phase 5**: Enable automated daily snapshots

**Rollback:** Each phase is additive - can disable new features without data loss. If Flex Query validation fails in Phase 1.5, keep TWS API and investigate further.

---

## TIMELINE

- **Day 1**: Phase 0 (documentation setup - 30 min) ✅
- **Week 1**: Phases 1-1.6 (Flex Query import, validation, TWS deprecation)
- **Week 2**: Phases 2-3 (dividends & credential storage)
- **Week 3-4**: Phase 4 (historical performance reconstruction)
- **Week 5**: Phase 5 (Airflow automation & final testing)

**Total: 4-5 weeks**

---

## NOTES

- **TWS API Deprecation**: Only happens AFTER Flex Query validation proves it provides all required data
- **Encryption**: Deferred until pre-deployment phase (not critical for current development)
- **Multi-Tenant**: Credential isolation ready via account metadata, encryption added later
- **Cloud Deployment**: Flex Query API is HTTP-based, no local software required