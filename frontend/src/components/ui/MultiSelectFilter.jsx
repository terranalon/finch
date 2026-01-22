/**
 * MultiSelectFilter - Dropdown with checkboxes for multi-selection
 *
 * Used across all pages (Holdings, Activity, Accounts, Insights) for consistent
 * filter behavior. All options are selected by default.
 *
 * @param {string} label - Display label (e.g., "Accounts", "Classes")
 * @param {Array} options - Array of options to select from
 * @param {Array} selected - Array of currently selected values
 * @param {Function} onChange - Callback when selection changes
 * @param {Function} getOptionLabel - Function to get display label from option
 * @param {Function} getOptionValue - Function to get value from option
 */

import { useState, useRef, useEffect } from 'react';
import { cn } from '../../lib';

// Inline icons to avoid circular dependencies
function ChevronDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function CheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

export function MultiSelectFilter({
  label,
  options,
  selected,
  onChange,
  getOptionLabel = (opt) => opt,
  getOptionValue = (opt) => opt,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const allSelected = selected.length === options.length;
  const noneSelected = selected.length === 0;

  const toggleOption = (value) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  const toggleAll = () => {
    if (allSelected) {
      onChange([]);
    } else {
      onChange(options.map(getOptionValue));
    }
  };

  // Display text
  let displayText = label;
  if (noneSelected) {
    displayText = `No ${label}`;
  } else if (!allSelected) {
    displayText = `${selected.length} ${label}`;
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-4 py-2.5 rounded-lg cursor-pointer',
          'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
          'text-[var(--text-primary)] text-sm',
          'hover:bg-[var(--bg-tertiary)] transition-colors',
          !allSelected && !noneSelected && 'border-accent'
        )}
      >
        <span>{displayText}</span>
        <ChevronDownIcon className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 min-w-[180px] bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg z-50 py-1">
          {/* Select All */}
          <button
            onClick={toggleAll}
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <span
              className={cn(
                'w-4 h-4 rounded border flex items-center justify-center',
                allSelected ? 'bg-accent border-accent' : 'border-[var(--border-secondary)]'
              )}
            >
              {allSelected && <CheckIcon className="w-3 h-3 text-white" />}
            </span>
            <span className="font-medium text-[var(--text-primary)]">Select All</span>
          </button>

          <div className="h-px bg-[var(--border-primary)] my-1" />

          {/* Options */}
          {options.map((option) => {
            const value = getOptionValue(option);
            const optionLabel = getOptionLabel(option);
            const isSelected = selected.includes(value);

            return (
              <button
                key={value}
                onClick={() => toggleOption(value)}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-left hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
              >
                <span
                  className={cn(
                    'w-4 h-4 rounded border flex items-center justify-center',
                    isSelected ? 'bg-accent border-accent' : 'border-[var(--border-secondary)]'
                  )}
                >
                  {isSelected && <CheckIcon className="w-3 h-3 text-white" />}
                </span>
                <span className="text-[var(--text-primary)]">{optionLabel}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}