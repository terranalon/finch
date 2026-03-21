import { useState, useRef, useCallback } from 'react';
import { cn } from '../../lib';
import { FilterIcon, ChevronDownIcon } from './icons';
import { useClickOutside } from '../../hooks/useClickOutside';

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

  const activeFilterCount =
    (excludedTypes.size > 0 ? 1 : 0) + (excludedAccounts.size > 0 ? 1 : 0);

  const handleTypeToggle = (type) => {
    const next = new Set(excludedTypes);
    if (next.has(type)) {
      next.delete(type);
    } else {
      next.add(type);
    }
    onTypesChange(next);
  };

  const handleAccountToggle = (accountId) => {
    const next = new Set(excludedAccounts);
    if (next.has(accountId)) {
      next.delete(accountId);
    } else {
      next.add(accountId);
    }
    onAccountsChange(next);
  };

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
          'bg-[var(--bg-elevated)] border border-[var(--border)] rounded-lg',
          'text-[var(--text-muted)] hover:bg-[var(--bg-card-hover)] transition-colors cursor-pointer'
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
        <div className="absolute top-full right-0 mt-1 w-[260px] bg-[var(--bg-card)] border border-[var(--border)] rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.4)] z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-[var(--border)]">
            <span className="text-xs font-semibold text-[var(--text-primary)]">Filters</span>
            {activeFilterCount > 0 && (
              <button
                onClick={handleClearAll}
                className="text-[11px] text-accent hover:underline cursor-pointer"
              >
                Clear all
              </button>
            )}
          </div>

          {/* Type section */}
          <div className="px-3 py-2">
            <button
              onClick={() => setTypesExpanded(!typesExpanded)}
              className="flex items-center justify-between w-full cursor-pointer"
            >
              <span className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                Type
              </span>
              <ChevronDownIcon
                className={cn(
                  'w-3 h-3 text-[var(--text-muted)] transition-transform',
                  !typesExpanded && '-rotate-90'
                )}
              />
            </button>

            {typesExpanded && (
              <div className="mt-2 flex flex-col gap-0.5">
                {types.map((type) => (
                  <label
                    key={type}
                    className="flex items-center gap-1.5 px-2 py-[5px] rounded-md text-xs text-[var(--text-secondary)] cursor-pointer hover:bg-[var(--bg-elevated)]"
                  >
                    <input
                      type="checkbox"
                      checked={!excludedTypes.has(type)}
                      onChange={() => handleTypeToggle(type)}
                      className="w-[13px] h-[13px]"
                      style={{ accentColor: 'var(--accent)' }}
                    />
                    {type}
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Accounts section */}
          {accounts.length > 0 && (
            <div className="px-3 py-2 border-t border-[var(--border)]">
              <button
                onClick={() => setAccountsExpanded(!accountsExpanded)}
                className="flex items-center justify-between w-full cursor-pointer"
              >
                <span className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wide">
                  Accounts
                </span>
                <ChevronDownIcon
                  className={cn(
                    'w-3 h-3 text-[var(--text-muted)] transition-transform',
                    !accountsExpanded && '-rotate-90'
                  )}
                />
              </button>

              {accountsExpanded && (
                <div className="mt-2 flex flex-col gap-0.5">
                  {accounts.map((account) => (
                    <label
                      key={account.id}
                      className="flex items-center gap-1.5 px-2 py-[5px] rounded-md text-xs text-[var(--text-secondary)] cursor-pointer hover:bg-[var(--bg-elevated)]"
                    >
                      <input
                        type="checkbox"
                        checked={!excludedAccounts.has(account.id)}
                        onChange={() => handleAccountToggle(account.id)}
                        className="w-[13px] h-[13px]"
                        style={{ accentColor: 'var(--accent)' }}
                      />
                      {account.name}
                    </label>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
