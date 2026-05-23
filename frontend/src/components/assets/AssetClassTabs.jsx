import { cn } from '../../lib';

const ASSET_CLASSES = ['All', 'Crypto', 'Stock', 'ETF', 'Cash'];
const ASSET_CLASS_LABELS = {
  All: 'All',
  Crypto: 'Crypto',
  Stock: 'Stocks',
  ETF: 'ETFs',
  Cash: 'Forex',
};

export function AssetClassTabs({ assets, activeTab, onTabChange }) {
  const counts = { All: assets.length };
  for (const asset of assets) {
    counts[asset.asset_class] = (counts[asset.asset_class] || 0) + 1;
  }

  const visibleTabs = ASSET_CLASSES.filter((cls) => cls === 'All' || counts[cls] > 0);

  return (
    <div className="flex items-center gap-0.5 p-[3px] bg-[var(--bg-tertiary)] rounded-[10px] mb-4 overflow-x-auto">
      {visibleTabs.map((cls) => (
        <button
          key={cls}
          onClick={() => onTabChange(cls)}
          className={cn(
            'flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[13px] font-medium cursor-pointer',
            'transition-all whitespace-nowrap border-none',
            activeTab === cls
              ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] font-semibold shadow-sm'
              : 'bg-transparent text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
          )}
        >
          {ASSET_CLASS_LABELS[cls] || cls}
          <span
            className={cn(
              'text-[11px] px-[7px] py-px rounded-[10px] font-semibold tabular-nums',
              activeTab === cls
                ? 'bg-[var(--accent-primary)]/15 text-[var(--accent-primary)]'
                : 'bg-[var(--bg-secondary)] text-[var(--text-faint)]'
            )}
          >
            {counts[cls]}
          </span>
        </button>
      ))}
    </div>
  );
}
