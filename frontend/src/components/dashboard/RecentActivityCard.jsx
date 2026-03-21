import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatCurrency, formatDate } from '../../lib';
import api from '../../lib/api';
import { Skeleton } from '../ui';

const ACTION_CONFIG = {
  Buy: { label: 'Bought', color: 'text-positive', icon: '+' },
  Sell: { label: 'Sold', color: 'text-negative', icon: '-' },
};

export function RecentActivityCard({ onTradeClick }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api('/transactions/trades?limit=5')
      .then((resp) => resp.json())
      .then((res) => {
        if (!cancelled) setTransactions(res.items || res || []);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="card">
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
            const config = ACTION_CONFIG[tx.action] || { label: tx.action || '?', color: 'text-[var(--text-secondary)]', icon: '?' };
            const unit = tx.asset_class === 'Crypto' ? 'units' : 'shares';
            return (
              <div
                key={tx.id}
                onClick={() => onTradeClick?.(tx)}
                className={cn(
                  'flex items-center gap-3 py-2.5 border-b border-[var(--border-primary)] last:border-b-0',
                  onTradeClick && 'cursor-pointer hover:bg-[var(--bg-tertiary)] rounded -mx-1 px-1 transition-colors'
                )}
              >
                <div className={cn(
                  'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0',
                  'bg-[var(--bg-tertiary)]', config.color
                )}>
                  {config.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-medium text-[var(--text-primary)] truncate">
                    {config.label} {tx.symbol || ''}
                  </div>
                  <div className="text-[10px] text-[var(--text-tertiary)]">
                    {tx.account_name || ''} {tx.date ? `\u00B7 ${formatDate(tx.date)}` : ''}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  {tx.quantity != null && (
                    <div className={cn('text-[12px] font-mono tabular-nums font-medium', config.color)}>
                      {Number(tx.quantity).toLocaleString(undefined, { maximumFractionDigits: 4 })} {unit}
                    </div>
                  )}
                  {tx.total != null && (
                    <div className="text-[10px] font-mono tabular-nums text-[var(--text-tertiary)]">
                      {formatCurrency(Math.abs(Number(tx.total)), tx.currency || 'USD')}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
