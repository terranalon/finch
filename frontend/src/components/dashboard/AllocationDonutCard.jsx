import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { formatCurrency, ASSET_COLORS } from '../../lib';
import { Skeleton } from '../ui';

const FALLBACK_COLOR = '#64748B';

export function AllocationDonutCard({ allocation, totalValue, currency, loading }) {
  if (loading) {
    return <div className="card"><Skeleton className="h-[200px] w-full" /></div>;
  }

  if (!allocation || allocation.length === 0) {
    return (
      <div className="card">
        <span className="text-[13px] font-semibold mb-3 block">Allocation</span>
        <div className="text-center py-6 text-[var(--text-tertiary)] text-xs">No allocation data</div>
      </div>
    );
  }

  const total = allocation.reduce((s, a) => s + (a.total_value || 0), 0);
  const chartData = allocation.map((a) => ({
    name: a.asset_class,
    value: a.total_value || 0,
    pct: total > 0 ? ((a.total_value || 0) / total) * 100 : 0,
    color: ASSET_COLORS[a.asset_class] || FALLBACK_COLOR,
  }));

  return (
    <div className="card">
      <span className="text-[13px] font-semibold mb-3 block">Allocation</span>

      <div className="relative h-[130px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={38}
              outerRadius={58}
              dataKey="value"
              stroke="var(--bg-secondary)"
              strokeWidth={2}
            >
              {chartData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span className="text-[13px] font-bold font-mono tabular-nums">
            {formatCurrency(totalValue || 0, currency)}
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-2">
        {chartData.map((entry) => (
          <div key={entry.name} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: entry.color }}
            />
            <span className="text-[11px] text-[var(--text-secondary)]">
              {entry.name}
            </span>
            <span className="text-[11px] font-mono tabular-nums text-[var(--text-tertiary)]">
              {entry.pct.toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
