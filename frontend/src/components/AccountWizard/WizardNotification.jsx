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
          ? 'bg-negative-bg dark:bg-negative-bg-dark/90 border border-negative-light dark:border-negative-dark/30'
          : 'bg-positive-light dark:bg-positive-bg-dark/90 border border-positive-light dark:border-positive-dark/30'
      )}
    >
      <div
        className={cn(
          'p-1.5 rounded-full flex-shrink-0',
          isError
            ? 'bg-negative-light dark:bg-negative-bg-dark/50'
            : 'bg-positive-light dark:bg-positive-bg-dark/50'
        )}
      >
        {isError ? (
          <XIcon className="size-4 text-negative dark:text-negative-dark" />
        ) : (
          <CheckIcon className="size-4 text-positive dark:text-positive-dark" />
        )}
      </div>
      <p
        className={cn(
          'flex-1 text-sm font-medium',
          isError
            ? 'text-negative dark:text-red-200'
            : 'text-positive dark:text-emerald-200'
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
            ? 'hover:bg-negative-light dark:hover:bg-negative-bg-dark'
            : 'hover:bg-positive-light dark:hover:bg-positive-bg-dark'
        )}
        aria-label="Dismiss notification"
      >
        <XIcon
          className={cn(
            'size-4',
            isError
              ? 'text-negative dark:text-negative-dark'
              : 'text-positive dark:text-positive-dark'
          )}
        />
      </button>
    </div>
  );
}
