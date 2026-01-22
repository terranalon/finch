import { cn } from '../../lib';

/**
 * Page container with consistent max-width and padding.
 *
 * @param {object} props
 * @param {string} props.className - Additional CSS classes
 * @param {'default'|'narrow'|'wide'} props.width - Container width preset
 */
export function PageContainer({
  children,
  className,
  width = 'default',
  ...props
}) {
  const widthClasses = {
    narrow: 'max-w-4xl',
    default: 'max-w-6xl',
    wide: 'max-w-7xl',
  };

  return (
    <main
      className={cn(
        'mx-auto px-4 sm:px-6 lg:px-8 py-6',
        widthClasses[width],
        className
      )}
      {...props}
    >
      {children}
    </main>
  );
}

/**
 * Page header section with title and optional actions
 */
export function PageHeader({ title, description, children, className, ...props }) {
  return (
    <div className={cn('mb-6', className)} {...props}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)] text-balance">
            {title}
          </h1>
          {description && (
            <p className="mt-1 text-sm text-[var(--text-secondary)] text-pretty">
              {description}
            </p>
          )}
        </div>
        {children && <div className="flex items-center gap-3">{children}</div>}
      </div>
    </div>
  );
}

export default PageContainer;
