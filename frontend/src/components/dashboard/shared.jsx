import { cn } from '../../lib';

/**
 * Sort direction indicator for table column headers.
 */
export function SortArrow({ dir }) {
  return <span className="text-[10px] ml-0.5 opacity-60">{dir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
}

/**
 * Toggleable star icon for marking assets as favorites.
 */
export function FavoriteStar({ isFavorite, onClick }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      className={cn(
        'text-sm leading-none transition-all cursor-pointer select-none hover:scale-110',
        isFavorite ? 'text-[#F59E0B]' : 'text-[var(--text-faint)] hover:text-[#F59E0B]'
      )}
    >
      {isFavorite ? '\u2605' : '\u2606'}
    </button>
  );
}

/**
 * Build the minimal asset object expected by onAssetClick handlers.
 * Used by TopHoldingsTable, AssetExplorerCard, and MoversCard to avoid
 * duplicating the same field selection.
 */
export function toAssetClickPayload(item) {
  return {
    id: item.asset_id,
    symbol: item.symbol,
    name: item.name,
    asset_class: item.asset_class,
    current_price: item.current_price,
    day_change_pct: item.day_change_pct,
    currency: item.currency,
  };
}
