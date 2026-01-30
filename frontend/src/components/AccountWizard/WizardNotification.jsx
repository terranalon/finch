import { useEffect } from 'react';

import { cn } from '../../lib/index.js';
import { CheckIcon, XIcon } from './icons.jsx';

/**
 * Notification component for the wizard.
 * Displays success or error messages with auto-dismiss.
 */
export function WizardNotification({ message, type = 'error', onDismiss, autoDismiss = 5000 }) {
  useEffect(() => {
    if (autoDismiss && message) {
      const timer = setTimeout(() => {
        onDismiss?.();
      }, autoDismiss);
      return () => clearTimeout(timer);
    }
  }, [message, autoDismiss, onDismiss]);

  if (!message) return null;

  const isError = type === 'error';

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        'fixed bottom-6 left-1/2 -translate-x-1/2 z-50',
        'flex items-center gap-3 px-5 py-4 rounded-xl shadow-lg',
        'max-w-md w-[calc(100%-2rem)]',
        'animate-in slide-in-from-bottom-4 fade-in duration-300',
        isError
          ? 'bg-red-50 dark:bg-red-950/90 border border-red-200 dark:border-red-800'
          : 'bg-emerald-50 dark:bg-emerald-950/90 border border-emerald-200 dark:border-emerald-800'
      )}
    >
      <div
        className={cn(
          'p-1.5 rounded-full flex-shrink-0',
          isError
            ? 'bg-red-100 dark:bg-red-900/50'
            : 'bg-emerald-100 dark:bg-emerald-900/50'
        )}
      >
        {isError ? (
          <XIcon className="size-4 text-red-600 dark:text-red-400" />
        ) : (
          <CheckIcon className="size-4 text-emerald-600 dark:text-emerald-400" />
        )}
      </div>
      <p
        className={cn(
          'flex-1 text-sm font-medium',
          isError
            ? 'text-red-800 dark:text-red-200'
            : 'text-emerald-800 dark:text-emerald-200'
        )}
      >
        {message}
      </p>
      <button
        type="button"
        onClick={onDismiss}
        className={cn(
          'p-1 rounded-full transition-colors cursor-pointer flex-shrink-0',
          isError
            ? 'hover:bg-red-200 dark:hover:bg-red-800'
            : 'hover:bg-emerald-200 dark:hover:bg-emerald-800'
        )}
        aria-label="Dismiss notification"
      >
        <XIcon
          className={cn(
            'size-4',
            isError
              ? 'text-red-600 dark:text-red-400'
              : 'text-emerald-600 dark:text-emerald-400'
          )}
        />
      </button>
    </div>
  );
}
