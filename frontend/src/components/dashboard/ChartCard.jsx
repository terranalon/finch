import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { cn, formatCurrency, formatPercent, formatDate, getChangeColor } from '../../lib';
import { calculateTWR } from '../../lib/twr';
import { useChartColors } from '../../hooks/useChartColors';
import { useClickOutside } from '../../hooks/useClickOutside';
import { Skeleton, DateRangeCalendar } from '../ui';
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

function filterByPeriod(data, days, customRange) {
  if (!data.length) return data;
  if (customRange?.start && customRange?.end) {
    const start = new Date(customRange.start);
    const end = new Date(customRange.end);
    end.setHours(23, 59, 59);
    return data.filter((d) => {
      const dt = new Date(d.date);
      return dt >= start && dt <= end;
    });
  }
  if (!days) return data;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return data.filter((d) => new Date(d.date) >= cutoff);
}

export function ChartCard({ snapshots, cashFlows, summary, currency, loading }) {
  const [tab, setTab] = useState('value');
  const [period, setPeriod] = useState('1M');
  const [benchmark, setBenchmark] = useState(null);
  const [hoverData, setHoverData] = useState(null);
  const [periodOpen, setPeriodOpen] = useState(false);
  const [showCalendar, setShowCalendar] = useState(false);
  const [customRange, setCustomRange] = useState({ start: '', end: '' });
  const periodRef = useRef(null);
  const colors = useChartColors();

  useClickOutside(periodRef, useCallback(() => setPeriodOpen(false), []));

  // Fetch benchmark when on performance tab
  useEffect(() => {
    if (tab !== 'perf') return;
    if (period === 'custom' && (!customRange.start || !customRange.end)) return;
    let cancelled = false;
    const benchParams = period === 'custom'
      ? new URLSearchParams({ start_date: customRange.start, end_date: customRange.end, symbol: 'SPY' })
      : new URLSearchParams({ period: PERIOD_TO_API[period] || '1mo', symbol: 'SPY' });
    const benchUrl = `/dashboard/benchmark?${benchParams}`;
    api(benchUrl)
      .then((resp) => resp.json())
      .then((res) => { if (!cancelled) setBenchmark(res); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [tab, period, customRange.start, customRange.end]);

  const filteredSnapshots = useMemo(
    () => filterByPeriod(
      snapshots,
      PERIODS.find((p) => p.label === period)?.days,
      period === 'custom' ? customRange : null
    ),
    [snapshots, period, customRange]
  );

  const twrData = useMemo(
    () => (tab === 'perf' ? calculateTWR(filteredSnapshots, cashFlows) : []),
    [filteredSnapshots, cashFlows, tab]
  );

  // TWR percentage for period header (only meaningful on perf tab)
  const twrPct = useMemo(() => {
    if (!twrData.length) return null;
    return twrData[twrData.length - 1].performance;
  }, [twrData]);

  // Merge benchmark data into performance chart
  // Labels are ISO dates; display formatting is handled by tickFormatter
  const chartData = useMemo(() => {
    if (tab === 'value') {
      return filteredSnapshots.map((s) => ({
        date: s.date,
        value: s.value,
        label: s.date.split('T')[0],
      }));
    }

    // Build lookup of raw benchmark performance by date
    const benchMap = new Map();
    if (benchmark?.data) {
      benchmark.data.forEach((d) => benchMap.set(d.date, d.performance));
    }

    // Rebase benchmark so it starts at 0% on the portfolio's first date.
    // Without this, "ALL" shows SPY from 1993 (+2600%) dwarfing the portfolio.
    // Use closest earlier date since portfolio may start on a holiday/weekend.
    let basePerf = null;
    const firstDate = twrData[0]?.date?.split('T')[0];
    if (firstDate != null && benchmark?.data?.length) {
      for (let i = benchmark.data.length - 1; i >= 0; i--) {
        if (benchmark.data[i].date <= firstDate) {
          basePerf = benchmark.data[i].performance;
          break;
        }
      }
      // Fallback: if the first snapshot is before the earliest benchmark date
      // (e.g., portfolio starts on a weekend/holiday), use the first benchmark point.
      if (basePerf == null) {
        basePerf = benchmark.data[0].performance;
      }
    }
    const rebase = (perf) => {
      if (perf == null || basePerf == null) return null;
      return Math.round(((1 + perf / 100) / (1 + basePerf / 100) - 1) * 10000) / 100;
    };

    return twrData.map((s) => ({
      date: s.date,
      performance: s.performance,
      benchmark: rebase(benchMap.get(s.date)),
      label: s.date.split('T')[0],
    }));
  }, [tab, filteredSnapshots, twrData, benchmark]);

  // Final benchmark percentage for non-hover display (last trading day with data)
  const benchEndPct = useMemo(() => {
    if (!chartData.length || tab !== 'perf') return null;
    for (let i = chartData.length - 1; i >= 0; i--) {
      if (chartData[i].benchmark != null) return chartData[i].benchmark;
    }
    return null;
  }, [chartData, tab]);

  // Effective span in days (null for ALL = unbounded)
  const spanDays = useMemo(() => {
    if (period === 'custom' && customRange.start && customRange.end) {
      return Math.round((new Date(customRange.end) - new Date(customRange.start)) / 86400000);
    }
    return PERIODS.find((p) => p.label === period)?.days ?? null;
  }, [period, customRange]);

  // Explicit tick positions for long spans (one per year); shorter spans use auto
  const xTicks = useMemo(() => {
    if (!chartData.length) return undefined;
    if (spanDays != null && spanDays <= 365) return undefined;
    const seen = new Set();
    return chartData.reduce((acc, d) => {
      const year = new Date(d.label).getFullYear();
      if (!seen.has(year)) {
        seen.add(year);
        acc.push(d.label);
      }
      return acc;
    }, []);
  }, [chartData, spanDays]);

  // Format x-axis tick labels based on effective span
  const formatTick = (dateStr) => {
    const d = new Date(dateStr);
    if (spanDays == null || spanDays > 365) return String(d.getFullYear());
    if (spanDays > 90) {
      return `${d.toLocaleString('en-US', { month: 'short' })} '${String(d.getFullYear()).slice(2)}`;
    }
    return formatDate(dateStr);
  };

  // Compute period change for display
  const periodChange = useMemo(() => {
    if (!filteredSnapshots.length) return null;
    const first = filteredSnapshots[0].value;
    const last = filteredSnapshots[filteredSnapshots.length - 1].value;
    const change = last - first;
    const pct = first > 0 ? (change / first) * 100 : 0;
    return { value: last, change, pct };
  }, [filteredSnapshots]);

  // Dropdown trigger label
  const periodLabel = useMemo(() => {
    if (period === 'custom') {
      if (customRange.start && customRange.end) {
        const fmt = (d) => new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        return `${fmt(customRange.start)} - ${fmt(customRange.end)}`;
      }
      return 'Custom';
    }
    return period;
  }, [period, customRange]);

  if (loading) {
    return <div className="card mb-5"><Skeleton className="h-[300px] w-full" /></div>;
  }

  const displayValue = hoverData?.value ?? periodChange?.value ?? summary?.total_value;
  const displayChange = hoverData?.change ?? periodChange?.change;
  // On perf tab, show TWR percentage (cash-flow-adjusted) instead of simple return
  const displayPct = tab === 'perf'
    ? (hoverData?.pct ?? twrPct)
    : (hoverData?.pct ?? periodChange?.pct);
  const displayDate = hoverData?.date ?? (
    period === 'custom'
      ? (customRange.start && customRange.end
          ? `${formatDate(customRange.start)} - ${formatDate(customRange.end)}`
          : 'custom range')
      : period === 'ALL' ? 'all time' : `past ${period.toLowerCase()}`
  );

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
        <div className="relative" ref={periodRef}>
          <button
            onClick={() => { setPeriodOpen((prev) => !prev); setShowCalendar(false); }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium transition-all cursor-pointer bg-[var(--bg-tertiary)] text-[var(--text-primary)]"
          >
            <span>{periodLabel}</span>
            <svg className={cn('w-3 h-3 transition-transform', periodOpen && 'rotate-180')} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          </button>

          {periodOpen && (
            <div className="absolute top-full right-0 mt-1 min-w-[140px] bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg z-50 py-1">
              {PERIODS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => { setPeriod(p.label); setPeriodOpen(false); }}
                  className={cn(
                    'w-full px-3 py-1.5 text-[11px] font-medium text-left transition-colors cursor-pointer',
                    period === p.label
                      ? 'bg-accent/10 text-accent'
                      : 'text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
                  )}
                >
                  {p.label}
                </button>
              ))}
              <div className="h-px bg-[var(--border-primary)] my-1" />
              <button
                onClick={() => { setPeriod('custom'); setPeriodOpen(false); setShowCalendar(true); }}
                className={cn(
                  'w-full px-3 py-1.5 text-[11px] font-medium text-left transition-colors cursor-pointer',
                  period === 'custom'
                    ? 'bg-accent/10 text-accent'
                    : 'text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
                )}
              >
                Custom range
              </button>
            </div>
          )}

          {/* Custom date range calendar */}
          {showCalendar && (
            <DateRangeCalendar
              className="absolute top-full right-0 mt-1 z-50"
              initialStart={customRange.start || undefined}
              initialEnd={customRange.end || undefined}
              onChange={(start, end) => { setCustomRange({ start, end }); setShowCalendar(false); }}
              onClose={() => setShowCalendar(false)}
            />
          )}
        </div>
      </div>

      {/* Hover display */}
      <div className="flex justify-between mb-2">
        <div>
          {tab === 'value' ? (
            <span className="text-xl font-bold font-mono tabular-nums">
              {formatCurrency(displayValue || 0, currency)}
            </span>
          ) : (
            <span className={`text-xl font-bold font-mono tabular-nums ${getChangeColor(displayPct)}`}>
              {displayPct != null ? formatPercent(displayPct) : '--'}
            </span>
          )}
          <div className="flex items-baseline gap-2 mt-0.5">
            {tab === 'value' && displayChange != null && (
              <span className={`text-sm font-semibold font-mono ${getChangeColor(displayChange)}`}>
                {displayChange >= 0 ? '+' : ''}{formatCurrency(displayChange, currency)}
                {displayPct != null && ` (${formatPercent(displayPct)})`}
              </span>
            )}
            {tab === 'perf' && (hoverData?.benchPct ?? benchEndPct) != null && (
              <span className="text-sm font-semibold font-mono" style={{ color: 'var(--warning)' }}>
                vs S&P {formatPercent(hoverData?.benchPct ?? benchEndPct)}
              </span>
            )}
            <span className="text-[11px] text-[var(--text-tertiary)]">{displayDate}</span>
          </div>
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
                  setHoverData({ value: d.value, change, pct, date: formatDate(d.date, { format: 'medium' }) });
                }
              }}
              onMouseLeave={() => setHoverData(null)}
              margin={{ top: 4, right: 0, bottom: 0, left: 4 }}
            >
              <defs>
                <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={colors.accent} stopOpacity={0.18} />
                  <stop offset="100%" stopColor={colors.accent} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="label"
                ticks={xTicks}
                tickFormatter={formatTick}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: colors.textTertiary }}
                interval={xTicks ? 0 : 'preserveStartEnd'}
                minTickGap={60}
              />
              <YAxis
                orientation="right"
                domain={['auto', 'auto']}
                tickFormatter={(v) => formatCurrency(v, currency, { compact: true })}
                tick={{ fontSize: 10, fill: colors.textTertiary }}
                axisLine={false}
                tickLine={false}
                width={55}
              />
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
                  setHoverData({ pct: d.performance, benchPct: d.benchmark, date: formatDate(d.date, { format: 'medium' }) });
                }
              }}
              onMouseLeave={() => setHoverData(null)}
              margin={{ top: 4, right: 0, bottom: 0, left: 4 }}
            >
              <XAxis
                dataKey="label"
                ticks={xTicks}
                tickFormatter={formatTick}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: colors.textTertiary }}
                interval={xTicks ? 0 : 'preserveStartEnd'}
                minTickGap={60}
              />
              <YAxis
                orientation="right"
                domain={['auto', 'auto']}
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 10, fill: colors.textTertiary }}
                axisLine={false}
                tickLine={false}
                width={45}
              />
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
                activeDot={{ r: 4, fill: 'var(--warning)', stroke: colors.bgSecondary, strokeWidth: 2 }}
                connectNulls
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
