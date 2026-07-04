import { Link } from 'react-router-dom';
import { cn, formatCurrency, formatDate, formatNumber } from '../../lib';
import { Card } from '../ui/Card';
import { TransactionBadge } from '../ui/Badge';
import { NoTransactionsEmpty } from '../ui/EmptyState';

// Buy reduces cash (red, "-"), sell/dividend add cash (green/accent, "+").
function amountColor(type) {
  const t = (type || '').toLowerCase();
  if (t === 'buy') return 'text-negative';
  if (t === 'sell') return 'text-positive';
  return 'text-accent';
}

function amountSign(type) {
  return (type || '').toLowerCase() === 'buy' ? '-' : '+';
}

export default function RecentActivity({ activity, activityCount, currency }) {
  return (
    <Card>
      <div className="mb-3 text-[13px] font-semibold text-[var(--text-primary)]">Recent Activity</div>

      {activity.length === 0 ? (
        <NoTransactionsEmpty />
      ) : (
        <>
          <div className="flex flex-col">
            {activity.map((tx) => {
              const meta =
                tx.quantity != null
                  ? `${formatNumber(tx.quantity)} @ ${formatCurrency(tx.price, currency)} · ${tx.account || '--'} · ${formatDate(tx.date)}`
                  : `${tx.account || '--'} · ${formatDate(tx.date)}`;
              const total = Number(tx.total);
              const hasTotal = Number.isFinite(total);
              return (
                <div
                  key={tx.id}
                  className="flex items-center gap-3 py-2.5 border-b border-[var(--border-primary)] last:border-b-0"
                >
                  <TransactionBadge type={tx.type} />
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] font-medium text-[var(--text-primary)] capitalize truncate">
                      {(tx.type || '').toLowerCase()}
                    </div>
                    <div className="text-[10px] text-[var(--text-tertiary)] truncate">{meta}</div>
                  </div>
                  <div
                    className={cn(
                      'text-[12px] font-mono tabular-nums font-medium flex-shrink-0',
                      hasTotal && amountColor(tx.type),
                    )}
                  >
                    {hasTotal ? (
                      <>
                        {amountSign(tx.type)}
                        {formatCurrency(Math.abs(total), currency)}
                      </>
                    ) : (
                      '--'
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {activityCount > activity.length && (
            <Link
              to="/activity"
              className="mt-3 inline-flex items-center gap-1 text-[12px] text-accent hover:text-accent-hover font-medium"
            >
              View all {activityCount} transactions <span aria-hidden>&rarr;</span>
            </Link>
          )}
        </>
      )}
    </Card>
  );
}
