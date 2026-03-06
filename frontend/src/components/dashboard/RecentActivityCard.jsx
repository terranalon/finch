import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatCurrency, formatDate } from '../../lib';
import api from '../../lib/api';
import { Skeleton } from '../ui';

const TYPE_CONFIG = {
  BUY: { label: 'Bought', color: 'text-positive', icon: '+' },
  SELL: { label: 'Sold', color: 'text-negative', icon: '-' },
  DIVIDEND: { label: 'Dividend', color: 'text-accent', icon: '$' },
  DEPOSIT: { label: 'Deposit', color: 'text-positive', icon: '+' },
  WITHDRAWAL: { label: 'Withdrawal', color: 'text-negative', icon: '-' },
  TRANSFER_IN: { label: 'Transfer In', color: 'text-positive', icon: '+' },
  TRANSFER_OUT: { label: 'Transfer Out', color: 'text-negative', icon: '-' },
};

export function RecentActivityCard() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api('/api/transactions/trades?limit=5')
      .then((res) => {
        if (!cancelled) setTransactions(res.items || res || []);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="card flex-1 min-h-0 overflow-y-auto">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-semibold">Recent Activity</span>
        <Link to="/activity" className="text-[12px] text-accent hover:text-accent-hover font-medium">
          All activity &rarr;
        </Link>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full rounded" />)}
        </div>
      ) : transactions.length === 0 ? (
        <div className="text-center py-6 text-[var(--text-tertiary)] text-xs">No recent activity</div>
      ) : (
        <div className="flex flex-col">
          {transactions.map((tx) => {
            const config = TYPE_CONFIG[tx.type] || { label: tx.type, color: 'text-[var(--text-secondary)]', icon: '?' };
            return (
              <div
                key={tx.id}
                className="flex items-center gap-3 py-2.5 border-b border-[var(--border-primary)] last:border-b-0"
              >
                <div className={cn(
                  'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                  'bg-[var(--bg-tertiary)]', config.color
                )}>
                  {config.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-medium text-[var(--text-primary)] truncate">
                    {config.label} {tx.symbol || tx.asset_symbol || ''}
                  </div>
                  <div className="text-[10px] text-[var(--text-tertiary)]">
                    {tx.account_name || ''} {tx.date ? `\u00B7 ${formatDate(tx.date)}` : ''}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className={cn('text-[12px] font-mono tabular-nums font-medium', config.color)}>
                    {tx.total_amount != null
                      ? formatCurrency(Math.abs(tx.total_amount), tx.currency || 'USD')
                      : tx.quantity != null
                        ? `${tx.quantity} shares`
                        : '--'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
