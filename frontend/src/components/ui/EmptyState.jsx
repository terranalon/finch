import { cn } from '../../lib';
import { Button } from './Button';

/**
 * Empty state component with icon, title, description, and action.
 *
 * @param {object} props
 * @param {React.ReactNode} props.icon - Icon to display
 * @param {string} props.title - Empty state title
 * @param {string} props.description - Description of what will appear
 * @param {string} props.actionLabel - Primary action button label
 * @param {function} props.onAction - Primary action callback
 * @param {string} props.className - Additional CSS classes
 */
export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  secondaryActionLabel,
  onSecondaryAction,
  className,
  children,
  ...props
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
      {...props}
    >
      {icon && (
        <div className="mb-4 text-[var(--text-tertiary)]">
          {typeof icon === 'function' ? icon({ className: 'size-12' }) : icon}
        </div>
      )}
      {title && (
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2 text-balance">
          {title}
        </h3>
      )}
      {description && (
        <p className="text-sm text-[var(--text-secondary)] mb-6 max-w-md text-pretty">
          {description}
        </p>
      )}
      {(actionLabel || children) && (
        <div className="flex flex-col sm:flex-row gap-3">
          {actionLabel && onAction && (
            <Button onClick={onAction} variant="primary">
              {actionLabel}
            </Button>
          )}
          {secondaryActionLabel && onSecondaryAction && (
            <Button onClick={onSecondaryAction} variant="secondary">
              {secondaryActionLabel}
            </Button>
          )}
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * Pre-configured empty states for common scenarios
 */
export function NoHoldingsEmpty({ onAddHolding }) {
  return (
    <EmptyState
      icon={(props) => (
        <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
      )}
      title="No holdings yet"
      description="Start tracking your portfolio by adding your first holding. Import from your broker or add positions manually."
      actionLabel="Add your first holding"
      onAction={onAddHolding}
    />
  );
}

export function NoAccountsEmpty({ onAddAccount }) {
  return (
    <EmptyState
      icon={(props) => (
        <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      )}
      title="No accounts connected"
      description="Add your brokerage accounts to start tracking your portfolio. You can import data from popular brokers or add accounts manually."
      actionLabel="Connect an account"
      onAction={onAddAccount}
    />
  );
}

export function NoTransactionsEmpty({ onAddTransaction }) {
  return (
    <EmptyState
      icon={(props) => (
        <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      )}
      title="No transactions yet"
      description="Your transaction history will appear here once you import data or add trades manually."
      actionLabel="Import transactions"
      onAction={onAddTransaction}
    />
  );
}

export function NoDataEmpty({ title = "No data available", description }) {
  return (
    <EmptyState
      icon={(props) => (
        <svg {...props} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      )}
      title={title}
      description={description || "Data will appear here once available."}
    />
  );
}

export default EmptyState;