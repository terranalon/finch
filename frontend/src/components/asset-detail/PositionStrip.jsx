import React, { useState } from 'react';
import { formatCurrency, formatPercent, formatNumber, cn } from '../../lib';

export default function PositionStrip({ position, asset }) {
  const [expanded, setExpanded] = useState(false);

  if (!position) return null;

  const isCrypto = asset.asset_class === 'Crypto';
  const quantityDecimals = isCrypto ? 4 : 0;
  const qty = position.total_quantity;
  const unitLabel = isCrypto ? asset.symbol : (qty === 1 ? 'share' : 'shares');

  const isPositive = position.total_return >= 0;
  const accentClass = isPositive ? 'border-positive' : 'border-negative';
  const returnColorClass = isPositive ? 'text-positive' : 'text-negative';

  const hasMultipleAccounts = position.accounts && position.accounts.length > 1;

  return (
    <div className={cn('bg-[var(--bg-secondary)] border border-[var(--border-primary)] border-t-2 rounded-lg mb-6', accentClass)}>
      {/* Main strip row */}
      <div className="flex items-center justify-between px-4 py-3 gap-4">
        <div className="flex items-center gap-6 flex-wrap flex-1">
          {/* Quantity */}
          <div className="flex flex-col">
            <span className="text-xs text-[var(--text-secondary)]">Quantity</span>
            <span className="text-sm font-semibold text-[var(--text-primary)]">
              <span>{formatNumber(qty, { decimals: quantityDecimals })}</span>
              {' '}
              <span className="text-xs font-normal text-[var(--text-secondary)]">{unitLabel}</span>
            </span>
          </div>
          {/* Avg Cost */}
          <div className="flex flex-col">
            <span className="text-xs text-[var(--text-secondary)]">Avg Cost</span>
            <span className="text-sm font-semibold text-[var(--text-primary)]">
              {formatCurrency(position.avg_cost_per_unit, asset.currency)}
            </span>
          </div>
          {/* Market Value */}
          <div className="flex flex-col">
            <span className="text-xs text-[var(--text-secondary)]">Market Value</span>
            <span className="text-sm font-semibold text-[var(--text-primary)]">
              {formatCurrency(position.current_value, asset.currency)}
            </span>
          </div>
          {/* Total Return */}
          <div className="flex flex-col">
            <span className="text-xs text-[var(--text-secondary)]">Total Return</span>
            <span className={cn('text-sm font-semibold', returnColorClass)}>
              {formatCurrency(position.total_return, asset.currency)}{' '}
              <span className="text-xs font-normal">
                ({formatPercent(position.total_return_percent)})
              </span>
            </span>
          </div>
        </div>

        {/* Expand chevron for multi-account */}
        {hasMultipleAccounts && (
          <button
            onClick={() => setExpanded((prev) => !prev)}
            aria-label={expanded ? 'Collapse account breakdown' : 'Expand account breakdown'}
            className="flex-shrink-0 p-1.5 rounded hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] transition-colors"
          >
            <svg
              className={cn('size-4 transition-transform', expanded ? 'rotate-180' : '')}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        )}
      </div>

      {/* Expandable per-account breakdown */}
      {expanded && hasMultipleAccounts && (
        <div className="border-t border-[var(--border-primary)] px-4 pb-3 overflow-x-auto">
          <table className="w-full text-sm mt-2">
            <thead>
              <tr className="text-xs text-[var(--text-secondary)]">
                <th className="text-left pb-2 font-medium">Account</th>
                <th className="text-right pb-2 font-medium">Quantity</th>
                <th className="text-right pb-2 font-medium">Avg Cost</th>
                <th className="text-right pb-2 font-medium">Market Value</th>
                <th className="text-right pb-2 font-medium">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {position.accounts.map((acc) => {
                const accPositive = acc.return_value >= 0;
                return (
                  <tr key={acc.name} className="border-t border-[var(--border-primary)]">
                    <td className="py-2 text-[var(--text-primary)] font-medium">{acc.name}</td>
                    <td className="py-2 text-right text-[var(--text-secondary)]">
                      {formatNumber(acc.quantity, { decimals: quantityDecimals })}
                    </td>
                    <td className="py-2 text-right text-[var(--text-secondary)]">
                      {formatCurrency(acc.avg_cost, asset.currency)}
                    </td>
                    <td className="py-2 text-right text-[var(--text-secondary)]">
                      {formatCurrency(acc.current_value, asset.currency)}
                    </td>
                    <td className={cn('py-2 text-right font-medium', accPositive ? 'text-positive' : 'text-negative')}>
                      {formatCurrency(acc.return_value, asset.currency)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
