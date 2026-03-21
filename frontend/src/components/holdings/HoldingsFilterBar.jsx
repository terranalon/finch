import { useState, useRef, useCallback } from 'react';
import { cn } from '../../lib';
import { useClickOutside } from '../../hooks/useClickOutside';

function SearchIcon() {
  return (
    <svg className="w-[15px] h-[15px]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
  );
}

function FunnelIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
      <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
    </svg>
  );
}

function ChevronIcon({ collapsed }) {
  return (
    <svg
      className={cn('w-3 h-3 transition-transform', collapsed && '-rotate-90')}
      fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

function FilterSection({ label, collapsed, onToggle, items, selectedValues, onItemToggle, getLabel, getValue }) {
  return (
    <div className={cn('mb-3.5 last:mb-0')}>
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-[10px] font-semibold text-[var(--text-faint)] uppercase tracking-wide py-1 cursor-pointer select-none hover:text-[var(--text-tertiary)] transition-colors"
      >
        {label}
        <ChevronIcon collapsed={collapsed} />
      </button>
      {!collapsed && (
        <div className="mt-1.5">
          {items.map((item) => {
            const value = getValue(item);
            const isSelected = selectedValues.includes(value);
            return (
              <button
                key={value}
                onClick={() => onItemToggle(value)}
                className="flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
              >
                <span
                  className={cn(
                    'w-4 h-4 rounded flex items-center justify-center flex-shrink-0 border-[1.5px] transition-colors',
                    isSelected
                      ? 'bg-accent border-accent'
                      : 'border-[var(--border-primary)]'
                  )}
                >
                  {isSelected && <CheckIcon />}
                </span>
                {getLabel(item)}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function HoldingsFilterBar({
  searchQuery,
  onSearchChange,
  accounts,
  selectedAccounts,
  onAccountsChange,
  assetClasses,
  selectedClasses,
  onClassesChange,
  sectors,
  selectedSectors,
  onSectorsChange,
  onClearAll,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState({
    accounts: true,
    classes: true,
    sectors: true,
  });

  const panelRef = useRef(null);
  useClickOutside(panelRef, () => setIsOpen(false));

  const toggleSection = useCallback((section) => {
    setCollapsedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const toggleItem = useCallback((list, value, onChange) => {
    const next = list.includes(value)
      ? list.filter((v) => v !== value)
      : [...list, value];
    onChange(next);
  }, []);

  // Count active filter groups (a group is active when not all items are selected)
  const activeGroups =
    (selectedAccounts.length < accounts.length ? 1 : 0) +
    (selectedClasses.length < assetClasses.length ? 1 : 0) +
    (selectedSectors.length < sectors.length ? 1 : 0);

  return (
    <div className="flex items-center gap-3">
      {/* Search */}
      <div className="relative flex-1 max-w-md">
        <div className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)]">
          <SearchIcon />
        </div>
        <input
          type="text"
          placeholder="Search by symbol or name..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className={cn(
            'w-full pl-9 pr-4 py-2 rounded-lg text-[13px]',
            'bg-[var(--bg-tertiary)] border border-[var(--border-primary)]',
            'text-[var(--text-primary)] placeholder:text-[var(--text-faint)]',
            'focus:outline-none focus:border-accent transition-colors'
          )}
        />
      </div>

      {/* Filter icon + panel */}
      <div className="relative" ref={panelRef}>
        <button
          title="Filters"
          onClick={() => setIsOpen((prev) => !prev)}
          className={cn(
            'relative w-9 h-9 flex items-center justify-center rounded-lg border transition-colors cursor-pointer',
            isOpen || activeGroups > 0
              ? 'bg-accent/10 border-accent text-accent'
              : 'bg-[var(--bg-tertiary)] border-[var(--border-primary)] text-[var(--text-tertiary)] hover:border-[var(--text-faint)] hover:text-[var(--text-secondary)]'
          )}
        >
          <FunnelIcon />
          {activeGroups > 0 && (
            <span
              data-testid="filter-badge"
              className="absolute -top-1 -right-1 min-w-[16px] h-4 bg-accent text-white rounded-full text-[9px] font-bold flex items-center justify-center px-1"
            >
              {activeGroups}
            </span>
          )}
        </button>

        {isOpen && (
          <div className="absolute top-[calc(100%+6px)] right-0 z-50 w-[280px] bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-3.5">
              <span className="text-sm font-semibold text-[var(--text-primary)]">Filters</span>
              <button
                onClick={() => { onClearAll(); }}
                className="text-[11px] text-accent hover:underline cursor-pointer"
              >
                Clear all
              </button>
            </div>

            <FilterSection
              label="Accounts"
              collapsed={collapsedSections.accounts}
              onToggle={() => toggleSection('accounts')}
              items={accounts}
              selectedValues={selectedAccounts}
              onItemToggle={(v) => toggleItem(selectedAccounts, v, onAccountsChange)}
              getLabel={(a) => a.name}
              getValue={(a) => a.id}
            />

            <FilterSection
              label="Asset Class"
              collapsed={collapsedSections.classes}
              onToggle={() => toggleSection('classes')}
              items={assetClasses}
              selectedValues={selectedClasses}
              onItemToggle={(v) => toggleItem(selectedClasses, v, onClassesChange)}
              getLabel={(c) => c}
              getValue={(c) => c}
            />

            <FilterSection
              label="Sector"
              collapsed={collapsedSections.sectors}
              onToggle={() => toggleSection('sectors')}
              items={sectors}
              selectedValues={selectedSectors}
              onItemToggle={(v) => toggleItem(selectedSectors, v, onSectorsChange)}
              getLabel={(c) => c}
              getValue={(c) => c}
            />
          </div>
        )}
      </div>
    </div>
  );
}
