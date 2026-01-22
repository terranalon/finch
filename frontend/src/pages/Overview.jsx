/**
 * Overview Page - Finch Redesign
 *
 * Purpose: Answer "How am I doing?" in one glance
 *
 * Wired up to real API endpoints:
 * - /api/dashboard/summary - portfolio totals, allocation, accounts, historical
 * - /api/positions - daily movers (sorted by day_change_pct)
 */

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart, ReferenceLine } from 'recharts';
import { cn, formatCurrency, formatPercent, getChangeColor, getChangeIndicator, api } from '../lib';
import { useCurrency, usePortfolio } from '../contexts';
import { PageContainer } from '../components/layout';
import { Card, CardHeader, CardTitle, CardContent, Skeleton } from '../components/ui';

/**
 * Calculate Time-Weighted Return using Modified Dietz method
 * This excludes the effect of cash flows (deposits/withdrawals) from returns
 *
 * @param {Array} snapshots - Array of {date, value} objects, sorted by date ascending
 * @param {Array} cashFlows - Array of {date, amount} objects (positive = deposit, negative = withdrawal)
 * @returns {Array} Array of {date, value, performance} objects
 */
function calculateTWR(snapshots, cashFlows) {
  if (!snapshots || snapshots.length === 0) return [];

  const result = [];
  const startDate = new Date(snapshots[0].date);
  const startValue = snapshots[0].value;

  // Create a map of cash flows by date for quick lookup
  const cashFlowMap = new Map();
  if (cashFlows && cashFlows.length > 0) {
    cashFlows.forEach((cf) => {
      const dateKey = cf.date.split('T')[0]; // Normalize to YYYY-MM-DD
      const existing = cashFlowMap.get(dateKey) || 0;
      cashFlowMap.set(dateKey, existing + cf.amount);
    });
  }

  // For each snapshot, calculate cumulative TWR from start
  snapshots.forEach((snapshot, index) => {
    const currentDate = new Date(snapshot.date);
    const currentValue = snapshot.value;

    if (index === 0) {
      // First point is always 0% (baseline)
      result.push({ ...snapshot, performance: 0 });
      return;
    }

    // Calculate total days in period
    const totalDays = Math.max(1, (currentDate - startDate) / (1000 * 60 * 60 * 24));

    // Sum all cash flows and their weighted contributions
    let totalCashFlow = 0;
    let weightedCashFlow = 0;

    cashFlowMap.forEach((amount, dateStr) => {
      const cfDate = new Date(dateStr);
      if (cfDate > startDate && cfDate <= currentDate) {
        totalCashFlow += amount;
        // Weight = proportion of period remaining after cash flow
        const daysFromStart = (cfDate - startDate) / (1000 * 60 * 60 * 24);
        const weight = (totalDays - daysFromStart) / totalDays;
        weightedCashFlow += amount * weight;
      }
    });

    // Modified Dietz formula:
    // Return = (Ending Value - Beginning Value - Cash Flows) / (Beginning Value + Weighted Cash Flows)
    const denominator = startValue + weightedCashFlow;
    let performance = 0;

    if (denominator > 0) {
      performance = ((currentValue - startValue - totalCashFlow) / denominator) * 100;
    }

    result.push({ ...snapshot, performance });
  });

  return result;
}

// ============================================
// COMPONENTS
// ============================================

/**
 * Mini sparkline chart for the hero section
 */
function SparkLine({ data, positive = true }) {
  if (!data || data.length === 0) {
    return <div className="h-12 w-64" />;
  }

  return (
    <div className="h-12 w-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="sparklineGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={positive ? '#059669' : '#DC2626'} stopOpacity={0.3} />
              <stop offset="95%" stopColor={positive ? '#059669' : '#DC2626'} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="value"
            stroke={positive ? '#059669' : '#DC2626'}
            strokeWidth={2}
            fill="url(#sparklineGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Hero section with total value and day change
 */
function HeroSection({ data, sparklineData, currency, loading }) {
  if (loading) {
    return (
      <div className="text-center py-8">
        <Skeleton className="h-4 w-32 mx-auto mb-2" />
        <Skeleton className="h-12 w-64 mx-auto mb-3" />
        <Skeleton className="h-6 w-48 mx-auto mb-4" />
        <Skeleton className="h-12 w-64 mx-auto" />
      </div>
    );
  }

  const isPositive = (data?.dayChangePct || 0) >= 0;
  const indicator = getChangeIndicator(data?.dayChangePct || 0);
  const colorClass = getChangeColor(data?.dayChangePct || 0);

  return (
    <div className="text-center py-8">
      <p className="text-sm text-[var(--text-secondary)] mb-2">Total Portfolio Value</p>
      <h1 className="text-4xl font-bold text-[var(--text-primary)] tabular-nums font-mono">
        {formatCurrency(data?.totalValue || 0, currency)}
      </h1>
      {data?.dayChange !== null && data?.dayChange !== undefined ? (
        <div className={cn('mt-3 flex items-center justify-center gap-2', colorClass)}>
          <span className="text-lg font-medium tabular-nums">
            {indicator} {formatCurrency(Math.abs(data.dayChange), currency, { compact: true })} ({formatPercent(data.dayChangePct)})
          </span>
          <span className="text-sm text-[var(--text-tertiary)]">today</span>
        </div>
      ) : (
        <div className="mt-3 text-sm text-[var(--text-tertiary)]">
          Day change unavailable
        </div>
      )}
      <div className="mt-4 flex justify-center">
        <SparkLine data={sparklineData} positive={isPositive} />
      </div>
    </div>
  );
}

/**
 * Get day name from a date string (e.g., "Friday" from "2026-01-16")
 */
function getDayName(dateStr) {
  if (!dateStr) return null;
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', { weekday: 'long' });
}

/**
 * Check if a date string matches today
 */
function isToday(dateStr) {
  if (!dateStr) return false;
  const date = new Date(dateStr + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date.getTime() === today.getTime();
}

/**
 * Single mover card - compact card with colored accent
 */
function MoverCard({ mover, isGainer, showDateBadge = false }) {
  const navigate = useNavigate();
  const indicator = getChangeIndicator(mover.dayChangePct);

  // Calculate day change in native currency terms
  const dayChangeNative = mover.totalMarketValueNative && mover.dayChangePct
    ? (mover.totalMarketValueNative * mover.dayChangePct) / (100 + mover.dayChangePct)
    : 0;

  // Show date badge only if showDateBadge is true and it's not today
  const dateBadge = showDateBadge && mover.dayChangeDate && !isToday(mover.dayChangeDate)
    ? getDayName(mover.dayChangeDate)
    : null;

  return (
    <div
      onClick={() => navigate(`/holdings?symbol=${encodeURIComponent(mover.symbol)}`)}
      className={cn(
        'flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all',
        'border-l-4',
        isGainer
          ? 'border-l-positive bg-positive/5 hover:bg-positive/10'
          : 'border-l-negative bg-negative/5 hover:bg-negative/10'
      )}
    >
      {/* Symbol badge */}
      <div className={cn(
        'flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center font-bold text-sm',
        isGainer
          ? 'bg-positive/10 text-positive'
          : 'bg-negative/10 text-negative'
      )}>
        {mover.symbol.slice(0, 4)}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-[var(--text-primary)] truncate">{mover.name}</p>
        <div className={cn(
          'text-sm font-semibold tabular-nums',
          isGainer ? 'text-positive' : 'text-negative'
        )}>
          {indicator} {formatPercent(mover.dayChangePct)}
          <span className="font-normal text-[var(--text-tertiary)] ml-2">
            ({indicator}{formatCurrency(Math.abs(dayChangeNative), mover.currency, { compact: true })})
          </span>
        </div>
        {dateBadge && (
          <p className="text-xs text-[var(--text-tertiary)]">{dateBadge}</p>
        )}
      </div>

      {/* Current price + price change - right aligned */}
      {mover.currentPrice && (
        <div className="flex-shrink-0 text-right">
          <p className="font-medium text-[var(--text-primary)] tabular-nums">
            {formatCurrency(mover.currentPrice, mover.currency)}
          </p>
          {mover.dayChange != null && (
            <p className={cn(
              'text-sm tabular-nums',
              isGainer ? 'text-positive' : 'text-negative'
            )}>
              {indicator}{formatCurrency(Math.abs(mover.dayChange), mover.currency)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Generate section title based on the day change reference date.
 * Shows "Today's Movers" if date matches today, otherwise "Friday's Movers" etc.
 */
function getMoversTitle(dayChangeDate) {
  if (!dayChangeDate) return 'Your Daily Movers';

  const referenceDate = new Date(dayChangeDate + 'T00:00:00'); // Parse as local date
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (referenceDate.getTime() === today.getTime()) {
    return "Today's Movers";
  }

  const dayName = referenceDate.toLocaleDateString('en-US', { weekday: 'long' });
  return `${dayName}'s Movers`;
}

/**
 * Your Daily Movers - top gainers and losers from user's holdings
 */
function DailyMoversSection({ movers, currency, loading, hasMixedDates, commonDayChangeDate }) {
  const navigate = useNavigate();

  // Determine section title based on date scenario
  const sectionTitle = useMemo(() => {
    if (hasMixedDates) {
      return 'Your Daily Movers';
    }
    return getMoversTitle(commonDayChangeDate);
  }, [hasMixedDates, commonDayChangeDate]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{sectionTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <Skeleton className="h-4 w-24 mb-4" />
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            </div>
            <div>
              <Skeleton className="h-4 w-24 mb-4" />
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!movers || movers.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{sectionTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6">
            <p className="text-[var(--text-secondary)]">
              No holdings to display
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Split into gainers and losers (only those with day change data)
  const withDayChange = movers.filter(m => m.dayChangePct !== null && m.dayChangePct !== undefined);
  const gainers = withDayChange.filter(m => m.dayChangePct > 0).sort((a, b) => b.dayChangePct - a.dayChangePct).slice(0, 3);
  const losers = withDayChange.filter(m => m.dayChangePct < 0).sort((a, b) => a.dayChangePct - b.dayChangePct).slice(0, 3);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{sectionTitle}</CardTitle>
          <button
            onClick={() => navigate('/holdings')}
            className="text-sm text-[var(--text-secondary)] hover:text-accent transition-colors cursor-pointer"
          >
            View all
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Gainers */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-positive" />
              <p className="text-sm font-medium text-[var(--text-secondary)]">Top Gainers</p>
            </div>
            <div className="space-y-3">
              {gainers.length > 0 ? (
                gainers.map((mover) => (
                  <MoverCard key={mover.symbol} mover={mover} isGainer showDateBadge={hasMixedDates} />
                ))
              ) : (
                <p className="text-sm text-[var(--text-tertiary)] py-4">No gainers today</p>
              )}
            </div>
          </div>

          {/* Losers */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-negative" />
              <p className="text-sm font-medium text-[var(--text-secondary)]">Top Losers</p>
            </div>
            <div className="space-y-3">
              {losers.length > 0 ? (
                losers.map((mover) => (
                  <MoverCard key={mover.symbol} mover={mover} isGainer={false} showDateBadge={hasMixedDates} />
                ))
              ) : (
                <p className="text-sm text-[var(--text-tertiary)] py-4">No losers today</p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Time range configuration: maps UI labels to days and API periods
const TIME_RANGE_CONFIG = {
  '1W': { days: 7, apiPeriod: '1mo' },
  '1M': { days: 30, apiPeriod: '1mo' },
  '3M': { days: 90, apiPeriod: '3mo' },
  '1Y': { days: 365, apiPeriod: '1y' },
  'ALL': { days: Infinity, apiPeriod: 'max' },
};
const TIME_RANGES = Object.keys(TIME_RANGE_CONFIG);

// Chart styling constants
const CHART_COLORS = {
  positive: '#10B981',
  negative: '#EF4444',
  value: '#2563EB',
  benchmark: '#6B7280',
};

// Format date for chart X-axis (M/D format)
function formatChartDate(value) {
  const date = new Date(value);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

/**
 * Chart section with Performance/Value toggle and time range
 * Shows value at the top that updates on hover
 */
function HistoricalChartSection({ valueData, cashFlows, currency, loading }) {
  const [chartMode, setChartMode] = useState('value');
  const [timeRange, setTimeRange] = useState('1M');
  const [hoveredData, setHoveredData] = useState(null);
  const [showBenchmark, setShowBenchmark] = useState(true);
  const [benchmarkData, setBenchmarkData] = useState([]);

  const isPerformance = chartMode === 'performance';
  const rangeConfig = TIME_RANGE_CONFIG[timeRange] || TIME_RANGE_CONFIG['1M'];

  // Fetch benchmark data when time range changes
  useEffect(() => {
    async function fetchBenchmark() {
      try {
        const res = await api(`/dashboard/benchmark?period=${rangeConfig.apiPeriod}&symbol=SPY`);
        if (res.ok) {
          const data = await res.json();
          setBenchmarkData(data.data || []);
        }
      } catch (err) {
        console.error('Error fetching benchmark:', err);
        setBenchmarkData([]);
      }
    }
    fetchBenchmark();
  }, [rangeConfig.apiPeriod]);

  // Filter data based on time range
  const filteredData = useMemo(() => {
    if (!valueData || valueData.length === 0) return [];
    if (rangeConfig.days === Infinity) return valueData;
    return valueData.slice(-rangeConfig.days);
  }, [valueData, rangeConfig.days]);

  // Calculate performance data using TWR (excludes deposits/withdrawals)
  const performanceData = useMemo(() => {
    if (!filteredData || filteredData.length === 0) return [];
    return calculateTWR(filteredData, cashFlows || []).map(point => ({
      ...point,
      portfolio: point.performance,
      sp500: null,
    }));
  }, [filteredData, cashFlows]);

  // Extract latest values for display
  const hasData = filteredData.length > 0;
  const baseValue = hasData ? filteredData[0].value : 0;
  const latestValue = hasData ? filteredData[filteredData.length - 1].value : 0;
  const latestPerformance = performanceData.length > 0 ? performanceData[performanceData.length - 1].portfolio : 0;
  const latestSP500 = benchmarkData.length > 0 ? benchmarkData[benchmarkData.length - 1].performance : null;
  const latestDate = hasData ? filteredData[filteredData.length - 1].date : null;

  // Display values - use hovered data if available, otherwise latest
  const displayValue = hoveredData?.value ?? latestValue;
  const displayPerformance = hoveredData?.portfolio ?? latestPerformance;
  const displaySP500 = hoveredData?.sp500 ?? latestSP500;
  const displayDate = hoveredData?.date ?? latestDate;

  // Calculate value change for display (includes deposits/withdrawals)
  const valueChange = displayValue - baseValue;
  const valueChangePct = baseValue > 0 ? ((displayValue - baseValue) / baseValue) * 100 : 0;

  // Create a map of benchmark data by date for quick lookup
  // Also create a sorted array for finding closest previous date (for weekends/holidays)
  const { benchmarkMap, benchmarkDates } = useMemo(() => {
    const map = new Map();
    const dates = [];
    benchmarkData.forEach(b => {
      map.set(b.date, b.performance);
      dates.push(b.date);
    });
    dates.sort();
    return { benchmarkMap: map, benchmarkDates: dates };
  }, [benchmarkData]);

  // Helper to get benchmark value for a date, using closest available trading day
  const getBenchmarkValue = (date) => {
    if (benchmarkMap.has(date)) {
      return benchmarkMap.get(date);
    }
    // Find the closest previous date with data (for weekends/holidays)
    for (let i = benchmarkDates.length - 1; i >= 0; i--) {
      if (benchmarkDates[i] < date) {
        return benchmarkMap.get(benchmarkDates[i]);
      }
    }
    // If no previous date found, use the first available date (for start of range)
    if (benchmarkDates.length > 0) {
      return benchmarkMap.get(benchmarkDates[0]);
    }
    return null;
  };

  // Create performance data with separate positive/negative keys for coloring + benchmark
  const performanceChartData = useMemo(() => {
    if (!performanceData || performanceData.length < 2) return [];

    const result = [];

    for (let i = 0; i < performanceData.length; i++) {
      const point = performanceData[i];
      const prevPoint = i > 0 ? performanceData[i - 1] : null;

      // Insert interpolated point at zero crossing for smooth color transition
      const crossesZero = prevPoint && (prevPoint.portfolio < 0) !== (point.portfolio < 0);
      if (crossesZero) {
        const ratio = Math.abs(prevPoint.portfolio) / (Math.abs(prevPoint.portfolio) + Math.abs(point.portfolio));
        const crossTime = new Date(prevPoint.date).getTime() + ratio * (new Date(point.date).getTime() - new Date(prevPoint.date).getTime());
        const crossDate = new Date(crossTime).toISOString().split('T')[0];
        result.push({
          date: crossDate,
          portfolio: 0,
          positive: 0,
          negative: 0,
          sp500: getBenchmarkValue(crossDate),
        });
      }

      // Add point with positive/negative split for dual-color rendering
      const isPositive = point.portfolio >= 0;
      result.push({
        ...point,
        positive: isPositive ? point.portfolio : null,
        negative: isPositive ? null : point.portfolio,
        sp500: getBenchmarkValue(point.date),
      });
    }

    return result;
  }, [performanceData, benchmarkMap, benchmarkDates]);

  // Update header display on hover instead of showing tooltip
  function handleMouseMove(state) {
    if (state?.activePayload?.[0]?.payload) {
      setHoveredData(state.activePayload[0].payload);
    }
  }

  function handleMouseLeave() {
    setHoveredData(null);
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-48 mb-4" />
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            {/* Value/Performance Toggle */}
            <div className="flex bg-[var(--bg-tertiary)] rounded-md p-0.5">
              <button
                onClick={() => setChartMode('value')}
                className={cn(
                  'px-3 py-1 text-sm rounded transition-colors cursor-pointer',
                  !isPerformance
                    ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                )}
              >
                Value
              </button>
              <button
                onClick={() => setChartMode('performance')}
                className={cn(
                  'px-3 py-1 text-sm rounded transition-colors cursor-pointer',
                  isPerformance
                    ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                )}
              >
                Performance
              </button>
            </div>
            {/* Benchmark Toggle - only in performance mode */}
            {isPerformance && (
              <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)] cursor-pointer ml-3">
                <input
                  type="checkbox"
                  checked={showBenchmark}
                  onChange={(e) => setShowBenchmark(e.target.checked)}
                  className="w-4 h-4 rounded border-[var(--border-primary)] text-accent focus:ring-accent cursor-pointer"
                />
                <span className="flex items-center gap-1">
                  <span className="w-4 h-0.5 bg-gray-500" style={{ borderTop: '2px dashed #6B7280' }} />
                  S&P 500
                </span>
              </label>
            )}
          </div>
          {/* Time Range */}
          <div className="flex gap-1">
            {TIME_RANGES.map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={cn(
                  'px-3 py-1 text-sm rounded-md transition-colors cursor-pointer',
                  timeRange === range
                    ? 'bg-accent text-white'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                )}
              >
                {range}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {filteredData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-[var(--text-tertiary)]">
            No historical data available
          </div>
        ) : (
          <>
            {/* Value display at top - updates on hover */}
            <div className="mb-4">
              <div className="flex items-baseline gap-3">
                {isPerformance ? (
                  <div className="flex items-baseline gap-4">
                    <span className={cn(
                      'text-3xl font-bold tabular-nums font-mono',
                      displayPerformance >= 0 ? 'text-positive' : 'text-negative'
                    )}>
                      {displayPerformance >= 0 ? '+' : ''}{displayPerformance.toFixed(2)}%
                    </span>
                    {showBenchmark && displaySP500 !== null && (
                      <span className="text-lg text-[var(--text-tertiary)] tabular-nums font-mono">
                        <span className="text-sm mr-1">S&P 500:</span>
                        <span className="text-gray-400">
                          {displaySP500 >= 0 ? '+' : ''}{displaySP500.toFixed(2)}%
                        </span>
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col">
                    <span className="text-3xl font-bold text-[var(--text-primary)] tabular-nums font-mono">
                      {formatCurrency(displayValue, currency)}
                    </span>
                    <span className={cn(
                      'text-sm font-medium tabular-nums',
                      valueChange >= 0 ? 'text-positive' : 'text-negative'
                    )}>
                      {valueChange >= 0 ? '+' : ''}{formatCurrency(valueChange, currency, { compact: true })} ({valueChangePct >= 0 ? '+' : ''}{valueChangePct.toFixed(2)}%)
                    </span>
                  </div>
                )}
                {displayDate && (
                  <span className="text-sm text-[var(--text-tertiary)]">
                    {new Date(displayDate).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </span>
                )}
              </div>
            </div>

            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                {isPerformance ? (
                  /* Performance Chart (% returns) with green/red coloring */
                  <LineChart
                    data={performanceChartData}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={handleMouseLeave}
                  >
                    <XAxis
                      dataKey="date"
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
                      axisLine={{ stroke: 'var(--border-primary)' }}
                      tickLine={false}
                      tickFormatter={formatChartDate}
                    />
                    <YAxis
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) => `${value.toFixed(1)}%`}
                    />
                    <Tooltip
                      content={() => null}
                      cursor={{ stroke: 'var(--border-secondary)', strokeWidth: 1 }}
                    />
                    <ReferenceLine y={0} stroke="var(--border-secondary)" strokeDasharray="3 3" />
                    <Line
                      type="monotone"
                      dataKey="positive"
                      stroke={CHART_COLORS.positive}
                      strokeWidth={2}
                      dot={false}
                      connectNulls={false}
                      activeDot={{ r: 4, stroke: CHART_COLORS.positive, strokeWidth: 2, fill: 'white' }}
                      isAnimationActive={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="negative"
                      stroke={CHART_COLORS.negative}
                      strokeWidth={2}
                      dot={false}
                      connectNulls={false}
                      activeDot={{ r: 4, stroke: CHART_COLORS.negative, strokeWidth: 2, fill: 'white' }}
                      isAnimationActive={false}
                    />
                    {showBenchmark && (
                      <Line
                        type="monotone"
                        dataKey="sp500"
                        stroke={CHART_COLORS.benchmark}
                        strokeWidth={1.5}
                        strokeDasharray="4 4"
                        dot={false}
                        connectNulls
                        isAnimationActive={false}
                      />
                    )}
                  </LineChart>
                ) : (
                  <AreaChart
                    data={filteredData}
                    onMouseMove={handleMouseMove}
                    onMouseLeave={handleMouseLeave}
                  >
                    <defs>
                      <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.value} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={CHART_COLORS.value} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="date"
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
                      axisLine={{ stroke: 'var(--border-primary)' }}
                      tickLine={false}
                      tickFormatter={formatChartDate}
                    />
                    <YAxis
                      tick={{ fill: 'var(--text-tertiary)', fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) => {
                        if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                        if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
                        return `$${value}`;
                      }}
                      domain={['dataMin - 5000', 'dataMax + 5000']}
                    />
                    <Tooltip
                      content={() => null}
                      cursor={{ stroke: 'var(--border-secondary)', strokeWidth: 1 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke={CHART_COLORS.value}
                      strokeWidth={2}
                      fill="url(#valueGradient)"
                      activeDot={{ r: 4, stroke: CHART_COLORS.value, strokeWidth: 2, fill: 'white' }}
                    />
                  </AreaChart>
                )}
              </ResponsiveContainer>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Allocation bar (horizontal stacked)
 */
function AllocationSection({ data, currency, loading }) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Allocation</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-4 w-full mb-6" />
          <div className="space-y-3">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Allocation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-[var(--text-secondary)]">
            No allocation data available
          </div>
        </CardContent>
      </Card>
    );
  }

  const total = data.reduce((sum, item) => sum + item.value, 0);

  // Calculate percentages
  const dataWithPercentages = data.map(item => ({
    ...item,
    percentage: total > 0 ? Math.round((item.value / total) * 100) : 0,
  }));

  const colors = {
    'Stock': 'bg-accent',
    'Stocks': 'bg-accent',
    'ETF': 'bg-blue-400',
    'ETFs': 'bg-blue-400',
    'Cash': 'bg-slate-400',
    'Crypto': 'bg-amber-500',
    'MutualFund': 'bg-purple-500',
    'Bond': 'bg-green-500',
    'Other': 'bg-gray-400',
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Allocation</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Stacked bar */}
        <div className="h-4 rounded-full overflow-hidden flex mb-6">
          {dataWithPercentages.map((item) => (
            <div
              key={item.assetClass}
              className={cn(colors[item.assetClass] || 'bg-slate-300')}
              style={{ width: `${item.percentage}%` }}
              title={`${item.assetClass}: ${item.percentage}%`}
            />
          ))}
        </div>

        {/* Legend */}
        <div className="space-y-3">
          {dataWithPercentages.map((item) => (
            <div key={item.assetClass} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn('w-3 h-3 rounded-sm', colors[item.assetClass] || 'bg-slate-300')} />
                <span className="text-[var(--text-secondary)]">{item.assetClass}</span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-[var(--text-tertiary)] tabular-nums">{item.percentage}%</span>
                <span className="font-medium text-[var(--text-primary)] tabular-nums w-28 text-right">
                  {formatCurrency(item.value, currency, { compact: true })}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Accounts list section
 */
function AccountsSection({ accounts, currency, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!accounts || accounts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-[var(--text-secondary)]">
            No accounts found
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Accounts</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {accounts.map((account) => (
            <div
              key={account.id}
              onClick={() => navigate(`/accounts/${account.id}`)}
              className={cn(
                'flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors',
                'hover:bg-[var(--bg-tertiary)]'
              )}
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    'w-2 h-2 rounded-full',
                    account.status === 'connected' ? 'bg-positive' : 'bg-amber-500'
                  )}
                  title={account.status === 'connected' ? 'Connected' : 'Needs attention'}
                />
                <div>
                  <p className="font-medium text-[var(--text-primary)]">{account.name}</p>
                  <p className="text-xs text-[var(--text-tertiary)]">{account.institution}</p>
                </div>
              </div>
              <span className="font-medium text-[var(--text-primary)] tabular-nums">
                {formatCurrency(account.value, currency, { compact: true })}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================
// MAIN PAGE COMPONENT
// ============================================

export default function Overview() {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use portfolio's currency when viewing a specific portfolio, otherwise use global currency
  const currency = portfolioCurrency || globalCurrency;

  // Data states
  const [portfolioData, setPortfolioData] = useState(null);
  const [positions, setPositions] = useState([]);
  const [fullHistoricalData, setFullHistoricalData] = useState([]); // Full portfolio snapshots
  const [cashFlows, setCashFlows] = useState([]); // All cash transactions for TWR

  // Fetch data on mount and when currency/portfolio changes
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      // Build query params - add portfolio_id if a specific portfolio is selected
      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';

      try {
        // Fetch dashboard summary, positions, full snapshots, and cash transactions in parallel
        const [summaryRes, positionsRes, snapshotsRes, cashRes] = await Promise.all([
          api(`/dashboard/summary?display_currency=${currency}${portfolioParam}`),
          api(`/positions?display_currency=${currency}${portfolioParam}`),
          api(`/snapshots/portfolio?limit=2000&display_currency=${currency}${portfolioParam}`),
          api(`/transactions/cash?limit=500&display_currency=${currency}${portfolioParam}`), // All cash transactions, converted to display currency
        ]);

        if (!summaryRes.ok) throw new Error('Failed to fetch dashboard summary');
        if (!positionsRes.ok) throw new Error('Failed to fetch positions');

        const summaryData = await summaryRes.json();
        const positionsData = await positionsRes.json();

        // Process snapshots
        if (snapshotsRes.ok) {
          const snapshotsData = await snapshotsRes.json();
          const chartData = snapshotsData
            .filter((s) => s.date && !isNaN(new Date(s.date).getTime()))
            .map((s) => ({
              date: s.date,
              value: s.value || 0,
            }))
            .sort((a, b) => new Date(a.date) - new Date(b.date));
          setFullHistoricalData(chartData);
        }

        // Process cash transactions for TWR calculation
        if (cashRes.ok) {
          const cashData = await cashRes.json();
          // Transform to {date, amount} format (positive = deposit, negative = withdrawal)
          const flows = cashData.map((tx) => ({
            date: tx.date,
            amount: tx.type === 'Deposit' ? parseFloat(tx.amount) : -parseFloat(tx.amount),
          }));
          setCashFlows(flows);
        }

        setPortfolioData(summaryData);
        setPositions(positionsData);
      } catch (err) {
        console.error('Error fetching overview data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [currency, selectedPortfolioId]);

  // Transform data for components
  const heroData = useMemo(() => {
    if (!portfolioData) return null;
    return {
      totalValue: portfolioData.total_value,
      dayChange: portfolioData.day_change,
      dayChangePct: portfolioData.day_change_pct,
    };
  }, [portfolioData]);

  // Sparkline from historical data (last 30 days)
  const sparklineData = useMemo(() => {
    if (!portfolioData?.historical_performance) return [];
    return portfolioData.historical_performance.map(point => ({
      date: point.date,
      value: point.value,
    }));
  }, [portfolioData]);

  // Daily movers from positions (transformed) with per-asset day change dates
  const { dailyMovers, hasMixedDates, commonDayChangeDate } = useMemo(() => {
    if (!positions || positions.length === 0) {
      return { dailyMovers: [], hasMixedDates: false, commonDayChangeDate: null };
    }

    const movers = positions
      .filter(pos => pos.day_change_pct !== null && pos.day_change_pct !== undefined)
      .map(pos => ({
        symbol: pos.symbol,
        name: pos.name,
        dayChangePct: pos.day_change_pct,
        dayChange: pos.day_change,
        dayChangeDate: pos.day_change_date,
        currentPrice: pos.current_price,
        totalMarketValue: pos.total_market_value,
        totalMarketValueNative: pos.total_market_value_native,
        currency: pos.currency,
      }));

    // Check if all movers have the same day change date
    const uniqueDates = [...new Set(movers.map(m => m.dayChangeDate).filter(Boolean))];
    const hasMixedDates = uniqueDates.length > 1;
    const commonDayChangeDate = uniqueDates.length === 1 ? uniqueDates[0] : null;

    return { dailyMovers: movers, hasMixedDates, commonDayChangeDate };
  }, [positions]);

  // Historical value data for chart - use full snapshots instead of limited dashboard data
  // Append today's live value to ensure chart matches current portfolio value
  const valueHistory = useMemo(() => {
    let data = [];
    if (fullHistoricalData.length > 0) {
      data = [...fullHistoricalData];
    } else if (portfolioData?.historical_performance) {
      // Fallback to dashboard data if snapshots not loaded
      data = portfolioData.historical_performance.map(point => ({
        date: point.date,
        value: point.value,
      }));
    }

    // If we have current portfolio value, ensure today's value is included
    if (portfolioData?.total_value && data.length > 0) {
      const today = new Date().toISOString().split('T')[0];
      const lastDataDate = data[data.length - 1]?.date;

      // If the last data point isn't today, add today's live value
      if (lastDataDate && lastDataDate < today) {
        data.push({
          date: today,
          value: portfolioData.total_value,
        });
      } else if (lastDataDate === today) {
        // Update today's value to match the live calculated value
        data[data.length - 1] = {
          ...data[data.length - 1],
          value: portfolioData.total_value,
        };
      }
    }

    return data;
  }, [fullHistoricalData, portfolioData]);

  // Allocation data
  const allocationData = useMemo(() => {
    if (!portfolioData?.asset_allocation) return [];
    return portfolioData.asset_allocation.map(item => ({
      assetClass: item.asset_class,
      value: item.total_value,
    }));
  }, [portfolioData]);

  // Accounts data
  const accountsData = useMemo(() => {
    if (!portfolioData?.accounts) return [];
    return portfolioData.accounts.map(account => ({
      id: account.id,
      name: account.name,
      institution: account.institution || account.type,
      value: account.value,
      status: 'connected', // Default to connected - could check last sync time
    }));
  }, [portfolioData]);

  if (error) {
    return (
      <PageContainer width="wide">
        <div className="text-center py-12">
          <p className="text-negative mb-4">Error loading overview: {error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer width="wide">
      {/* Hero Section */}
      <HeroSection
        data={heroData}
        sparklineData={sparklineData}
        currency={currency}
        loading={loading}
      />

      {/* Your Daily Movers - Top gainers/losers from holdings */}
      <div className="mb-8">
        <DailyMoversSection
          movers={dailyMovers}
          currency={currency}
          loading={loading}
          hasMixedDates={hasMixedDates}
          commonDayChangeDate={commonDayChangeDate}
        />
      </div>

      {/* Historical Chart - Performance/Value toggle */}
      <div className="mb-8">
        <HistoricalChartSection
          valueData={valueHistory}
          cashFlows={cashFlows}
          currency={currency}
          loading={loading}
        />
      </div>

      {/* Allocation and Accounts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AllocationSection data={allocationData} currency={currency} loading={loading} />
        <AccountsSection accounts={accountsData} currency={currency} loading={loading} />
      </div>
    </PageContainer>
  );
}
