import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { useChartColors } from '../../hooks/useChartColors';
import { formatCurrency, cn } from '../../lib';

const PERIODS = [
  { label: '1D', value: '1d' },
  { label: '5D', value: '5d' },
  { label: '1M', value: '1mo' },
  { label: '3M', value: '3mo' },
  { label: '6M', value: '6mo' },
  { label: '1Y', value: '1y' },
];

function CustomTooltip({ active, payload, label, currency }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg shadow-lg p-3">
      <p className="text-xs text-[var(--text-secondary)]">{label}</p>
      <p className="text-sm font-bold text-[var(--text-primary)] font-mono mt-1">
        {formatCurrency(payload[0].value, currency)}
      </p>
    </div>
  );
}

export default function AssetChart({ priceHistory, activePeriod, onPeriodChange, currency }) {
  const chartColors = useChartColors();
  const data = priceHistory?.data || [];
  const isPositive = data.length >= 2 && data[data.length - 1].close >= data[0].close;
  const lineColor = isPositive ? chartColors.positive : chartColors.negative;
  const gradientId = `assetGradient-${isPositive ? 'pos' : 'neg'}`;

  if (data.length === 0) {
    return (
      <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg p-6 mb-6">
        <p className="text-sm text-[var(--text-secondary)] text-center">No price history available</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg p-4 mb-6">
      <ResponsiveContainer width="100%" height={340}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={lineColor} stopOpacity={0.25} />
              <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={chartColors.borderPrimary} />
          <XAxis
            dataKey="date"
            stroke={chartColors.textTertiary}
            tick={{ fontSize: 11 }}
            minTickGap={40}
          />
          <YAxis
            stroke={chartColors.textTertiary}
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => formatCurrency(v, currency, { compact: true })}
            domain={['auto', 'auto']}
            width={70}
          />
          <Tooltip content={<CustomTooltip currency={currency} />} />
          <Area
            type="monotone"
            dataKey="close"
            stroke={lineColor}
            strokeWidth={2}
            fillOpacity={1}
            fill={`url(#${gradientId})`}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Period selector */}
      <div className="flex justify-center gap-1 mt-3">
        {PERIODS.map(({ label, value }) => (
          <button
            key={value}
            onClick={() => onPeriodChange(value)}
            className={cn(
              'px-3 py-1 rounded text-xs font-medium transition-colors',
              activePeriod === value
                ? 'bg-accent text-white'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
            )}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
