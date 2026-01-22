import { cn } from '../../lib';

/**
 * Finch logo icon - A geometric bird silhouette representing
 * the portfolio tracker's "view from above" philosophy.
 */
export function FinchIcon({ className, ...props }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="currentColor"
      className={cn('size-6', className)}
      {...props}
    >
      {/* Bird in flight - abstract geometric design */}
      <path
        d="M4 16c0-1.5 1-2.5 2-3l8-5c1-.5 2-.5 3 0l8 5c1 .5 2 1.5 2 3s-1 2.5-2 3l-3 2v3c0 1-1 2-2 2h-8c-1 0-2-1-2-2v-3l-3-2c-1-.5-2-1.5-2-3z"
        fillRule="evenodd"
      />
      {/* Wing detail */}
      <path
        d="M16 9l6 4-6 3-6-3 6-4z"
        fill="currentColor"
        opacity="0.3"
      />
    </svg>
  );
}

export default FinchIcon;
