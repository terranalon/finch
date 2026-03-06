import { useState, useMemo, useEffect } from 'react';
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { cn, formatCurrency, formatPercent, getChangeColor } from '../../lib';
import { calculateTWR } from '../../lib/twr';
import { useChartColors } from '../../hooks/useChartColors';
import { Skeleton } from '../ui';
import api from '../../lib/api';

const PERIODS = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: 'ALL', days: null },
];

const PERIOD_TO_API = { '1W': '5d', '1M': '1mo', '3M': '3mo', '6M': '6mo', '1Y': '1y', ALL: 'max' };

function filterByPeriod(data, days) {
  if (!days || !data.length) return data;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return data.filter((d) => new Date(d.date) >= cutoff);
}

function formatXDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function ChartCard({ snapshots, cashFlows, summary, currency, loading }) {
  const [tab, setTab] = useState('value');
  const [period, setPeriod] = useState('1M');
  const [benchmark, setBenchmark] = useState(null);
  const [hoverData, setHoverData] = useState(null);
  const colors = useChartColors();

  // Fetch benchmark when on performance tab
  useEffect(() => {
    if (tab !== 'perf') return;
    let cancelled = false;
    api(`/api/dashboard/benchmark?period=${PERIOD_TO_API[period] || '1mo'}&symbol=SPY`)
      .then((res) => { if (!cancelled) setBenchmark(res); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [tab, period]);

  const filteredSnapshots = useMemo(
    () => filterByPeriod(snapshots, PERIODS.find((p) => p.label === period)?.days),
    [snapshots, period]
  );

  const twrData = useMemo(
    () => (tab === 'perf' ? calculateTWR(filteredSnapshots, cashFlows) : []),
    [filteredSnapshots, cashFlows, tab]
  );

  // Merge benchmark data into performance chart
  const chartData = useMemo(() => {
    if (tab === 'value') {
      return filteredSnapshots.map((s) => ({
        date: s.date,
        value: s.value,
        label: formatXDate(s.date),
      }));
    }

    const benchMap = new Map();
    if (benchmark?.data) {
      benchmark.data.forEach((d) => benchMap.set(d.date, d.performance));
    }

    return twrData.map((s) => ({
      date: s.date,
      performance: s.performance,
      benchmark: benchMap.get(s.date) ?? null,
      label: formatXDate(s.date),
    }));
  }, [tab, filteredSnapshots, twrData, benchmark]);

  // Compute period change for display
  const periodChange = useMemo(() => {
    if (!filteredSnapshots.length) return null;
    const first = filteredSnapshots[0].value;
    const last = filteredSnapshots[filteredSnapshots.length - 1].value;
    const change = last - first;
    const pct = first > 0 ? (change / first) * 100 : 0;
    return { value: last, change, pct };
  }, [filteredSnapshots]);

  if (loading) {
    return <div className="card mb-5"><Skeleton className="h-[300px] w-full" /></div>;
  }

  const displayValue = hoverData?.value ?? periodChange?.value ?? summary?.total_value;
  const displayChange = hoverData?.change ?? periodChange?.change;
  const displayPct = hoverData?.pct ?? periodChange?.pct;
  const displayDate = hoverData?.date ?? `past ${period === 'ALL' ? 'all time' : period.toLowerCase()}`;

  return (
    <div className="card mb-5">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex gap-1 bg-[var(--bg-tertiary)] rounded-lg p-0.5">
          {['value', 'perf'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-all cursor-pointer',
                tab === t
                  ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
              )}
            >
              {t === 'value' ? 'Value' : 'Performance %'}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.label}
              onClick={() => setPeriod(p.label)}
              className={cn(
                'px-2.5 py-1 rounded-md text-[11px] font-medium transition-all cursor-pointer',
                period === p.label
                  ? 'bg-accent text-white'
                  : 'text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)]'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Hover display */}
      <div className="flex items-baseline justify-between mb-2">
        <div className="flex items-baseline gap-3">
          {tab === 'value' ? (
            <span className="text-xl font-bold font-mono tabular-nums">
              {formatCurrency(displayValue || 0, currency)}
            </span>
          ) : (
            <span className="text-xl font-bold font-mono tabular-nums">
              {displayPct != null ? formatPercent(displayPct) : '--'}
            </span>
          )}
          {displayChange != null && (
            <span className={`text-sm font-semibold font-mono ${getChangeColor(displayChange)}`}>
              {displayChange >= 0 ? '+' : ''}{formatCurrency(displayChange, currency)}
              {displayPct != null && ` (${formatPercent(displayPct)})`}
            </span>
          )}
          <span className="text-[11px] text-[var(--text-tertiary)]">{displayDate}</span>
        </div>
        {tab === 'perf' && (
          <div className="flex items-center gap-4 text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ background: colors.accent }} />
              Portfolio
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ background: 'var(--warning)' }} />
              S&P 500
            </div>
          </div>
        )}
      </div>

      {/* Chart */}
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          {tab === 'value' ? (
            <AreaChart
              data={chartData}
              onMouseMove={(e) => {
                if (e?.activePayload?.[0]) {
                  const d = e.activePayload[0].payload;
                  const first = filteredSnapshots[0]?.value || 0;
                  const change = d.value - first;
                  const pct = first > 0 ? (change / first) * 100 : 0;
                  setHoverData({ value: d.value, change, pct, date: formatXDate(d.date) });
                }
              }}
              onMouseLeave={() => setHoverData(null)}
              margin={{ top: 4, right: 4, bottom: 0, left: 4 }}
            >
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.accent} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={colors.accent} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: colors.textTertiary }}
                interval="preserveStartEnd"
                minTickGap={60}
              />
              <YAxis hide domain={['auto', 'auto']} />
              <Tooltip content={() => null} />
              <Area
                type="monotone"
                dataKey="value"
                stroke={colors.accent}
                strokeWidth={2}
                fill="url(#areaGrad)"
                dot={false}
                activeDot={{ r: 4, fill: colors.accent, stroke: colors.bgSecondary, strokeWidth: 2 }}
              />
            </AreaChart>
          ) : (
            <LineChart
              data={chartData}
              onMouseMove={(e) => {
                if (e?.activePayload?.[0]) {
                  const d = e.activePayload[0].payload;
                  setHoverData({ pct: d.performance, date: formatXDate(d.date) });
                }
              }}
              onMouseLeave={() => setHoverData(null)}
              margin={{ top: 4, right: 4, bottom: 0, left: 4 }}
            >
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: colors.textTertiary }}
                interval="preserveStartEnd"
                minTickGap={60}
              />
              <YAxis hide domain={['auto', 'auto']} />
              <Tooltip content={() => null} />
              <ReferenceLine y={0} stroke={colors.borderPrimary} strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="performance"
                stroke={colors.accent}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: colors.accent, stroke: colors.bgSecondary, strokeWidth: 2 }}
              />
              <Line
                type="monotone"
                dataKey="benchmark"
                stroke="var(--warning)"
                strokeWidth={1.8}
                strokeDasharray="6 3"
                dot={false}
                activeDot={false}
                connectNulls
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
