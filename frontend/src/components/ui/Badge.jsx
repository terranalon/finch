import { cn } from '../../lib';

const variants = {
  default: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  buy: 'bg-positive-bg text-positive dark:bg-positive-bg-dark dark:text-positive-dark',
  sell: 'bg-negative-bg text-negative dark:bg-negative-bg-dark dark:text-negative-dark',
  positive: 'bg-positive-bg text-positive dark:bg-positive-bg-dark dark:text-positive-dark',
  negative: 'bg-negative-bg text-negative dark:bg-negative-bg-dark dark:text-negative-dark',
  accent: 'bg-accent-light text-accent dark:bg-[var(--accent-light)] dark:text-accent-400',
  dividend: 'bg-accent-light text-accent dark:bg-[var(--accent-light)] dark:text-accent-400',
  forex: 'bg-purple-100 text-purple-600 dark:bg-purple-900 dark:text-purple-300',
  deposit: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900 dark:text-emerald-300',
  withdrawal: 'bg-amber-100 text-amber-600 dark:bg-amber-900 dark:text-amber-300',
};

/**
 * Badge component for status indicators and labels.
 *
 * @param {object} props
 * @param {'default'|'buy'|'sell'|'positive'|'negative'|'accent'|'dividend'|'forex'|'deposit'|'withdrawal'} props.variant - Badge style variant
 * @param {string} props.className - Additional CSS classes
 */
export function Badge({
  children,
  variant = 'default',
  className,
  ...props
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

/**
 * Transaction type badge with automatic variant selection
 */
export function TransactionBadge({ type, className, ...props }) {
  const typeToVariant = {
    BUY: 'buy',
    SELL: 'sell',
    DIV: 'dividend',
    DIVIDEND: 'dividend',
    FX: 'forex',
    FOREX: 'forex',
    DEP: 'deposit',
    DEPOSIT: 'deposit',
    WD: 'withdrawal',
    WITHDRAWAL: 'withdrawal',
  };

  const variant = typeToVariant[type?.toUpperCase()] || 'default';
  const displayText = type?.toUpperCase() || 'UNKNOWN';

  return (
    <Badge variant={variant} className={className} {...props}>
      {displayText}
    </Badge>
  );
}

export default Badge;