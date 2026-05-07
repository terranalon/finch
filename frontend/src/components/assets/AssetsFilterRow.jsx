import { cn } from '../../lib';
import { MagnifyingGlassIcon, StarOutlineIcon, StarFilledIcon } from './icons';

const TIME_PERIODS = [
  { id: '1d', label: '1D' },
  { id: '1w', label: '1W' },
  { id: '1m', label: '1M' },
];

export function AssetsFilterRow({
  searchQuery,
  onSearchChange,
  selectedPeriod,
  onPeriodChange,
  showFavoritesOnly,
  onFavoritesToggle,
}) {
  return (
    <div className="flex items-center gap-2.5 mb-4 flex-wrap">
      {/* Search */}
      <div className="relative w-[240px] flex-shrink-0">
        <MagnifyingGlassIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 w-[15px] h-[15px] text-[var(--text-faint)] pointer-events-none" />
        <input
          type="text"
          placeholder="Search assets..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full py-2 pl-[34px] pr-3 bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
        />
      </div>

      <div className="flex-1" />

      {/* Time period toggle */}
      <div className="flex items-center gap-0.5 p-[3px] bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg">
        {TIME_PERIODS.map((p) => (
          <button
            key={p.id}
            onClick={() => onPeriodChange(p.id)}
            className={cn(
              'px-3 py-[5px] border-none rounded-md text-xs font-semibold cursor-pointer transition-all',
              selectedPeriod === p.id
                ? 'bg-[var(--accent-primary)] text-white'
                : 'bg-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Favorites toggle */}
      <button
        onClick={onFavoritesToggle}
        className={cn(
          'flex items-center gap-1.5 px-3.5 py-[6px] rounded-lg text-[13px] font-medium cursor-pointer transition-all border',
          showFavoritesOnly
            ? 'bg-[var(--amber)]/12 border-[var(--amber)] text-[var(--amber)]'
            : 'bg-[var(--bg-tertiary)] border-[var(--border-primary)] text-[var(--text-tertiary)] hover:border-[var(--text-faint)] hover:text-[var(--text-secondary)]'
        )}
      >
        {showFavoritesOnly ? (
          <StarFilledIcon className="w-[15px] h-[15px]" />
        ) : (
          <StarOutlineIcon className="w-[15px] h-[15px]" />
        )}
        Favorites
      </button>
    </div>
  );
}
