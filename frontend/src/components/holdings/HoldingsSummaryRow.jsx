import { cn, formatCurrency, formatPercent, getChangeColor, getChangeIndicator } from '../../lib';

const LABEL_CLASS = 'block text-[10px] text-[var(--text-faint)] uppercase tracking-wide font-medium mb-0.5';

function SummaryCell({ label, children }) {
  return (
    <td className="py-2 px-2 text-right">
      <span className={LABEL_CLASS}>{label}</span>
      {children}
    </td>
  );
}

export function HoldingsSummaryRow({ costBasis, marketValue, pnl, pnlPct, currency }) {
  const pnlColor = getChangeColor(pnl);

  return (
    <tr className="border-t-2 border-[var(--border-primary)] bg-[var(--bg-tertiary)]">
      <td colSpan={6} className="py-2 px-2">
        <span className="text-xs font-semibold text-[var(--text-tertiary)] uppercase tracking-wide">
          All Holdings
        </span>
      </td>

      <td className="py-2 px-2" />
      <td className="py-2 px-2" />

      <SummaryCell label="Cost Basis">
        <span className="font-mono tabular-nums text-[13px] font-bold text-[var(--text-secondary)]">
          {formatCurrency(costBasis, currency)}
        </span>
      </SummaryCell>

      <SummaryCell label="Market Value">
        <span className="font-mono tabular-nums text-[13px] font-bold text-[var(--text-primary)]">
          {formatCurrency(marketValue, currency)}
        </span>
      </SummaryCell>

      <SummaryCell label="Total P&L">
        <span className={cn('font-mono tabular-nums text-[13px] font-bold', pnlColor)}>
          {getChangeIndicator(pnl)} {formatCurrency(Math.abs(pnl), currency)}
          {pnlPct != null && ` (${formatPercent(pnlPct)})`}
        </span>
      </SummaryCell>

      <td className="py-2 px-2" />
    </tr>
  );
}
