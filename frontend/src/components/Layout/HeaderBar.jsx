import { cn, formatCurrency } from '../../lib';
import { useTheme, useCurrency, usePortfolio } from '../../contexts';
import { ThemeToggle } from '../ui';
import { PortfolioSelector } from './PortfolioSelector';
import { SettingsDropdown } from './SettingsDropdown';

function SearchIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

export function HeaderBar() {
  const { isDark, toggleTheme } = useTheme();
  const { selectedPortfolio } = usePortfolio();
  const { currency } = useCurrency();

  return (
    <header className="h-[52px] min-h-[52px] bg-[var(--bg-primary)] border-b border-[var(--border-primary)] flex items-center justify-between px-5 gap-3">
      {/* Left: search */}
      <div className={cn(
        'flex items-center gap-2 px-3.5 py-1.5 flex-1 max-w-[480px]',
        'bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg',
        'text-xs text-[var(--text-tertiary)] cursor-pointer',
        'hover:border-[var(--text-faint)] transition-colors'
      )}>
        <SearchIcon className="w-3.5 h-3.5 flex-shrink-0" />
        <span className="whitespace-nowrap">Search assets, accounts...</span>
        <kbd className="ml-auto text-[10px] px-1.5 py-0.5 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded text-[var(--text-faint)] font-sans">
          Cmd+K
        </kbd>
      </div>

      {/* Right: controls */}
      <div className="flex items-center gap-2">
        {selectedPortfolio?.total_value != null && (
          <span className="text-[13px] font-bold font-mono tabular-nums px-3 py-1.5 bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg">
            {formatCurrency(selectedPortfolio.total_value, currency)}
          </span>
        )}
        <PortfolioSelector />
        <ThemeToggle isDark={isDark} onToggle={toggleTheme} />
        <SettingsDropdown />
      </div>
    </header>
  );
}
