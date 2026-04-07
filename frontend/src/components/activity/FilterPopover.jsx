import { useState, useRef, useCallback } from 'react';
import { cn } from '../../lib';
import { FilterIcon, ChevronDownIcon } from './icons';
import { useClickOutside } from '../../hooks/useClickOutside';

function toggleSetItem(set, item) {
  const next = new Set(set);
  if (next.has(item)) {
    next.delete(item);
  } else {
    next.add(item);
  }
  return next;
}

function FilterSection({ title, expanded, onToggle, className, children }) {
  return (
    <div className={cn('px-3 py-2', className)}>
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full cursor-pointer"
      >
        <span className="text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wide">
          {title}
        </span>
        <ChevronDownIcon
          className={cn(
            'w-3 h-3 text-[var(--text-tertiary)] transition-transform',
            !expanded && '-rotate-90'
          )}
        />
      </button>

      {expanded && (
        <div className="mt-2 flex flex-col gap-1">
          {children}
        </div>
      )}
    </div>
  );
}

function FilterCheckbox({ checked, onChange, label }) {
  return (
    <label className="flex items-center gap-1.5 px-2 py-[5px] rounded-md text-xs text-[var(--text-secondary)] cursor-pointer hover:bg-[var(--bg-tertiary)]">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="w-[13px] h-[13px]"
        style={{ accentColor: 'var(--accent-primary)' }}
      />
      {label}
    </label>
  );
}

export function FilterPopover({
  types,
  excludedTypes,
  onTypesChange,
  accounts,
  excludedAccounts,
  onAccountsChange,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [typesExpanded, setTypesExpanded] = useState(false);
  const [accountsExpanded, setAccountsExpanded] = useState(false);
  const popoverRef = useRef(null);

  useClickOutside(popoverRef, useCallback(() => setIsOpen(false), []));

  const hasTypeFilters = excludedTypes.size > 0;
  const hasAccountFilters = excludedAccounts.size > 0;
  const activeFilterCount = (hasTypeFilters ? 1 : 0) + (hasAccountFilters ? 1 : 0);

  const handleClearAll = () => {
    onTypesChange(new Set());
    onAccountsChange(new Set());
  };

  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-[34px] h-[34px] flex items-center justify-center',
          'bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg',
          'text-[var(--text-tertiary)] hover:border-[var(--text-faint)] hover:text-[var(--text-secondary)] transition-colors cursor-pointer'
        )}
      >
        <FilterIcon className="w-4 h-4" />
      </button>

      {activeFilterCount > 0 && (
        <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-accent text-white text-[9px] font-bold flex items-center justify-center">
          {activeFilterCount}
        </span>
      )}

      {isOpen && (
        <div className="absolute top-full right-0 mt-1 w-[260px] bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.4)] z-50">
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--border-primary)]">
            <span className="text-xs font-semibold text-[var(--text-secondary)]">Filters</span>
            {activeFilterCount > 0 && (
              <button
                onClick={handleClearAll}
                className="text-[11px] text-accent hover:underline cursor-pointer"
              >
                Clear all
              </button>
            )}
          </div>

          <FilterSection
            title="Type"
            expanded={typesExpanded}
            onToggle={() => setTypesExpanded(!typesExpanded)}
          >
            {types.map((type) => (
              <FilterCheckbox
                key={type}
                checked={!excludedTypes.has(type)}
                onChange={() => onTypesChange(toggleSetItem(excludedTypes, type))}
                label={type}
              />
            ))}
          </FilterSection>

          {accounts.length > 0 && (
            <FilterSection
              title="Accounts"
              expanded={accountsExpanded}
              onToggle={() => setAccountsExpanded(!accountsExpanded)}
              className="border-t border-[var(--border-primary)]"
            >
              {accounts.map((account) => (
                <FilterCheckbox
                  key={account.id}
                  checked={!excludedAccounts.has(account.id)}
                  onChange={() => onAccountsChange(toggleSetItem(excludedAccounts, account.id))}
                  label={account.name}
                />
              ))}
            </FilterSection>
          )}
        </div>
      )}
    </div>
  );
}
