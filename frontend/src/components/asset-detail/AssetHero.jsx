import { formatCurrency, formatDate, getChangeColor, getChangeIndicator, cn } from '../../lib';
import { Badge } from '../ui/Badge';

const ASSET_CLASS_VARIANTS = {
  Stock: 'default',
  ETF: 'accent',
  Crypto: 'accent',
};

export default function AssetHero({ asset, onToggleFavorite, onRefreshPrice }) {
  const currentPrice = asset.daily_metrics?.close ?? asset.last_fetched_price;
  const open = asset.daily_metrics?.open;
  const change = open != null ? currentPrice - open : null;
  const changePercent = open != null && open !== 0 ? (change / open) * 100 : null;

  const colorClass = change != null ? getChangeColor(change) : '';
  const indicator = change != null ? getChangeIndicator(change) : '';

  const badgeVariant = ASSET_CLASS_VARIANTS[asset.asset_class] || 'default';

  return (
    <div className="mb-6">
      {/* Row 1: Identity + favorite star */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-mono text-2xl font-bold text-[var(--text-primary)] truncate">
            {asset.symbol}
          </span>
          <span className="text-[var(--text-secondary)]">&middot;</span>
          <span className="text-lg text-[var(--text-secondary)] truncate">{asset.name}</span>
        </div>
        <button
          onClick={onToggleFavorite}
          aria-label={asset.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
          className="flex-shrink-0 p-1.5 rounded-full hover:bg-[var(--bg-tertiary)] transition-colors text-[var(--text-secondary)] hover:text-amber-400"
        >
          {asset.is_favorite ? (
            <svg className="size-5 fill-amber-400 text-amber-400" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          ) : (
            <svg className="size-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
            </svg>
          )}
        </button>
      </div>

      {/* Row 2: Meta badges */}
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <Badge variant={badgeVariant}>{asset.asset_class}</Badge>
        {asset.exchange && (
          <span className="text-xs text-[var(--text-secondary)] font-medium">{asset.exchange}</span>
        )}
        <span className="text-xs text-[var(--text-secondary)]">{asset.currency}</span>
      </div>

      {/* Row 3: Price + change */}
      <div className="flex items-baseline gap-3 mt-3">
        <span className="font-mono text-4xl font-bold text-[var(--text-primary)]">
          {formatCurrency(currentPrice, asset.currency)}
        </span>
        {change != null && indicator && (
          <span className={cn('text-base font-medium', colorClass)}>
            {indicator} {formatCurrency(Math.abs(change), asset.currency)} ({changePercent?.toFixed(2) ?? '0.00'}%)
          </span>
        )}
      </div>

      {/* Row 4: Last updated + refresh */}
      <div className="flex items-center gap-2 mt-1.5 text-xs text-[var(--text-secondary)]">
        <span>Last updated {formatDate(asset.last_fetched_at, { relative: true })}</span>
        <button
          onClick={onRefreshPrice}
          aria-label="Refresh price"
          className="p-0.5 rounded hover:bg-[var(--bg-tertiary)] transition-colors hover:text-[var(--text-primary)]"
        >
          <svg className="size-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>
  );
}
