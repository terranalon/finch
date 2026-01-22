import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Combines clsx and tailwind-merge for conditional class names
 * that properly handle Tailwind CSS class conflicts.
 *
 * @param  {...any} inputs - Class values to merge
 * @returns {string} - Merged class string
 *
 * @example
 * cn('px-4 py-2', 'px-6') // => 'py-2 px-6'
 * cn('text-red-500', isError && 'text-green-500') // conditional
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}