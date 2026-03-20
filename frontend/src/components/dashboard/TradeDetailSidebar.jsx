import { cn, formatCurrency, formatDate } from '../../lib';
import { useSlideover } from '../../hooks/useSlideover';

function CloseIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M18 6 6 18" /><path d="m6 6 12 12" />
    </svg>
  );
}

const ACTION_CONFIG = {
  Buy: { label: 'Bought', color: 'text-positive', badge: 'bg-positive/10 text-positive' },
  Sell: { label: 'Sold', color: 'text-negative', badge: 'bg-negative/10 text-negative' },
};

export function TradeDetailSidebar({ trade, isOpen, onClose, currency = 'USD' }) {
  useSlideover(isOpen, onClose);

  if (!isOpen || !trade) return null;

  const config = ACTION_CONFIG[trade.action] || { label: trade.action || '?', color: 'text-[var(--text-secondary)]', badge: 'bg-[var(--bg-tertiary)]' };
  const unit = trade.asset_class === 'Crypto' ? 'units' : 'shares';

  const rows = [
    { label: 'Date', value: trade.date ? formatDate(trade.date) : '--' },
    { label: 'Account', value: trade.account_name || '--' },
    { label: 'Quantity', value: trade.quantity != null ? `${Number(trade.quantity).toLocaleString(undefined, { maximumFractionDigits: 6 })} ${unit}` : '--' },
    { label: 'Price per Unit', value: trade.price_per_unit != null ? formatCurrency(Number(trade.price_per_unit), trade.currency || currency) : '--' },
    { label: 'Fees', value: trade.fees != null ? formatCurrency(Number(trade.fees), trade.currency || currency) : '--' },
    { label: 'Asset Class', value: trade.asset_class || '--' },
  ];

  if (trade.notes) {
    rows.push({ label: 'Notes', value: trade.notes });
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 transition-opacity"
        onClick={onClose}
      />

      <div className="fixed top-0 right-0 z-50 h-dvh w-[380px] max-w-[90vw] bg-[var(--bg-secondary)] border-l border-[var(--border-primary)] shadow-2xl flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="px-6 pt-5 pb-4 border-b border-[var(--border-primary)] flex-shrink-0">
          <div className="flex items-start justify-between mb-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={cn('px-2 py-0.5 rounded text-[11px] font-semibold', config.badge)}>
                  {trade.action}
                </span>
                <span className="text-[12px] text-[var(--text-tertiary)]">
                  {trade.asset_class}
                </span>
              </div>
              <h2 className="text-lg font-bold truncate">
                {trade.asset_name || trade.symbol}
              </h2>
              <p className="text-[12px] text-[var(--text-tertiary)]">{trade.symbol}</p>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)] transition-all cursor-pointer flex-shrink-0 ml-3"
            >
              <CloseIcon />
            </button>
          </div>

          {/* Total */}
          <div className="flex items-baseline gap-2">
            <span className={cn('text-2xl font-bold font-mono tabular-nums', config.color)}>
              {trade.total != null
                ? formatCurrency(Math.abs(Number(trade.total)), trade.currency || currency)
                : '--'}
            </span>
            <span className="text-[12px] text-[var(--text-tertiary)]">total</span>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="flex flex-col gap-0">
            {rows.map((row) => (
              <div
                key={row.label}
                className="flex items-center justify-between py-3 border-b border-[var(--border-primary)] last:border-b-0"
              >
                <span className="text-[12px] text-[var(--text-tertiary)]">{row.label}</span>
                <span className="text-[12px] font-medium text-[var(--text-primary)] text-right max-w-[60%] truncate">
                  {row.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
