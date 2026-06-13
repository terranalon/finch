/**
 * Merge trade and dividend rows into a single recent-activity list,
 * sorted by date descending and sliced to `limit`.
 *
 * Trades and dividends share a normalized shape:
 *   { id, date, type, quantity, price, total, account }
 * Dividends have null quantity/price.
 */
export function mergeRecentActivity(trades = [], dividends = [], limit = 5) {
  const tradeRows = trades.map((t) => ({
    id: `trade-${t.id}`,
    date: t.date,
    type: t.type,
    quantity: t.quantity,
    price: t.price,
    total: t.amount,
    account: t.account_name,
  }));

  const dividendRows = dividends.map((d) => ({
    id: `div-${d.id}`,
    date: d.date,
    type: d.type || 'DIVIDEND',
    quantity: null,
    price: null,
    total: d.amount,
    account: d.account_name,
  }));

  return [...tradeRows, ...dividendRows]
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, limit);
}
