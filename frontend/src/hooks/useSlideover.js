import { useEffect, useCallback } from 'react';

/**
 * Shared behavior for slide-over panels (sidebars):
 * - Locks body scroll while open
 * - Closes on Escape key press
 *
 * @param {boolean} isOpen - Whether the panel is visible
 * @param {Function} onClose - Called when panel should close
 */
export function useSlideover(isOpen, onClose) {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') onClose?.();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);
}
