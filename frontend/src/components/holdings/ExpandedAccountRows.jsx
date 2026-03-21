import { cn, formatCurrency, formatPercent, formatNumber, getChangeColor, getChangeIndicator } from '../../lib';

const METRIC_VALUE = 'text-[13px] font-mono tabular-nums font-medium text-[var(--text-primary)]';

function MetricCell({ label, value }) {
  return (
    <div>
      <p className="text-[10px] text-[var(--text-faint)] mb-0.5">{label}</p>
      <p className={METRIC_VALUE}>{value}</p>
    </div>
  );
}

export function ExpandedAccountRows({ accounts, displayCurrency, assetClass, colSpan = 12 }) {
  const isCrypto = assetClass === 'Crypto';

  return (
    <tr>
      <td colSpan={colSpan} className="p-0 bg-[var(--bg-tertiary)]">
        <div className="px-4 py-4" style={{ paddingLeft: '62px' }}>
          <p className="text-xs font-semibold text-[var(--text-tertiary)] mb-2.5 uppercase tracking-wide">
            Account Breakdown
          </p>
          <div className="flex flex-col gap-2">
            {accounts.map((acct) => (
              <div
                key={acct.holding_id}
                className="flex items-center justify-between p-3 px-4 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-primary)] hover:border-[var(--text-faint)] transition-colors"
              >
                <div className="flex flex-col gap-0.5">
                  <span className="text-[13px] font-semibold text-[var(--text-primary)]">
                    {acct.account_name}
                  </span>
                  <span className="text-[11px] text-[var(--text-faint)]">
                    {acct.institution}
                    {acct.account_type && ` \u00B7 ${acct.account_type}`}
                  </span>
                </div>
                <div className="flex items-center gap-6 text-right">
                  <MetricCell
                    label="Qty"
                    value={formatNumber(acct.quantity, { decimals: isCrypto ? 4 : 0 })}
                  />
                  <MetricCell
                    label="Cost Basis"
                    value={formatCurrency(acct.cost_basis, displayCurrency)}
                  />
                  <MetricCell
                    label="Value"
                    value={formatCurrency(acct.market_value, displayCurrency)}
                  />
                  <div className="min-w-[80px]">
                    <p className="text-[10px] text-[var(--text-faint)] mb-0.5">P&L</p>
                    <p className={cn(METRIC_VALUE, getChangeColor(acct.pnl))}>
                      {getChangeIndicator(acct.pnl)} {formatPercent(acct.pnl_pct)}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </td>
    </tr>
  );
}
