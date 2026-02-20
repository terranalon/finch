import { formatCurrency, formatPercent, formatDate } from '../../lib';

function MetricCell({ label, value }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-[var(--text-secondary)] mb-0.5">{label}</span>
      <span className="text-sm font-semibold text-[var(--text-primary)]">{value}</span>
    </div>
  );
}

export default function AssetDividend({ asset, position }) {
  const metrics = asset.daily_metrics || {};

  const annualIncome = position != null
    ? formatCurrency(position.total_quantity * metrics.dividend_rate, asset.currency)
    : '--';

  const yieldOnCost = position != null && position.avg_cost_per_unit
    ? formatPercent((metrics.dividend_rate / position.avg_cost_per_unit) * 100)
    : '--';

  const perShareYear = metrics.dividend_rate != null
    ? formatCurrency(metrics.dividend_rate, asset.currency)
    : '--';

  const currentYield = metrics.dividend_yield != null
    ? formatPercent(metrics.dividend_yield * 100)
    : '--';

  const payoutRatio = metrics.payout_ratio != null
    ? formatPercent(metrics.payout_ratio * 100)
    : '--';

  const exDivDate = asset.ex_dividend_date
    ? formatDate(asset.ex_dividend_date)
    : '--';

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg mb-6">
      <div className="px-4 py-3 border-b border-[var(--border-primary)]">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Dividend Income</h3>
      </div>
      <div className="p-4">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <MetricCell label="Annual Income" value={annualIncome} />
          <MetricCell label="Yield on Cost" value={yieldOnCost} />
          <MetricCell label="Per Share / Year" value={perShareYear} />
          <MetricCell label="Current Yield" value={currentYield} />
        </div>

        <div className="border-t border-[var(--border-primary)] pt-3 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-[var(--text-secondary)]">Next Ex-Dividend</span>
            <span className="text-[var(--text-primary)] font-medium">{exDivDate}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-[var(--text-secondary)]">Payout Ratio</span>
            <span className="text-[var(--text-primary)] font-medium">{payoutRatio}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
