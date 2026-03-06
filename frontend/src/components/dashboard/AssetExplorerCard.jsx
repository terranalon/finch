import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatCurrency, formatPercent, getChangeColor } from '../../lib';
import api from '../../lib/api';
import { Skeleton } from '../ui';

const ASSET_COLORS = {
  Equity: '#3B82F6',
  ETF: '#8B5CF6',
  Crypto: '#F59E0B',
  Cash: '#10B981',
  Bond: '#06B6D4',
};

const TABS = ['Favorites', 'Popular', 'Gainers', 'Losers'];

export function AssetExplorerCard({ onAssetClick }) {
  const [tab, setTab] = useState('Favorites');
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api('/api/positions?limit=100')
      .then((res) => {
        if (!cancelled) setPositions(res.items || res || []);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const filtered = useMemo(() => {
    if (!positions.length) return [];
    switch (tab) {
      case 'Favorites':
        return positions.filter((p) => p.is_favorite);
      case 'Popular':
        return [...positions].sort((a, b) => (b.total_market_value || 0) - (a.total_market_value || 0)).slice(0, 8);
      case 'Gainers':
        return [...positions]
          .filter((p) => p.day_change_pct != null && p.day_change_pct > 0)
          .sort((a, b) => b.day_change_pct - a.day_change_pct)
          .slice(0, 8);
      case 'Losers':
        return [...positions]
          .filter((p) => p.day_change_pct != null && p.day_change_pct < 0)
          .sort((a, b) => a.day_change_pct - b.day_change_pct)
          .slice(0, 8);
      default:
        return positions.slice(0, 8);
    }
  }, [positions, tab]);

  if (loading) {
    return <div className="card"><Skeleton className="h-[240px] w-full" /></div>;
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'px-3 py-1.5 rounded-md text-[11px] font-medium transition-all cursor-pointer',
                tab === t
                  ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] font-semibold'
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
              )}
            >
              {t}
            </button>
          ))}
        </div>
        <Link to="/assets" className="text-[12px] text-accent hover:text-accent-hover font-medium">
          All assets &rarr;
        </Link>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-8 text-[var(--text-tertiary)] text-sm">
          {tab === 'Favorites' ? 'No favorite assets yet' : 'No data available'}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px]">
            <thead>
              <tr>
                <th className="table-header w-7 pr-0" />
                <th className="table-header">Asset</th>
                <th className="table-header text-right">Price</th>
                <th className="table-header text-right">Day</th>
                <th className="table-header text-right">Value</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr
                  key={p.asset_id}
                  onClick={() => onAssetClick?.({
                    id: p.asset_id,
                    symbol: p.symbol,
                    name: p.name,
                    asset_class: p.asset_class,
                    current_price: p.current_price,
                    day_change_pct: p.day_change_pct,
                    currency: p.currency,
                  })}
                  className="table-row-hover"
                >
                  <td className="table-cell pr-0">
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full"
                      style={{ background: ASSET_COLORS[p.asset_class] || '#64748B' }}
                    />
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center gap-2">
                      <div>
                        <div className="font-semibold text-[var(--text-primary)]">{p.name || p.symbol}</div>
                        <div className="text-[10px] text-[var(--text-tertiary)] flex items-center gap-1">
                          {p.symbol}
                          {p.account_count > 0 && (
                            <span className="px-1 py-0.5 bg-[var(--bg-tertiary)] rounded text-[9px]">
                              Held
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="table-cell text-right font-mono tabular-nums">
                    {p.current_price != null ? formatCurrency(p.current_price, p.currency || 'USD') : '--'}
                  </td>
                  <td className={cn('table-cell text-right font-mono tabular-nums', getChangeColor(p.day_change_pct))}>
                    {p.day_change_pct != null ? formatPercent(p.day_change_pct) : '--'}
                  </td>
                  <td className="table-cell text-right font-mono tabular-nums font-semibold">
                    {p.total_market_value != null ? formatCurrency(p.total_market_value, 'USD') : '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
