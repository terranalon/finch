import { cn, formatCurrency, formatPercent, formatNumber, getChangeColor, getChangeIndicator, ASSET_COLORS } from '../../lib';

function ChevronIcon({ open }) {
  return (
    <svg
      className={cn('w-3.5 h-3.5 transition-transform', open && 'rotate-90')}
      fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
    </svg>
  );
}

function StarIcon({ filled }) {
  if (filled) {
    return (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
        <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clipRule="evenodd" />
      </svg>
    );
  }
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
    </svg>
  );
}

const FALLBACK_COLORS = Object.values(ASSET_COLORS);

function getIconColor(symbol, assetClass) {
  if (ASSET_COLORS[assetClass]) return ASSET_COLORS[assetClass];
  // Deterministic color from symbol hash
  let hash = 0;
  for (let i = 0; i < symbol.length; i++) hash = symbol.charCodeAt(i) + ((hash << 5) - hash);
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}

export function HoldingsRow({ position, isExpanded, onToggleExpand, onRowClick, onToggleFavorite }) {
  const isCash = position.asset_class === 'Cash';
  const isCrypto = position.asset_class === 'Crypto';
  const dayColor = getChangeColor(position.day_change_pct);
  const pnlColor = getChangeColor(position.total_pnl_native);

  const handleRowClick = (e) => {
    if (e.target.closest('[data-no-detail]')) return;
    onRowClick();
  };

  return (
    <tr
      id={`holdings-row-${position.asset_id}`}
      onClick={handleRowClick}
      className={cn(
        'border-b border-[var(--border-subtle)] cursor-pointer transition-colors hover:bg-[var(--bg-tertiary)]',
        isExpanded && 'bg-[var(--bg-tertiary)]'
      )}
    >
      {/* 1. Expand */}
      <td className="py-3 pl-2 pr-0 w-[28px] text-center">
        <button
          data-no-detail
          title="Expand"
          onClick={(e) => { e.stopPropagation(); onToggleExpand(); }}
          className="p-1 rounded hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer text-[var(--text-tertiary)]"
        >
          <ChevronIcon open={isExpanded} />
        </button>
      </td>

      {/* 2. Star */}
      <td className="py-3 px-1 w-[24px]">
        <button
          data-no-detail
          title={position.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(); }}
          className={cn(
            'cursor-pointer transition-colors text-base leading-none',
            position.is_favorite ? 'text-amber-500' : 'text-[var(--text-faint)] hover:text-amber-400'
          )}
        >
          <StarIcon filled={position.is_favorite} />
        </button>
      </td>

      {/* 3. Icon */}
      <td className="py-3 pr-0 pl-1 w-[32px]">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
          style={{ background: getIconColor(position.symbol, position.asset_class) }}
        >
          {position.symbol.slice(0, 2).toUpperCase()}
        </div>
      </td>

      {/* 4. Symbol */}
      <td className="py-3 pl-2 pr-1">
        <span className="font-mono font-semibold text-[var(--text-primary)] text-[13px]">
          {position.symbol}
        </span>
      </td>

      {/* 5. Name */}
      <td className="py-3 px-1">
        <p className="text-[var(--text-primary)] truncate max-w-[160px] text-[13px]" title={position.name}>
          {position.name}
        </p>
      </td>

      {/* 6. Price + day change */}
      <td className="py-3 px-2 text-right whitespace-nowrap">
        <p className="font-mono tabular-nums text-[var(--text-primary)] text-[13px]">
          {formatCurrency(position.current_price, position.currency)}
        </p>
        {!isCash && position.day_change_pct != null && (
          <p className={cn('text-[11px] tabular-nums', dayColor)}>
            {getChangeIndicator(position.day_change_pct)} {formatPercent(position.day_change_pct)}
          </p>
        )}
      </td>

      {/* 7. Qty */}
      <td className="py-3 px-2 text-right font-mono tabular-nums text-[var(--text-secondary)] text-[13px]">
        {formatNumber(position.total_quantity, { decimals: isCrypto ? 4 : 0 })}
      </td>

      {/* 8. Avg Cost */}
      <td className="py-3 px-2 text-right font-mono tabular-nums text-[var(--text-tertiary)] text-[13px]">
        {isCash ? '\u2014' : formatCurrency(position.avg_cost_per_unit_native, position.currency)}
      </td>

      {/* 9. Cost Basis */}
      <td className="py-3 px-2 text-right font-mono tabular-nums text-[var(--text-secondary)] text-[13px]">
        {isCash ? '\u2014' : formatCurrency(position.total_cost_basis_native, position.currency)}
      </td>

      {/* 10. Value */}
      <td className="py-3 px-2 text-right font-mono tabular-nums font-semibold text-[var(--text-primary)] text-[13px]">
        {formatCurrency(position.total_market_value_native, position.currency)}
      </td>

      {/* 11. P&L */}
      <td className="py-3 px-2 text-right whitespace-nowrap">
        {isCash ? (
          <span className="text-[var(--text-faint)]">{'\u2014'}</span>
        ) : (
          <>
            <p className={cn('font-mono tabular-nums font-semibold text-[13px]', pnlColor)}>
              {getChangeIndicator(position.total_pnl_native)} {formatCurrency(Math.abs(position.total_pnl_native), position.currency)}
            </p>
            <p className={cn('text-[11px] tabular-nums', pnlColor)}>
              {formatPercent(position.total_pnl_pct)}
            </p>
          </>
        )}
      </td>

      {/* 12. Accts badge */}
      <td className="py-3 px-2 text-center">
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-accent/10 text-accent text-[10px] font-semibold">
          {position.account_count}
        </span>
      </td>
    </tr>
  );
}
