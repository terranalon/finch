import { cn } from '../../lib';

/**
 * Skeleton loading placeholder
 *
 * @param {object} props
 * @param {string} props.className - Additional CSS classes
 */
export function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-slate-200 dark:bg-slate-700',
        className
      )}
      {...props}
    />
  );
}

/**
 * Skeleton for text content
 */
export function SkeletonText({ lines = 1, className, ...props }) {
  return (
    <div className={cn('space-y-2', className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            'h-4',
            i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  );
}

/**
 * Skeleton for card content
 */
export function SkeletonCard({ className, ...props }) {
  return (
    <div
      className={cn(
        'bg-[var(--bg-secondary)] rounded-lg p-6 border border-[var(--border-primary)]',
        className
      )}
      {...props}
    >
      <Skeleton className="h-4 w-1/3 mb-4" />
      <Skeleton className="h-8 w-1/2 mb-2" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

/**
 * Skeleton for table rows
 */
export function SkeletonTableRow({ columns = 5, className, ...props }) {
  return (
    <tr className={cn('', className)} {...props}>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

/**
 * Skeleton for the Overview page hero section
 */
export function SkeletonHero({ className, ...props }) {
  return (
    <div className={cn('text-center py-8', className)} {...props}>
      <Skeleton className="h-10 w-48 mx-auto mb-3" />
      <Skeleton className="h-6 w-36 mx-auto mb-4" />
      <Skeleton className="h-12 w-64 mx-auto" />
    </div>
  );
}

/**
 * Skeleton for chart area
 */
export function SkeletonChart({ className, ...props }) {
  return (
    <div
      className={cn('rounded-lg bg-[var(--bg-tertiary)] p-4', className)}
      {...props}
    >
      <div className="flex justify-between mb-4">
        <Skeleton className="h-4 w-24" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-10" />
          <Skeleton className="h-6 w-10" />
          <Skeleton className="h-6 w-10" />
        </div>
      </div>
      <Skeleton className="h-48 w-full" />
    </div>
  );
}

export default Skeleton;