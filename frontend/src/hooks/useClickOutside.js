import { useEffect } from 'react';

/**
 * Close a dropdown/popover when clicking outside the referenced element.
 *
 * @param {React.RefObject} ref - Ref to the container element
 * @param {Function} onClickOutside - Callback invoked on outside click
 */
export function useClickOutside(ref, onClickOutside) {
  useEffect(() => {
    function handler(event) {
      if (ref.current && !ref.current.contains(event.target)) {
        onClickOutside();
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [ref, onClickOutside]);
}
