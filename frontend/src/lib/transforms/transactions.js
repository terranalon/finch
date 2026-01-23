/**
 * Transaction Transform Functions
 *
 * Shared transforms for normalizing API responses to unified transaction format.
 * Used by Activity page and AccountDetail page for consistent data display.
 */

const CASH_ACTIVITY_TYPE_MAP = {
  Deposit: 'DEPOSIT',
  Withdrawal: 'WITHDRAWAL',
  Fee: 'FEE',
  Transfer: 'TRANSFER',
  'Custody Fee': 'FEE',
  Interest: 'INTEREST',
};

/**
 * Transform API trade response to unified format.
 */
export function transformTrade(trade) {
  return {
    id: `trade-${trade.id}`,
    type: 'trade',
    date: trade.date,
    symbol: trade.symbol,
    name: trade.asset_name,
    side: trade.action === 'Buy' ? 'BUY' : 'SELL',
    quantity: parseFloat(trade.quantity),
    price: parseFloat(trade.price_per_unit),
    total: parseFloat(trade.total),
    fee: parseFloat(trade.fees || 0),
    currency: trade.currency || 'USD',
    account_name: trade.account_name,
    notes: trade.notes,
  };
}

/**
 * Transform API dividend response to unified format.
 */
export function transformDividend(dividend) {
  const description = dividend.type === 'Dividend' ? 'Dividend payment' : dividend.type;

  return {
    id: `dividend-${dividend.id}`,
    type: 'dividend',
    date: dividend.date,
    symbol: dividend.symbol,
    name: dividend.asset_name,
    amount: parseFloat(dividend.amount),
    currency: dividend.currency || 'USD',
    description,
    account_name: dividend.account_name,
    notes: dividend.notes,
  };
}

/**
 * Transform API forex response to unified format.
 */
export function transformForex(forex) {
  return {
    id: `forex-${forex.id}`,
    type: 'forex',
    date: forex.date,
    from_currency: forex.from_currency,
    to_currency: forex.to_currency,
    from_amount: parseFloat(forex.from_amount),
    to_amount: parseFloat(forex.to_amount),
    exchange_rate: parseFloat(forex.exchange_rate),
    fee: parseFloat(forex.fees || 0),
    account_name: forex.account_name,
    notes: forex.notes,
  };
}

/**
 * Transform API cash response to unified format.
 */
export function transformCash(cash) {
  const activityType = CASH_ACTIVITY_TYPE_MAP[cash.type] || cash.type.toUpperCase();

  return {
    id: `cash-${cash.id}`,
    type: 'cash',
    date: cash.date,
    activity_type: activityType,
    cash_type: cash.type,
    amount: parseFloat(cash.amount),
    fee: parseFloat(cash.fees || 0),
    currency: cash.currency || 'USD',
    description: cash.notes ? `${cash.type} - ${cash.notes}` : cash.type,
    account_name: cash.account_name,
    notes: cash.notes,
  };
}
