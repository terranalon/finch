import { describe, it, expect } from 'vitest';
import { mergeRecentActivity } from '../assetActivity';

const trades = [
  { id: 1, date: '2026-01-10', type: 'buy', quantity: 10, price: 100, amount: -1000, account_name: 'IBKR' },
  { id: 2, date: '2026-03-05', type: 'sell', quantity: 4, price: 120, amount: 480, account_name: 'IBKR' },
];
const dividends = [
  { id: 9, date: '2026-02-01', type: 'DIVIDEND', amount: 12.5, account_name: 'IBKR' },
];

describe('mergeRecentActivity', () => {
  it('merges trades and dividends into one list sorted by date descending', () => {
    const rows = mergeRecentActivity(trades, dividends, 5);
    expect(rows.map((r) => r.date)).toEqual(['2026-03-05', '2026-02-01', '2026-01-10']);
  });

  it('maps trade fields: type, quantity, price, total=amount, account', () => {
    const [sell] = mergeRecentActivity(trades, dividends, 5);
    expect(sell).toMatchObject({
      type: 'sell', quantity: 4, price: 120, total: 480, account: 'IBKR',
    });
  });

  it('maps dividends with null quantity/price and total=amount', () => {
    const rows = mergeRecentActivity([], dividends, 5);
    expect(rows[0]).toMatchObject({
      type: 'DIVIDEND', quantity: null, price: null, total: 12.5, account: 'IBKR',
    });
  });

  it('slices to the limit', () => {
    expect(mergeRecentActivity(trades, dividends, 1)).toHaveLength(1);
  });

  it('gives every row a stable unique id', () => {
    const rows = mergeRecentActivity(trades, dividends, 5);
    const ids = rows.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('defaults dividend type to DIVIDEND when missing', () => {
    const rows = mergeRecentActivity([], [{ id: 3, date: '2026-02-01', amount: 5, account_name: 'IBKR' }], 5);
    expect(rows[0].type).toBe('DIVIDEND');
  });
});
