import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatCurrency, formatPercent, getChangeColor, ASSET_COLORS } from '../../lib';
import api from '../../lib/api';
import { usePortfolio } from '../../contexts';
import { Skeleton, MiniSparkline } from '../ui';
import { SortArrow, FavoriteStar, toAssetClickPayload } from './shared';

const TABS = ['Favorites', 'Popular', 'Gainers', 'Losers'];
const TAB_LIMIT = 5;

export function AssetExplorerCard({ onAssetClick, favoriteOverrides = {}, onFavoriteToggle }) {
  const { selectedPortfolioId } = usePortfolio();
  const [tab, setTab] = useState('Favorites');
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('chg');
  const [sortDir, setSortDir] = useState('desc');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const portfolioParam = selectedPortfolioId
      ? `&portfolio_id=${selectedPortfolioId}`
      : '';
    api(`/positions?limit=100${portfolioParam}`)
      .then((resp) => resp.json())
      .then((res) => {
        if (!cancelled) setPositions(res.items || res || []);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedPortfolioId]);

  // Apply external favorite overrides from other components (e.g. TopHoldingsTable)
  const effectivePositions = useMemo(() => {
    if (!Object.keys(favoriteOverrides).length) return positions;
    return positions.map((p) =>
      p.asset_id in favoriteOverrides ? { ...p, is_favorite: favoriteOverrides[p.asset_id] } : p
    );
  }, [positions, favoriteOverrides]);

  const [sparklines, setSparklines] = useState({});
  const sparklineCacheRef = useRef({});

  const toggleFavorite = useCallback((assetId) => {
    // Optimistic update — toggle immediately, fire API in background
    setPositions((prev) => {
      const pos = prev.find((p) => p.asset_id === assetId);
      const newVal = pos ? !pos.is_favorite : true;
      onFavoriteToggle?.(assetId, newVal);
      return prev.map((p) => p.asset_id === assetId ? { ...p, is_favorite: newVal } : p);
    });
    api(`/assets/${assetId}/favorite`, { method: 'PUT' }).catch(() => {
      setPositions((prev) => {
        const pos = prev.find((p) => p.asset_id === assetId);
        const revertVal = pos ? !pos.is_favorite : false;
        onFavoriteToggle?.(assetId, revertVal);
        return prev.map((p) => p.asset_id === assetId ? { ...p, is_favorite: revertVal } : p);
      });
    });
  }, [onFavoriteToggle]);

  const handleTabChange = (t) => {
    setTab(t);
    setSortKey('chg');
    setSortDir(t === 'Losers' ? 'asc' : 'desc');
  };

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  // Count of matching items before slicing (for "See all" link)
  const totalForTab = useMemo(() => {
    if (!effectivePositions.length) return 0;
    switch (tab) {
      case 'Favorites':
        return effectivePositions.filter((p) => p.is_favorite).length;
      case 'Popular':
        return effectivePositions.length;
      case 'Gainers':
        return effectivePositions.filter((p) => p.day_change_pct != null && p.day_change_pct > 0).length;
      case 'Losers':
        return effectivePositions.filter((p) => p.day_change_pct != null && p.day_change_pct < 0).length;
      default:
        return effectivePositions.length;
    }
  }, [effectivePositions, tab]);

  const filtered = useMemo(() => {
    if (!effectivePositions.length) return [];
    let items;
    switch (tab) {
      case 'Favorites':
        items = effectivePositions.filter((p) => p.is_favorite).slice(0, TAB_LIMIT);
        break;
      case 'Popular':
        items = [...effectivePositions].sort((a, b) => (b.total_market_value || 0) - (a.total_market_value || 0)).slice(0, TAB_LIMIT);
        break;
      case 'Gainers':
        items = [...effectivePositions]
          .filter((p) => p.day_change_pct != null && p.day_change_pct > 0)
          .sort((a, b) => b.day_change_pct - a.day_change_pct)
          .slice(0, TAB_LIMIT);
        break;
      case 'Losers':
        items = [...effectivePositions]
          .filter((p) => p.day_change_pct != null && p.day_change_pct < 0)
          .sort((a, b) => a.day_change_pct - b.day_change_pct)
          .slice(0, TAB_LIMIT);
        break;
      default:
        items = effectivePositions.slice(0, TAB_LIMIT);
    }

    // Apply column sort
    const getVal = (p) => {
      switch (sortKey) {
        case 'name': return (p.name || p.symbol || '').toLowerCase();
        case 'price': return p.current_price || 0;
        case 'mcap': return p.market_cap || 0;
        case 'chg': return p.day_change_pct || 0;
        case '7d': return p.week_change_pct || 0;
        default: return 0;
      }
    };

    return [...items].sort((a, b) => {
      const aVal = getVal(a);
      const bVal = getVal(b);
      if (typeof aVal === 'string') {
        return sortDir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [effectivePositions, tab, sortKey, sortDir]);

  // Fetch sparklines for visible positions
  useEffect(() => {
    if (!filtered.length) return;
    const symbols = filtered.map((p) => p.symbol).filter(Boolean);
    const uncached = symbols.filter((s) => !(s in sparklineCacheRef.current));
    if (!uncached.length) {
      setSparklines({ ...sparklineCacheRef.current });
      return;
    }
    let cancelled = false;
    api(`/dashboard/sparklines?symbols=${uncached.join(',')}`)
      .then((resp) => resp.json())
      .then((res) => {
        if (cancelled) return;
        const merged = { ...sparklineCacheRef.current, ...res.sparklines };
        sparklineCacheRef.current = merged;
        setSparklines(merged);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [filtered]);

  if (loading) {
    return <div className="card"><Skeleton className="h-[240px] w-full" /></div>;
  }

  const columns = [
    { key: 'name', label: 'Asset', align: '' },
    { key: 'price', label: 'Price', align: 'text-right' },
    { key: 'mcap', label: 'Market Cap', align: 'text-right' },
    { key: 'chg', label: 'Day', align: 'text-right' },
    { key: '7d', label: '7D', align: 'text-right' },
    { key: null, label: '1D Chart', align: 'text-right' },
  ];

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => handleTabChange(t)}
              className={cn(
                'px-3.5 py-1.5 rounded-lg text-[12px] font-medium transition-all cursor-pointer',
                tab === t
                  ? 'bg-accent/10 text-accent font-semibold'
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
              )}
            >
              {t}
            </button>
          ))}
        </div>
        {totalForTab > TAB_LIMIT && (
          <Link to="/assets" className="text-[12px] text-accent hover:text-accent-hover font-medium">
            See all {tab.toLowerCase()} &rarr;
          </Link>
        )}
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
                {columns.map((col) => (
                  <th
                    key={col.label}
                    onClick={col.key ? () => handleSort(col.key) : undefined}
                    className={cn(
                      'table-header',
                      col.align,
                      col.key && 'cursor-pointer select-none hover:text-[var(--text-primary)]'
                    )}
                  >
                    {col.label}
                    {col.key && sortKey === col.key && <SortArrow dir={sortDir} />}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr
                  key={p.asset_id}
                  onClick={() => onAssetClick?.(toAssetClickPayload(p))}
                  className="table-row-hover"
                >
                  <td className="table-cell pr-0">
                    <FavoriteStar
                      isFavorite={p.is_favorite}
                      onClick={() => toggleFavorite(p.asset_id)}
                    />
                  </td>
                  <td className="table-cell">
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-7 h-7 rounded-full flex items-center justify-center text-[9px] font-semibold text-white flex-shrink-0"
                        style={{ background: ASSET_COLORS[p.asset_class] || '#64748B' }}
                      >
                        {(p.symbol || '??').substring(0, 2)}
                      </div>
                      <div>
                        <div className="font-semibold text-[13px] text-[var(--text-primary)]">{p.name || p.symbol}</div>
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
                  <td className="table-cell text-right font-mono tabular-nums" style={{ fontWeight: 600 }}>
                    {p.current_price != null ? formatCurrency(p.current_price, p.currency || 'USD') : '--'}
                  </td>
                  <td className="table-cell text-right font-mono tabular-nums">
                    {p.market_cap != null ? formatCurrency(p.market_cap, 'USD', { compact: true }) : '--'}
                  </td>
                  <td className={cn('table-cell text-right font-mono tabular-nums', getChangeColor(p.day_change_pct))} style={{ fontWeight: 600 }}>
                    {p.day_change_pct != null ? formatPercent(p.day_change_pct) : '--'}
                  </td>
                  <td className={cn('table-cell text-right font-mono tabular-nums', getChangeColor(p.week_change_pct))} style={{ fontWeight: 600 }}>
                    {p.week_change_pct != null ? formatPercent(p.week_change_pct) : '--'}
                  </td>
                  <td className="table-cell text-right">
                    <div className="w-[120px] h-7 ml-auto">
                      <MiniSparkline
                        data={sparklines[p.symbol]}
                        positive={(p.day_change_pct || 0) >= 0}
                        width={120}
                        height={28}
                      />
                    </div>
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
