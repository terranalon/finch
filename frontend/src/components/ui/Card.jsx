import { cn } from '../../lib';

/**
 * Card component for containing content sections.
 *
 * @param {object} props
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.hoverable - Whether to show hover effect
 * @param {boolean} props.clickable - Whether the card is clickable
 */
export function Card({
  children,
  className,
  hoverable = false,
  clickable = false,
  ...props
}) {
  return (
    <div
      className={cn(
        'bg-[var(--bg-secondary)] rounded-lg p-6 border border-[var(--border-primary)]',
        hoverable && 'hover:bg-[var(--bg-tertiary)] transition-colors',
        clickable && 'cursor-pointer',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Card header section
 */
export function CardHeader({ children, className, ...props }) {
  return (
    <div
      className={cn('mb-4', className)}
      {...props}
    >
      {children}
    </div>
  );
}

/**
 * Card title
 */
export function CardTitle({ children, className, ...props }) {
  return (
    <h3
      className={cn('text-lg font-semibold text-[var(--text-primary)] text-balance', className)}
      {...props}
    >
      {children}
    </h3>
  );
}

/**
 * Card description
 */
export function CardDescription({ children, className, ...props }) {
  return (
    <p
      className={cn('text-sm text-[var(--text-secondary)] text-pretty mt-1', className)}
      {...props}
    >
      {children}
    </p>
  );
}

/**
 * Card content section
 */
export function CardContent({ children, className, ...props }) {
  return (
    <div className={cn('', className)} {...props}>
      {children}
    </div>
  );
}

/**
 * Card footer section
 */
export function CardFooter({ children, className, ...props }) {
  return (
    <div
      className={cn('mt-4 pt-4 border-t border-[var(--border-primary)]', className)}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card;
