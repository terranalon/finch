import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatCurrency, formatPercent, getChangeColor } from '../../lib';
import { Skeleton } from '../ui';

const ASSET_COLORS = {
  Equity: '#3B82F6',
  ETF: '#8B5CF6',
  Crypto: '#F59E0B',
  Cash: '#10B981',
  Bond: '#06B6D4',
  MutualFund: '#EC4899',
};

function SortArrow({ dir }) {
  return <span className="text-[10px] ml-0.5 opacity-60">{dir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
}

export function TopHoldingsTable({ holdings, totalValue, loading, currency, onAssetClick }) {
  const [sortKey, setSortKey] = useState('weight');
  const [sortDir, setSortDir] = useState('desc');

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = useMemo(() => {
    if (!holdings) return [];
    const items = holdings.map((h) => ({
      ...h,
      weight: totalValue > 0 ? (h.market_value / totalValue) * 100 : 0,
      pnl: h.market_value - h.cost_basis,
      pnl_pct: h.cost_basis > 0 ? ((h.market_value - h.cost_basis) / h.cost_basis) * 100 : 0,
    }));

    const getVal = (item) => {
      switch (sortKey) {
        case 'name': return (item.name || item.symbol).toLowerCase();
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
  }, [holdings, totalValue, sortKey, sortDir]);

  if (loading) {
    return <div className="card mb-5"><Skeleton className="h-[300px] w-full" /></div>;
  }

  if (!holdings || holdings.length === 0) return null;

  const columns = [
    { key: 'name', label: 'Asset', align: '' },
    { key: 'price', label: 'Price', align: 'text-right' },
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
                onClick={() => onAssetClick?.(h)}
                className="table-row-hover"
              >
                <td className="table-cell pr-0">
                  <span
                    className="inline-block w-2.5 h-2.5 rounded-full"
                    style={{ background: ASSET_COLORS[h.asset_class] || '#64748B' }}
                  />
                </td>
                <td className="table-cell">
                  <div className="font-semibold text-[var(--text-primary)]">{h.name || h.symbol}</div>
                  <div className="text-[10px] text-[var(--text-tertiary)]">{h.symbol}</div>
                </td>
                <td className="table-cell text-right font-mono tabular-nums">
                  {h.current_price != null ? formatCurrency(h.current_price, h.currency || currency) : '--'}
                </td>
                <td className="table-cell text-right font-mono tabular-nums">
                  {formatCurrency(h.cost_basis, currency)}
                </td>
                <td className="table-cell text-right font-mono tabular-nums font-semibold">
                  {formatCurrency(h.market_value, currency)}
                </td>
                <td className="table-cell text-right font-mono tabular-nums">
                  {h.weight.toFixed(1)}%
                </td>
                <td className={cn('table-cell text-right font-mono tabular-nums', getChangeColor(h.day_change_pct))}>
                  {h.day_change_pct != null ? formatPercent(h.day_change_pct) : '--'}
                </td>
                <td className={cn('table-cell text-right font-mono tabular-nums', getChangeColor(h.pnl))}>
                  <div>{h.pnl >= 0 ? '+' : ''}{formatCurrency(h.pnl, currency)}</div>
                  <div className="text-[10px]">{formatPercent(h.pnl_pct)}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
