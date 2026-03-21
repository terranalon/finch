import { useState, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatCurrency, formatPercent, getChangeColor } from '../../lib';
import api from '../../lib/api';
import { Skeleton } from '../ui';
import { SortArrow, FavoriteStar, toAssetClickPayload } from './shared';

export function TopHoldingsTable({ holdings, totalValue, loading, currency, onAssetClick, favoriteOverrides = {}, onFavoriteToggle }) {
  const [sortKey, setSortKey] = useState('weight');
  const [sortDir, setSortDir] = useState('desc');

  // Merge external favorite overrides from sibling components (e.g. AssetExplorerCard)
  const effectiveHoldings = useMemo(() => {
    if (!holdings) return null;
    if (!Object.keys(favoriteOverrides).length) return holdings;
    return holdings.map((h) =>
      h.asset_id in favoriteOverrides ? { ...h, is_favorite: favoriteOverrides[h.asset_id] } : h
    );
  }, [holdings, favoriteOverrides]);

  const toggleFavorite = useCallback((assetId) => {
    const current = effectiveHoldings?.find((h) => h.asset_id === assetId);
    const newVal = current ? !current.is_favorite : true;
    onFavoriteToggle?.(assetId, newVal);
    api(`/assets/${assetId}/favorite`, { method: 'PUT' }).catch(() => {
      onFavoriteToggle?.(assetId, !newVal);
    });
  }, [effectiveHoldings, onFavoriteToggle]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = useMemo(() => {
    if (!effectiveHoldings) return [];
    const items = effectiveHoldings.map((h) => ({
      ...h,
      weight: totalValue > 0 ? (h.market_value / totalValue) * 100 : 0,
      pnl: h.market_value - h.cost_basis,
      pnl_pct: h.cost_basis > 0 ? ((h.market_value - h.cost_basis) / h.cost_basis) * 100 : 0,
      day_change_amt: h.day_change_pct != null ? h.market_value * h.day_change_pct / (100 + h.day_change_pct) : null,
    }));

    const getVal = (item) => {
      switch (sortKey) {
        case 'name': return (item.name || item.symbol).toLowerCase();
        case 'amount': return item.quantity || 0;
        case 'price': return item.current_price || 0;
        case 'cost': return item.cost_basis;
        case 'value': return item.market_value;
        case 'weight': return item.weight;
        case 'day': return item.day_change_pct || 0;
        case 'pnl': return item.pnl;
        default: return item.weight;
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
  }, [effectiveHoldings, totalValue, sortKey, sortDir]);

  if (loading) {
    return <div className="card mb-5"><Skeleton className="h-[300px] w-full" /></div>;
  }

  if (!effectiveHoldings || effectiveHoldings.length === 0) return null;

  const columns = [
    { key: 'name', label: 'Asset', align: '' },
    { key: 'price', label: 'Price', align: 'text-right' },
    { key: 'amount', label: 'Amount', align: 'text-right' },
    { key: 'cost', label: 'Cost Basis', align: 'text-right' },
    { key: 'value', label: 'Value', align: 'text-right' },
    { key: 'weight', label: 'Weight', align: 'text-right' },
    { key: 'day', label: 'Day', align: 'text-right' },
    { key: 'pnl', label: 'Total P&L', align: 'text-right' },
  ];

  return (
    <div className="card mb-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-semibold">Top Holdings</span>
        <Link to="/holdings" className="text-[12px] text-accent hover:text-accent-hover font-medium">
          All holdings &rarr;
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px]">
          <thead>
            <tr>
              <th className="table-header w-7 pr-0" />
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className={cn('table-header cursor-pointer select-none hover:text-[var(--text-primary)]', col.align)}
                >
                  {col.label}
                  {sortKey === col.key && <SortArrow dir={sortDir} />}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((h) => (
              <tr
                key={h.id}
                onClick={() => onAssetClick?.(toAssetClickPayload(h))}
                className="table-row-hover"
              >
                <td className="table-cell pr-0">
                  <FavoriteStar
                    isFavorite={h.is_favorite}
                    onClick={() => toggleFavorite(h.asset_id)}
                  />
                </td>
                <td className="table-cell">
                  <div className="font-semibold text-[var(--text-primary)]">{h.name || h.symbol}</div>
                  <div className="text-[10px] text-[var(--text-tertiary)]">{h.symbol}</div>
                </td>
                <td className="table-cell text-right font-mono tabular-nums">
                  {h.asset_class === 'Cash' ? '--' : (h.current_price != null ? formatCurrency(h.current_price, h.currency || currency) : '--')}
                </td>
                <td className="table-cell text-right font-mono tabular-nums">
                  {h.asset_class === 'Cash' ? '--' : (h.quantity != null ? h.quantity.toLocaleString(undefined, { maximumFractionDigits: 4 }) : '--')}
                </td>
                <td className="table-cell text-right font-mono tabular-nums">
                  {h.asset_class === 'Cash' ? '--' : formatCurrency(h.cost_basis, currency)}
                </td>
                <td className="table-cell text-right font-mono tabular-nums font-semibold">
                  {formatCurrency(h.market_value, currency)}
                </td>
                <td className="table-cell text-right font-mono tabular-nums">
                  {h.weight.toFixed(1)}%
                </td>
                <td className={cn('table-cell text-right font-mono tabular-nums', getChangeColor(h.day_change_pct))}>
                  {h.day_change_pct != null && h.day_change_pct !== 0 ? (
                    <>
                      <div>{h.day_change_amt >= 0 ? '+' : ''}{formatCurrency(h.day_change_amt, currency)}</div>
                      <div className="text-[10px]">{formatPercent(h.day_change_pct)}</div>
                    </>
                  ) : '--'}
                </td>
                <td className={cn('table-cell text-right font-mono tabular-nums', getChangeColor(h.pnl))}>
                  {h.asset_class === 'Cash' ? '--' : (
                    <>
                      <div>{h.pnl >= 0 ? '+' : ''}{formatCurrency(h.pnl, currency)}</div>
                      <div className="text-[10px]">{formatPercent(h.pnl_pct)}</div>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
