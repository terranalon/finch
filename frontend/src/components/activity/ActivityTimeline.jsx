import { DateGroupHeader } from './DateGroupHeader';
import { TransactionCard } from '../transactions';
import { CalendarIcon } from './icons';

export function ActivityTimeline({ groupedTransactions, currency, onTransactionClick }) {
  const dateKeys = Object.keys(groupedTransactions).sort((a, b) => new Date(b) - new Date(a));

  if (dateKeys.length === 0) {
    return (
      <div className="text-center py-12">
        <CalendarIcon className="w-12 h-12 mx-auto text-[var(--text-muted)] mb-4" />
        <h3 className="text-lg font-medium text-[var(--text-primary)]">No transactions found</h3>
        <p className="text-[var(--text-secondary)] mt-1">
          Try adjusting your filters to see more results.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {dateKeys.map((date) => (
        <div key={date}>
          <DateGroupHeader date={date} />
          <div className="ml-4 pl-4 border-l-2 border-[var(--border)] flex flex-col gap-[10px]">
            {groupedTransactions[date].map((tx) => (
              <TransactionCard
                key={tx.id}
                tx={tx}
                variant="detailed"
                currency={currency}
                onClick={() => onTransactionClick(tx)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
