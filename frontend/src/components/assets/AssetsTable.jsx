import { cn } from '../../lib';
import { AssetRow } from './AssetRow';
import { Skeleton } from '../ui';

function SortArrow({ direction }) {
  return (
    <span className="text-[var(--accent-primary)] ml-[3px] text-[10px]">
      {direction === 'asc' ? '\u25B2' : '\u25BC'}
    </span>
  );
}

function TableHeader({ label, sortKey, sortConfig, onSort, align = 'left', width, sortable = true }) {
  const isActive = sortConfig.key === sortKey;
  return (
    <th
      onClick={sortable ? () => onSort(sortKey) : undefined}
      style={width ? { width } : undefined}
      className={cn(
        'px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.5px] border-b border-[var(--border-primary)] whitespace-nowrap transition-colors',
        align === 'right' ? 'text-right' : 'text-left',
        sortable ? 'cursor-pointer select-none' : 'cursor-default',
        isActive ? 'text-[var(--text-secondary)]' : 'text-[var(--text-faint)]',
        sortable && 'hover:text-[var(--text-tertiary)]'
      )}
    >
      {label}
      {isActive && <SortArrow direction={sortConfig.direction} />}
    </th>
  );
}

function LoadingSkeleton() {
  return (
    <tbody>
      {Array.from({ length: 10 }).map((_, i) => (
        <tr key={i}>
          <td className="px-4 py-3 w-[40px]"><Skeleton className="w-4 h-4" /></td>
          <td className="px-4 py-3">
            <div className="flex items-center gap-2.5">
              <Skeleton className="w-8 h-8 rounded-lg" />
              <div>
                <Skeleton className="h-3.5 w-16 mb-1" />
                <Skeleton className="h-3 w-28" />
              </div>
            </div>
          </td>
          <td className="px-4 py-3"><Skeleton className="h-3.5 w-20 ml-auto" /></td>
          <td className="px-4 py-3">
            <div className="flex flex-col items-end gap-1">
              <Skeleton className="h-3.5 w-16" />
              <Skeleton className="h-3 w-12" />
            </div>
          </td>
          <td className="px-4 py-3"><Skeleton className="h-3.5 w-16 ml-auto" /></td>
          <td className="px-4 py-3"><Skeleton className="h-3.5 w-14 ml-auto" /></td>
          <td className="px-4 py-3"><Skeleton className="h-7 w-20 ml-auto" /></td>
        </tr>
      ))}
    </tbody>
  );
}

export function AssetsTable({
  assets,
  positionMap,
  period,
  currency,
  sortConfig,
  onSort,
  onRowClick,
  onToggleFavorite,
  loading,
  totalCount,
  favoritesCount,
}) {
  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl overflow-hidden">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <TableHeader label="" sortKey="" sortable={false} sortConfig={sortConfig} onSort={onSort} width="40px" />
            <TableHeader label="Asset" sortKey="symbol" sortConfig={sortConfig} onSort={onSort} />
            <TableHeader label="Price" sortKey="price" sortConfig={sortConfig} onSort={onSort} align="right" width="120px" />
            <TableHeader label="Change" sortKey="changePct" sortConfig={sortConfig} onSort={onSort} align="right" width="140px" />
            <TableHeader label="Mkt Cap" sortKey="marketCap" sortConfig={sortConfig} onSort={onSort} align="right" width="120px" />
            <TableHeader label="Volume" sortKey="volume" sortable={false} sortConfig={sortConfig} onSort={onSort} align="right" width="100px" />
            <TableHeader label="Trend" sortKey="" sortable={false} sortConfig={sortConfig} onSort={onSort} align="right" width="100px" />
          </tr>
        </thead>
        {loading ? (
          <LoadingSkeleton />
        ) : (
          <tbody>
            {assets.map((asset) => (
              <AssetRow
                key={asset.id}
                asset={asset}
                position={positionMap.get(asset.id)}
                period={period}
                currency={currency}
                onToggleFavorite={onToggleFavorite}
                onClick={onRowClick}
              />
            ))}
            {assets.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-16 text-center">
                  <div className="text-[var(--text-faint)]">
                    <p className="text-base font-semibold text-[var(--text-secondary)] mb-1.5">No assets found</p>
                    <p className="text-[13px]">Try adjusting your search or filters</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        )}
      </table>

      {/* Footer */}
      {!loading && assets.length > 0 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border-primary)] bg-[var(--bg-tertiary)] text-[12px] text-[var(--text-faint)]">
          <span>
            Showing {assets.length} of {totalCount} assets
          </span>
          {favoritesCount > 0 && (
            <span>{favoritesCount} favorite{favoritesCount !== 1 ? 's' : ''}</span>
          )}
        </div>
      )}
    </div>
  );
}
