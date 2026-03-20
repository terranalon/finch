import { useState, useEffect } from 'react';
import { cn, formatCurrency, formatPercent, getChangeColor } from '../../lib';
import api from '../../lib/api';
import { Skeleton } from '../ui';
import { toAssetClickPayload } from './shared';

function TriangleUp() {
  return (
    <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 2L11 10H1L6 2Z" />
    </svg>
  );
}

function TriangleDown() {
  return (
    <svg className="w-3 h-3" viewBox="0 0 12 12" fill="currentColor">
      <path d="M6 10L1 2H11L6 10Z" />
    </svg>
  );
}

export function MoversCard({ onAssetClick }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api('/dashboard/movers?limit=3')
      .then((resp) => resp.json())
      .then((res) => { if (!cancelled) setData(res); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <Skeleton className="h-[140px] w-full rounded-lg" />;
  }

  if (!data) return null;

  const renderSection = (title, items, isGainer) => {
    if (!items || items.length === 0) return null;
    return (
      <div className={isGainer ? 'mb-3' : ''}>
        <div className={cn('flex items-center gap-1.5 mb-2 text-[11px] font-semibold uppercase tracking-wide', isGainer ? 'text-positive' : 'text-negative')}>
          {isGainer ? <TriangleUp /> : <TriangleDown />}
          {title}
        </div>
        {items.map((item) => (
          <div
            key={item.asset_id}
            onClick={() => onAssetClick?.(toAssetClickPayload(item))}
            className="flex items-center gap-2 py-1.5 cursor-pointer hover:bg-[var(--bg-tertiary)] -mx-2 px-2 rounded transition-colors"
          >
            <div className="flex-1 min-w-0">
              <span className="text-[12px] font-medium truncate">{item.name || item.symbol}</span>
            </div>
            <span className="text-[11px] font-mono tabular-nums text-[var(--text-tertiary)]">
              {item.current_price != null ? formatCurrency(item.current_price, item.currency || 'USD') : '--'}
            </span>
            <span className={cn('text-[11px] font-mono tabular-nums font-semibold min-w-[50px] text-right', getChangeColor(item.day_change_pct))}>
              {item.day_change_pct != null ? formatPercent(item.day_change_pct) : '--'}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <>
      {renderSection('Gainers', data.gainers, true)}
      {renderSection('Losers', data.losers, false)}
    </>
  );
}
