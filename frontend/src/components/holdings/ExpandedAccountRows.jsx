import { cn, formatCurrency, formatPercent, formatNumber, getChangeColor, getChangeIndicator } from '../../lib';

export function ExpandedAccountRows({ accounts, currency, assetClass, colSpan = 12 }) {
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
                  <div>
                    <p className="text-[10px] text-[var(--text-faint)] mb-0.5">Qty</p>
                    <p className="text-[13px] font-mono tabular-nums font-medium text-[var(--text-primary)]">
                      {formatNumber(acct.quantity, { decimals: isCrypto ? 4 : 0 })}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[var(--text-faint)] mb-0.5">Cost Basis</p>
                    <p className="text-[13px] font-mono tabular-nums font-medium text-[var(--text-primary)]">
                      {formatCurrency(acct.cost_basis_native, currency)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-[var(--text-faint)] mb-0.5">Value</p>
                    <p className="text-[13px] font-mono tabular-nums font-medium text-[var(--text-primary)]">
                      {formatCurrency(acct.market_value_native, currency)}
                    </p>
                  </div>
                  <div className="min-w-[80px]">
                    <p className="text-[10px] text-[var(--text-faint)] mb-0.5">P&L</p>
                    <p className={cn('text-[13px] font-mono tabular-nums font-medium', getChangeColor(acct.pnl_native))}>
                      {getChangeIndicator(acct.pnl_native)} {formatPercent(acct.pnl_pct)}
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
