import { useMemo } from 'react';
import { formatCurrency, formatPercent, getChangeColor } from '../../lib';
import { Skeleton } from '../ui';

function MiniSparkline({ data, positive }) {
  if (!data || data.length < 2) return null;

  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 80;
  const h = 28;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });
  const lineD = `M${points.join(' L')}`;
  const fillD = `${lineD} L${w},${h} L0,${h} Z`;
  const color = positive ? 'var(--positive)' : 'var(--negative)';
  const gradId = `spark-${positive ? 'p' : 'n'}`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-20 h-7 flex-shrink-0">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.18" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={fillD} fill={`url(#${gradId})`} />
      <path d={lineD} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function SummaryStrip({ summary, snapshots, loading, currency }) {
  const isPositive = summary?.day_change != null ? summary.day_change >= 0 : true;

  const gainLoss = useMemo(() => {
    if (!summary) return null;
    const totalValue = summary.total_value || 0;
    const costBasis = summary.total_cost_basis || 0;
    return totalValue - costBasis;
  }, [summary]);

  const gainLossPct = useMemo(() => {
    if (!summary || !summary.total_cost_basis) return null;
    return ((gainLoss || 0) / summary.total_cost_basis) * 100;
  }, [summary, gainLoss]);

  if (loading) {
    return (
      <div className="mb-5 pb-[18px] border-b border-[var(--border-primary)]">
        <Skeleton className="h-20 w-full rounded-lg" />
      </div>
    );
  }

  if (!summary) return null;

  const changeColor = getChangeColor(summary.day_change);

  return (
    <div className="mb-5 pb-[18px] border-b border-[var(--border-primary)]">
      <div className="flex items-start gap-8 flex-wrap">
        {/* Hero: total value */}
        <div className="flex-shrink-0">
          <div className="text-[11px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
            Total Portfolio Value
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[28px] font-bold font-mono tabular-nums leading-none">
              {formatCurrency(summary.total_value, currency)}
            </span>
            <MiniSparkline data={snapshots?.slice(-7)} positive={isPositive} />
          </div>
          {summary.day_change != null && (
            <div className="flex items-center gap-2 mt-1.5">
              <span className={`text-sm font-semibold font-mono tabular-nums ${changeColor}`}>
                {summary.day_change >= 0 ? '+' : ''}
                {formatCurrency(summary.day_change, currency)}
                {summary.day_change_pct != null && ` (${formatPercent(summary.day_change_pct)})`}
              </span>
              <span className="text-[11px] text-[var(--text-tertiary)]">today</span>
            </div>
          )}
        </div>

        {/* Metric cards */}
        <div className="flex items-start gap-6 flex-wrap ml-auto">
          {/* Total Gain/Loss */}
          <div className="text-right min-w-[100px]">
            <div className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
              Total Gain/Loss
            </div>
            <div className={`text-[15px] font-bold font-mono tabular-nums ${getChangeColor(gainLoss)}`}>
              {gainLoss != null && (gainLoss >= 0 ? '+' : '')}
              {formatCurrency(gainLoss || 0, currency)}
            </div>
            {gainLossPct != null && (
              <div className={`text-[11px] font-medium ${getChangeColor(gainLossPct)}`}>
                {gainLossPct >= 0 ? '+' : ''}{gainLossPct.toFixed(1)}% all time
              </div>
            )}
          </div>

          {/* Cost Basis */}
          <div className="text-right min-w-[100px]">
            <div className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
              Cost Basis
            </div>
            <div className="text-[15px] font-bold font-mono tabular-nums">
              {formatCurrency(summary.total_cost_basis || 0, currency)}
            </div>
            <div className="text-[11px] text-[var(--text-tertiary)]">total invested</div>
          </div>

          {/* Cash */}
          <div className="text-right min-w-[80px]">
            <div className="text-[10px] font-medium text-[var(--text-tertiary)] uppercase tracking-wide mb-1">
              Cash
            </div>
            <div className="text-[15px] font-bold font-mono tabular-nums">
              {formatCurrency(summary.total_cash || 0, currency)}
            </div>
            <div className="text-[11px] text-[var(--text-tertiary)]">
              across {summary.accounts?.length || 0} accounts
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
