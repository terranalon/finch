# Broker Integration Guidelines

**CRITICAL:** Follow these rules when adding new broker integrations. Learned from Kraken integration bugs where balances were incorrect.

## 1. Dual-Entry Accounting (MANDATORY)
Every trade MUST create TWO transactions:
1. **Asset Transaction**: Buy/Sell on the asset holding (crypto/stock)
2. **Trade Settlement**: Cash impact on the cash holding (USD/ILS)

```python
# For a BUY order:
# 1. Asset transaction: quantity = +crypto_amount (positive)
# 2. Trade Settlement: amount = -fiat_amount (negative, deducts from cash)

# For a SELL order:
# 1. Asset transaction: quantity = -crypto_amount (negative)
# 2. Trade Settlement: amount = +fiat_amount (positive, adds to cash)
```

Without Trade Settlements, purchases won't deduct from cash balance, causing inflated USD balances.

## 2. Fee Handling (ALL fee types)

| Transaction Type | Fee Rule |
|-----------------|----------|
| **Buy (fiat->crypto)** | `quantity = crypto_received - crypto_fee` (net crypto you actually receive) |
| **Sell (crypto->fiat)** | `quantity = abs(crypto_sold) + crypto_fee` (total crypto leaving account) |
| **Crypto-to-Crypto** | Sell side: `quantity = abs(amount) + fee`; Buy side: `quantity = amount - fee` |
| **Staking Rewards** | `quantity = amount - fee` (net reward after fee) |
| **Withdrawal** | Use signed amounts: `net_amount = amount - fee` (fee increases outflow magnitude) |
| **Deposit** | `net_amount = amount - fee` (fees reduce what you receive) |

### Broker-Specific Notes

**Kraken**: Charges fees in crypto, not fiat. The CSV ledger uses signed amounts (negative for outflows).
- Buy: Fee deducted from crypto received (`quantity = crypto_amount - crypto_fee`)
- Sell: Fee added to crypto sold (`quantity = abs(crypto_amount) + crypto_fee`)
- Withdrawal: Already negative, so `amount - fee` correctly increases outflow magnitude

## 3. Decimal Precision
- **Transaction.amount**: `Numeric(15, 2)` - only 2 decimal places (for fiat values)
- **Transaction.quantity**: `Numeric(20, 8)` - 8 decimal places (for crypto/shares)
- **ALWAYS** use `quantity` field for crypto, never `amount` for position calculations

```python
deposit_qty = txn.quantity if txn.quantity is not None else txn.amount
```

## 4. Asset Normalization
Create a `<broker>_constants.py` file with symbol mappings:
```python
# Kraken: XXBT -> BTC, XETH -> ETH, ZUSD -> USD
# Staked variants: SOL.S -> SOL, ETH.S -> ETH (map to base asset)
```

## 5. Price Provider Mappings
Add new crypto symbols to `coingecko_client.py:SYMBOL_TO_ID`:
```python
SYMBOL_TO_ID = {
    "BTC": "bitcoin",
    "BABY": "babylon",  # NOT "baby-doge-coin"!
    # Verify correct ID at https://api.coingecko.com/api/v3/coins/list
}
```

## 6. Batch Price Fetching
Use batch API calls to avoid rate limits:
```python
# Good: Single API call for all crypto
crypto_prices = client.get_current_prices(["BTC", "ETH", "SOL"], "usd")

# Bad: Individual calls (rate limited)
for symbol in symbols:
    price = client.get_current_price(symbol, "usd")  # Will hit 429 errors
```

## 7. Testing Checklist
Before marking a broker integration complete:
- [ ] Clear all transactions for test account
- [ ] Re-sync from broker API
- [ ] Compare each asset balance with API response (must match exactly for crypto, <$0.01 for fiat)
- [ ] Verify USD/cash balance reflects all trade settlements
- [ ] Test re-sync (should skip duplicates)
- [ ] Verify historical data imports correctly

## 8. Common Bugs to Avoid

| Bug | Symptom | Fix |
|-----|---------|-----|
| Missing Trade Settlements | Cash balance inflated | Add dual-entry accounting |
| Fees not subtracted | Quantities slightly off | Include fees in all transaction types |
| Using `amount` for crypto | Precision loss (0.37 vs 0.37132823) | Use `quantity` field |
| Wrong CoinGecko ID | No price data | Verify at coingecko.com/api/v3/coins/list |
| Individual price calls | 429 rate limit errors | Use batch `get_current_prices()` |

## 9. Reference Implementations
- **IBKR** (`ibkr_import_service.py`): Best example of dual-entry accounting
- **Meitav** (`meitav_parser.py`): Good Israeli broker reference
- **Kraken** (`kraken_client.py`): Crypto exchange with all fee types handled
