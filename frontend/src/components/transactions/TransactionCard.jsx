/**
 * TransactionCard - Unified transaction display component
 *
 * Supports two variants:
 * - "detailed": Full card for Activity timeline (shows all fields, borders, shadows)
 * - "compact": Single row for Account tab lists (minimal, inline layout)
 */

import { cn, formatCurrency, hasConversion } from '../../lib';

// ============================================
// ICONS
// ============================================

function ArrowDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5 12 21m0 0-7.5-7.5M12 21V3" />
    </svg>
  );
}

function ArrowUpIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
    </svg>
  );
}

function BanknotesIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
    </svg>
  );
}

function ArrowsRightLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  );
}

function PlusCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function MinusCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function ReceiptPercentIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m9 14.25 6-6m4.5-3.493V21.75l-3.75-1.5-3.75 1.5-3.75-1.5-3.75 1.5V4.757c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0c1.1.128 1.907 1.077 1.907 2.185ZM9.75 9h.008v.008H9.75V9Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm4.125 4.5h.008v.008h-.008V13.5Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
    </svg>
  );
}

// ============================================
// STYLE CONFIGURATION
// ============================================

const STYLE_CONFIG = {
  trade: {
    BUY: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/40',
      text: 'text-emerald-600 dark:text-emerald-400',
      icon: ArrowDownIcon,
      sign: '-',
    },
    SELL: {
      bg: 'bg-red-50 dark:bg-red-950/40',
      text: 'text-red-600 dark:text-red-400',
      icon: ArrowUpIcon,
      sign: '+',
    },
  },
  dividend: {
    bg: 'bg-teal-50 dark:bg-teal-950/40',
    text: 'text-teal-600 dark:text-teal-400',
    icon: BanknotesIcon,
    sign: '+',
  },
  forex: {
    bg: 'bg-violet-50 dark:bg-violet-950/40',
    text: 'text-violet-600 dark:text-violet-400',
    icon: ArrowsRightLeftIcon,
  },
  cash: {
    DEPOSIT: {
      bg: 'bg-blue-50 dark:bg-blue-950/40',
      text: 'text-blue-600 dark:text-blue-400',
      icon: PlusCircleIcon,
      sign: '+',
    },
    WITHDRAWAL: {
      bg: 'bg-amber-50 dark:bg-amber-950/40',
      text: 'text-amber-600 dark:text-amber-400',
      icon: MinusCircleIcon,
      sign: '-',
    },
    FEE: {
      bg: 'bg-red-50 dark:bg-red-950/40',
      text: 'text-red-600 dark:text-red-400',
      icon: ReceiptPercentIcon,
      sign: '-',
    },
    INTEREST: {
      bg: 'bg-green-50 dark:bg-green-950/40',
      text: 'text-green-600 dark:text-green-400',
      icon: BanknotesIcon,
      sign: '+',
    },
    TRANSFER: {
      bg: 'bg-slate-50 dark:bg-slate-950/40',
      text: 'text-slate-600 dark:text-slate-400',
      icon: ArrowsRightLeftIcon,
      sign: '',
    },
  },
};

// ============================================
// HELPER FUNCTIONS
// ============================================

function getStyle(tx) {
  switch (tx.type) {
    case 'trade':
      return STYLE_CONFIG.trade[tx.side] || STYLE_CONFIG.trade.BUY;
    case 'dividend':
      return STYLE_CONFIG.dividend;
    case 'forex':
      return STYLE_CONFIG.forex;
    case 'cash':
      return STYLE_CONFIG.cash[tx.activity_type] || STYLE_CONFIG.cash.DEPOSIT;
    default:
      return STYLE_CONFIG.cash.DEPOSIT;
  }
}

function formatDateShort(dateStr) {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatRate(rate) {
  return parseFloat(rate.toFixed(4)).toString();
}

const CURRENCY_SYMBOLS = {
  USD: '$',
  EUR: '\u20AC',
  GBP: '\u00A3',
  ILS: '\u20AA',
  JPY: '\u00A5',
  CHF: 'CHF ',
};

function getCurrencySymbol(code) {
  return CURRENCY_SYMBOLS[code] || code + ' ';
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

function getCompactDescription(tx) {
  switch (tx.type) {
    case 'trade':
      return `${capitalize(tx.side)} ${tx.quantity} ${tx.symbol}`;
    case 'dividend':
      return `${tx.symbol} dividend`;
    case 'forex':
      return `${tx.from_currency} \u2192 ${tx.to_currency}`;
    case 'cash':
      return capitalize(tx.activity_type);
    default:
      return 'Transaction';
  }
}

function getCompactAmount(tx, currency, style) {
  const converted = hasConversion(tx);
  switch (tx.type) {
    case 'trade': {
      const amt = converted ? tx.original_amount : tx.total;
      const cur = converted ? tx.original_currency : currency;
      return `${style.sign}${formatCurrency(Math.abs(amt), cur)}`;
    }
    case 'dividend': {
      const amt = converted ? tx.original_amount : tx.amount;
      const cur = converted ? tx.original_currency : currency;
      return `+${formatCurrency(Math.abs(amt), cur)}`;
    }
    case 'forex':
      return `${Math.abs(tx.to_amount).toLocaleString()} ${tx.to_currency}`;
    case 'cash': {
      const amt = converted ? tx.original_amount : tx.amount;
      const cur = converted ? tx.original_currency : currency;
      return `${style.sign}${formatCurrency(Math.abs(amt), cur)}`;
    }
    default:
      return '';
  }
}

// ============================================
// DETAILED VARIANT HELPERS
// ============================================

function renderDetailedTradeContent(tx, style, currency) {
  return (
    <>
      <div className="flex items-center gap-2">
        <span className={cn('text-[10px] font-bold uppercase tracking-wide px-1.5 py-px rounded', style.bg, style.text)}>
          {tx.side}
        </span>
        <span className="text-[13px] font-semibold text-[var(--text-primary)]">{tx.symbol}</span>
      </div>
      <p className="text-[12px] text-[var(--text-muted,var(--text-secondary))] mt-1 font-mono tabular-nums">
        {tx.quantity} × {formatCurrency(tx.price, currency)}
      </p>
      {tx.fee > 0 && (
        <p className="text-[12px] text-[var(--text-muted,var(--text-tertiary))] mt-1">
          Fee: {formatCurrency(tx.fee, currency)}
        </p>
      )}
    </>
  );
}

function renderDetailedDividendContent(tx, style) {
  return (
    <>
      <div className="flex items-center gap-2">
        <span className={cn('text-[10px] font-bold uppercase tracking-wide px-1.5 py-px rounded', style.bg, style.text)}>
          DIVIDEND
        </span>
        <span className="text-[13px] font-semibold text-[var(--text-primary)]">{tx.symbol}</span>
      </div>
      <p className="text-[12px] text-[var(--text-muted,var(--text-secondary))] mt-1">{tx.description}</p>
    </>
  );
}

function renderDetailedForexContent(tx, style) {
  return (
    <>
      <div className="flex items-center gap-2">
        <span className={cn('text-[10px] font-bold uppercase tracking-wide px-1.5 py-px rounded', style.bg, style.text)}>
          FX
        </span>
        <span className="text-[13px] font-semibold text-[var(--text-primary)]">
          {tx.from_currency} {'\u2192'} {tx.to_currency}
        </span>
      </div>
      <p className="text-[12px] text-[var(--text-muted,var(--text-tertiary))] mt-1">
        Rate: {formatRate(tx.exchange_rate)}
        {tx.fee > 0 && (
          <span> · Fee: {getCurrencySymbol(tx.from_currency)}{tx.fee}</span>
        )}
      </p>
    </>
  );
}

function renderDetailedCashContent(tx, style, currency) {
  return (
    <>
      <div className="flex items-center gap-2">
        <span className={cn('text-[10px] font-bold uppercase tracking-wide px-1.5 py-px rounded', style.bg, style.text)}>
          {tx.cash_type || tx.activity_type}
        </span>
      </div>
      <p className="text-[12px] text-[var(--text-muted,var(--text-secondary))] mt-1">{tx.description}</p>
      {tx.fee > 0 && (
        <p className="text-[12px] text-[var(--text-muted,var(--text-tertiary))] mt-1">
          Fee: {formatCurrency(tx.fee, currency)}
        </p>
      )}
    </>
  );
}

function renderDetailedContent(tx, style, currency) {
  switch (tx.type) {
    case 'trade':
      return renderDetailedTradeContent(tx, style, currency);
    case 'dividend':
      return renderDetailedDividendContent(tx, style);
    case 'forex':
      return renderDetailedForexContent(tx, style);
    case 'cash':
      return renderDetailedCashContent(tx, style, currency);
    default:
      return null;
  }
}

function ConvertedAmountLine({ amount, currency }) {
  return (
    <p className="text-xs text-[var(--text-tertiary)] font-mono mt-0.5">
      {formatCurrency(Math.abs(amount), currency)}
    </p>
  );
}

function renderDetailedAmount(tx, style, currency) {
  const converted = hasConversion(tx);

  switch (tx.type) {
    case 'trade': {
      const primaryAmount = converted ? tx.original_amount : tx.total;
      const primaryCurrency = converted ? tx.original_currency : currency;
      return (
        <>
          <p className={cn('text-[15px] font-bold font-mono tabular-nums', style.text)}>
            {style.sign}{formatCurrency(Math.abs(primaryAmount), primaryCurrency)}
          </p>
          {converted && <ConvertedAmountLine amount={tx.total} currency={currency} />}
        </>
      );
    }
    case 'dividend': {
      const primaryAmount = converted ? tx.original_amount : tx.amount;
      const primaryCurrency = converted ? tx.original_currency : currency;
      return (
        <>
          <p className={cn('text-[15px] font-bold font-mono tabular-nums', style.text)}>
            +{formatCurrency(Math.abs(primaryAmount), primaryCurrency)}
          </p>
          {converted && <ConvertedAmountLine amount={tx.amount} currency={currency} />}
        </>
      );
    }
    case 'forex':
      return (
        <>
          <p className={cn('text-[15px] font-bold font-mono tabular-nums', style.text)}>
            {getCurrencySymbol(tx.to_currency)}{tx.to_amount.toLocaleString()}
          </p>
          <p className="text-xs text-[var(--text-tertiary)] font-mono mt-0.5">
            from {getCurrencySymbol(tx.from_currency)}{tx.from_amount.toLocaleString()}
          </p>
        </>
      );
    case 'cash': {
      const primaryAmount = converted ? tx.original_amount : tx.amount;
      const primaryCurrency = converted ? tx.original_currency : currency;
      return (
        <>
          <p className={cn('text-[15px] font-bold font-mono tabular-nums', style.text)}>
            {style.sign}{formatCurrency(Math.abs(primaryAmount), primaryCurrency)}
          </p>
          {converted && <ConvertedAmountLine amount={tx.amount} currency={currency} />}
        </>
      );
    }
    default:
      return null;
  }
}

// ============================================
// MAIN COMPONENT
// ============================================

/**
 * Unified TransactionCard component with detailed and compact variants.
 *
 * @param {Object} props
 * @param {Object} props.tx - Transformed transaction object
 * @param {'detailed'|'compact'} props.variant - Display variant (default: 'detailed')
 * @param {string} props.currency - Display currency for formatting
 * @param {Function} props.onClick - Optional click handler for detail panel
 */
export function TransactionCard({ tx, variant = 'detailed', currency, onClick }) {
  const style = getStyle(tx);
  const Icon = style.icon;
  const txCurrency = tx.currency || currency || 'USD';
  const isConverted = hasConversion(tx);

  // Compact variant - single row
  if (variant === 'compact') {
    return (
      <div
        onClick={onClick}
        className={cn(
          'flex items-center justify-between py-3',
          onClick && 'cursor-pointer hover:bg-[var(--bg-tertiary)] -mx-2 px-2 rounded-lg transition-colors'
        )}
      >
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg', style.bg)}>
            <Icon className={cn('size-4', style.text)} />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">
              {getCompactDescription(tx)}
            </p>
            <p className="text-xs text-[var(--text-tertiary)]">{formatDateShort(tx.date)}</p>
          </div>
        </div>
        <div className="text-right">
          <p className={cn('text-[15px] font-bold font-mono tabular-nums', style.text)}>
            {getCompactAmount(tx, txCurrency, style)}
          </p>
          {isConverted && (
            <p className="text-xs text-[var(--text-tertiary)] font-mono">
              {formatCurrency(Math.abs(tx.type === 'trade' ? tx.total : tx.amount), txCurrency)}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Detailed variant - full card
  return (
    <div
      onClick={onClick}
      className={cn(
        'flex items-start justify-between px-4 py-3.5 gap-3',
        'bg-[var(--bg-card)] border border-[var(--border-subtle,var(--border-primary))] rounded-lg',
        onClick && 'hover:bg-[var(--bg-card-hover,var(--bg-tertiary))] transition-colors cursor-pointer'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn('w-9 h-9 rounded-[10px] flex items-center justify-center flex-shrink-0', style.bg)}>
          <Icon className={cn('w-[18px] h-[18px]', style.text)} />
        </div>
        <div>
          {renderDetailedContent(tx, style, txCurrency)}
          {tx.account_name && (
            <p className="text-[11px] text-[var(--text-faint,var(--text-tertiary))] mt-0.5">{tx.account_name}</p>
          )}
        </div>
      </div>
      <div className="text-right flex-shrink-0 flex flex-col justify-center self-stretch">
        {renderDetailedAmount(tx, style, txCurrency)}
      </div>
    </div>
  );
}

export default TransactionCard;
