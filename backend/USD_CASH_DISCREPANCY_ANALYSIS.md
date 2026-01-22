# USD Cash Balance Discrepancy Analysis

## Status: FULLY RESOLVED (2026-01-12)

The USD cash balance now matches IBKR exactly.

## Final Balance Comparison

| Source | USD Balance |
|--------|-------------|
| **Our Reconstruction** | 10,098.94 |
| **IBKR FxPosition** | 10,098.94 |
| **Difference** | 0.00 ✓ |

## USD Transaction Breakdown

| Type | Count | Amount |
|------|-------|--------|
| Deposit | 1 | +2,500.00 |
| Dividend Cash | 16 | +169.41 |
| Forex Conversion | 27 | +38,777.39 |
| Interest | 4 | +30.11 |
| Fee | 2 | -0.38 |
| Tax | 17 | -26.08 |
| Trade Settlement | 73 | -31,351.51 |
| **Total** | | **10,098.94** |

## Fixes Applied (2026-01-12)

### Fix 1: Forex Parser
**Root Cause**: The forex parser was incorrectly including ILS deposit entries as forex conversions.

**Fix**: Updated `ibkr_parser.py` to only process FxTransaction entries where `description.startswith("CASH:")`. All other entries (deposits like "Net cash activity", "CASH RECEIPTS / ELECTRONIC FUND TRANSFERS") are now skipped.

### Fix 2: Added Missing Cash Transaction Types
Added parsing and import for cash transactions that affect balance:

1. **Dividend Cash** (`ibkr_import_service.py:_import_dividend_cash`)
   - Dividends now credit both stock holdings AND cash balance

2. **Broker Interest** (`ibkr_parser.py:extract_other_cash_transactions`)
   - Type: "Broker Interest Received" → "Interest"

3. **Withholding Tax**
   - Type: "Withholding Tax" → "Tax"

4. **Other Fees**
   - Type: "Other Fees" → "Fee"

---

## Previous Analysis (Historical Reference)

### Original Data Sources

Files used for analysis:
- `data/broker_uploads/ibkr/account_7/20260112_051740_Portfolio_Tracker_Query new may24-may25.xml`
- `data/broker_uploads/ibkr/account_7/20260112_051737_Portfolio_Tracker_Query new may25-jan26.xml`

### Original Summary (Before Fix)

| Source | USD Balance |
|--------|-------------|
| **Our Reconstruction** | 12,703.28 |
| **IBKR FxPosition** | 10,098.94 |
| **Difference** | 2,604.34 |

The discrepancy existed even when calculating purely from IBKR XML data (not using our database).

---

## IBKR XML Sections Currently in Flex Query

Your Flex Query exports these sections:
- `Trades` - Stock buy/sell transactions
- `CashTransactions` - Deposits, dividends, interest, taxes, fees
- `FxTransactions` - Forex conversions
- `FxPositions` - **Final cash balances** (what IBKR reports)
- `OpenPositions` - Current stock holdings
- `Transfers` - In/out transfers (empty in your files)
- `TransactionTaxes` - Tax records

---

## Cash Flow Categories in XML

### 1. CashTransactions (Deposits/Withdrawals)

**What it is:** Direct deposits and withdrawals from bank account.

**Example from XML:**
```xml
<CashTransaction
  currency="USD"
  amount="2500"
  type="Deposits/Withdrawals"
  description="CASH RECEIPTS / ELECTRONIC FUND TRANSFERS"
  dateTime="20250522" />
```

**Status:** Imported as `Deposit` transaction.

**USD Total:** +2,500 USD

---

### 2. CashTransactions (Dividends)

**What it is:** Cash dividend payments credited to your account.

**Example from XML:**
```xml
<CashTransaction
  currency="USD"
  symbol="KMI"
  amount="8.05"
  type="Dividends"
  description="KMI CASH DIVIDEND USD 0.2875 PER SHARE (Ordinary Dividend)"
  dateTime="20240815" />
```

**Status:** Imported but linked to stock holdings (KMI asset), NOT to USD cash asset.

**USD Total:** +88.42 (from KMI, NTR, LIT, GNR, RIO, MSFT dividends)

**Issue:** Our reconstruction doesn't count these toward USD cash balance because dividends are stored with their respective stock holdings, not as cash.

---

### 3. CashTransactions (Withholding Tax)

**What it is:** Taxes withheld on dividend payments (reduces cash).

**Example from XML:**
```xml
<CashTransaction
  currency="USD"
  symbol="KMI"
  amount="-2.01"
  type="Withholding Tax"
  description="KMI CASH DIVIDEND USD 0.2875 PER SHARE - US TAX"
  dateTime="20240815" />
```

**Status:** NOT IMPORTED. These are in CashTransactions but we don't parse this type.

**USD Total:** -17.60 (various stocks)

---

### 4. CashTransactions (Broker Interest Received)

**What it is:** Interest IBKR pays you on cash balances.

**Example from XML:**
```xml
<CashTransaction
  currency="USD"
  amount="10.58"
  type="Broker Interest Received"
  description="USD CREDIT INT FOR NOV-2025"
  dateTime="20251203" />
```

**Status:** NOT IMPORTED. We don't parse this type.

**USD Total:** +30.11 (monthly interest Sep-Dec 2025)

---

### 5. CashTransactions (Other Fees)

**What it is:** Miscellaneous fees (e.g., ADR custody fees).

**Example from XML:**
```xml
<CashTransaction
  currency="USD"
  symbol="RIO"
  amount="-0.04"
  type="Other Fees"
  description="RIO CASH DIVIDEND USD 1.77 PER SHARE - FEE"
  dateTime="20240926" />
```

**Status:** NOT IMPORTED.

**USD Total:** -0.04

---

### 6. Trades (netCash)

**What it is:** Cash impact of stock purchases/sales. Includes commission and taxes.

**Example from XML:**
```xml
<Trade
  symbol="MSTR"
  quantity="-2"
  tradePrice="323.76"
  netCash="646.15"
  description="Sold 2 MSTR @ $323.76" />
```

**Formula:** `netCash = (quantity * price) + commission + taxes`

**Status:** Imported as `Trade Settlement` transaction.

**USD Total:** -31,351.51 (net of all buys/sells)

---

### 7. FxTransactions (Forex Conversions)

**What it is:** Currency conversions between ILS, USD, CAD.

**Example from XML (ILS to USD):**
```xml
<FxTransaction
  fxCurrency="ILS"
  quantity="-35000"
  proceeds="9505.97"
  code="C"
  activityDescription="CASH: 9479 USD.ILS" />
```
This means: Sold 35,000 ILS, received ~9,506 USD.

**Example from XML (USD to CAD):**
```xml
<FxTransaction
  fxCurrency="CAD"
  quantity="2057.475"
  proceeds="1502"
  code="O"
  activityDescription="CASH: -1500 USD.CAD" />
```
This means: Bought 2,057 CAD, paid 1,502 USD.

**Status:** Imported as `Forex Conversion` transactions.

**USD Totals:**
- ILS→USD conversions: +46,491.47
- USD→ILS conversions: -1,232.00
- USD→CAD conversions: -3,704.68
- **Net forex:** +41,554.79

---

## The Math Problem

### What We Calculate:

| Category | Amount (USD) |
|----------|-------------|
| Deposit | +2,500.00 |
| Trade Settlements | -31,351.51 |
| Forex ILS→USD | +46,491.47 |
| Forex USD→ILS | -1,232.00 |
| Forex USD→CAD | -3,704.68 |
| **Our Total** | **12,703.28** |

### What We DON'T Include:

| Category | Amount (USD) |
|----------|-------------|
| Dividends (stored on stocks) | +88.42 |
| Broker Interest Received | +30.11 |
| Withholding Tax | -17.60 |
| Other Fees | -0.04 |
| **Missing Total** | **+100.89** |

### The Problem:

If we ADD the missing items:
- 12,703.28 + 100.89 = **12,804.17 USD**

This is **FURTHER from** IBKR's 10,098.94, not closer!

**This means the discrepancy is NOT simply "missing transaction types."**

---

## Raw XML Calculation

I verified this by calculating directly from XML (bypassing our database):

| Source | Amount |
|--------|--------|
| CashTransactions (all USD types) | +2,673.06 |
| Trades netCash (all USD trades) | -31,351.51 |
| FxTransactions (net USD impact) | +41,554.80 |
| **XML-based Total** | **12,876.35** |
| **IBKR FxPosition says** | **10,098.94** |
| **Gap** | **2,777.41** |

The discrepancy exists in the raw XML data itself, not from our import.

---

## Possible Explanations

### 1. Missing Sections in Flex Query

IBKR has sections that might provide better reconciliation data:

| Section | Description | Currently Included |
|---------|-------------|-------------------|
| `StatementOfFunds` | Complete cash activity log | NO |
| `ChangeInNAV` | Daily NAV changes | NO |
| `CashReport` | Detailed cash breakdown | NO |
| `MTMPerformanceSummary` | Mark-to-market summary | NO |

**The `StatementOfFunds` section is the most promising** - it provides a complete, reconciled view of all cash movements.

### 2. Forex Cost Basis Adjustments

IBKR tracks forex lots with cost basis. When you convert currencies, there are unrealized/realized P&L adjustments. The `FxClosedLot` entries show these:

```xml
<FxClosedLot
  fxCurrency="CAD"
  quantity="-2034.43"
  proceeds="1481.31"
  cost="-1485.18"
  realizedPL="-3.87" />
```

This 3.87 loss isn't captured as a separate cash transaction - it's an adjustment to cost basis.

### 3. FxPosition is Reported Differently

The `FxPosition` section reports:
```xml
<FxPosition
  fxCurrency="USD"
  quantity="10098.9405965"
  costBasis="-10098.9405965" />
```

IBKR calculates this using their full internal accounting system, which may include:
- Mark-to-market adjustments
- Interest accruals not yet settled
- Pending settlements
- Adjustments from prior periods

---

## Recommendations

### Option 1: Add StatementOfFunds to Flex Query

In your IBKR Flex Query configuration:
1. Edit the query
2. Add the **Statement of Funds** section
3. Re-export and re-import

This section provides a day-by-day reconciled view of:
- Starting balance
- All cash movements (categorized)
- Ending balance

We can then verify our logic against IBKR's reconciled data.

### Option 2: Use Cash Balances from FxPositions

Instead of reconstructing cash from transactions, we could:
1. Import the `FxPosition` values for each currency
2. Use these as "snapshots" for current-day balances
3. Only reconstruct for historical dates (before first snapshot)

**Tradeoff:** Accurate current balance, but historical chart might still have drift.

### Option 3: Investigate Forex Realized P&L

The forex realized P&L entries (-3.87, -59.55, etc.) represent real cash changes that we might not be capturing correctly. Adding the `FxClosedLots` processing might help.

---

## Next Steps

### Step 1: Add These Sections to Your Flex Query

In your IBKR Flex Query configuration, add these sections:

1. **Statement of Funds** (most important)
   - Provides complete, reconciled cash movements
   - Shows daily starting balance, all activity, ending balance

2. **Change in NAV** (optional but useful)
   - Day-by-day NAV changes
   - Helps understand what IBKR includes in their calculations

3. **Cash Report** (optional)
   - Detailed cash breakdown by currency
   - Accruals and adjustments

### Step 2: Export New Files

Export two new Flex Query files:
- One covering May 2024 - May 2025
- One covering May 2025 - Jan 2026

### Step 3: Upload and Re-Analyze

1. Delete existing broker data sources through the UI
2. Upload the new files
3. I'll parse the new sections to identify:
   - Exactly how IBKR calculates the 10,098.94 balance
   - What transactions we're missing

---

## How to Edit Your Flex Query in IBKR

1. Log in to IBKR Portal → Reports → Flex Queries
2. Edit your existing query (Portfolio_Tracker_Query)
3. In the "Sections" area, add:
   - Statement of Funds (select all fields)
   - Change in NAV (select all fields)
4. Save and run the query
5. Download the XML files

---

## Questions for Investigation

If you look at your IBKR account directly:

1. **What does your current USD cash show?** Check the main portfolio page
2. **Is there a "pending" or "unsettled" amount?** Some transactions take T+1 or T+2 to settle
3. **Any margin interest or fees?** Check your activity statement for any charges we might be missing
