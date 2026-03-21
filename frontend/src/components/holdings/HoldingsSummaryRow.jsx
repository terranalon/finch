import { cn, formatCurrency, formatPercent, getChangeColor, getChangeIndicator } from '../../lib';

export function HoldingsSummaryRow({ costBasis, marketValue, pnl, pnlPct, currency }) {
  const pnlColor = getChangeColor(pnl);

  return (
    <tr className="border-t-2 border-[var(--border-primary)] bg-[var(--bg-tertiary)]">
      {/* Spans expand + star + icon + symbol + name + price = 6 columns */}
      <td colSpan={6} className="table-cell py-2.5">
        <span className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wide">
          All Holdings
        </span>
      </td>

      {/* Qty - empty */}
      <td className="table-cell" />

      {/* Avg Cost - empty */}
      <td className="table-cell" />

      {/* Cost Basis */}
      <td className="table-cell text-right">
        <span className="block text-[10px] text-[var(--text-faint)] uppercase tracking-wide font-medium mb-0.5">
          Cost Basis
        </span>
        <span className="font-mono tabular-nums text-[13px] font-bold text-[var(--text-secondary)]">
          {formatCurrency(costBasis, currency)}
        </span>
      </td>

      {/* Market Value */}
      <td className="table-cell text-right">
        <span className="block text-[10px] text-[var(--text-faint)] uppercase tracking-wide font-medium mb-0.5">
          Market Value
        </span>
        <span className="font-mono tabular-nums text-[13px] font-bold text-[var(--text-primary)]">
          {formatCurrency(marketValue, currency)}
        </span>
      </td>

      {/* Total P&L */}
      <td className="table-cell text-right">
        <span className="block text-[10px] text-[var(--text-faint)] uppercase tracking-wide font-medium mb-0.5">
          Total P&L
        </span>
        <span className={cn('font-mono tabular-nums text-[13px] font-bold', pnlColor)}>
          {getChangeIndicator(pnl)} {formatCurrency(Math.abs(pnl), currency)}
          {pnlPct != null && ` (${formatPercent(pnlPct)})`}
        </span>
      </td>

      {/* Accts - empty */}
      <td className="table-cell" />
    </tr>
  );
}
