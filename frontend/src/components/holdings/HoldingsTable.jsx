import { Fragment } from 'react';
import { cn } from '../../lib';
import { HoldingsRow } from './HoldingsRow';
import { ExpandedAccountRows } from './ExpandedAccountRows';
import { HoldingsSummaryRow } from './HoldingsSummaryRow';

const HEADER_BASE = 'py-[10px] px-2 text-left font-semibold text-[11px] leading-none uppercase tracking-wide text-[var(--text-faint)] border-b border-[var(--border-primary)] whitespace-nowrap';

function SortableHeader({ field, label, sortField, sortDirection, onSort, align = 'left' }) {
  const isActive = sortField === field;
  return (
    <th
      className={cn(
        HEADER_BASE,
        'cursor-pointer hover:text-[var(--text-tertiary)] transition-colors select-none',
        align === 'right' && 'text-right',
        isActive && 'text-[var(--text-secondary)]'
      )}
      onClick={() => onSort(field)}
    >
      <div className={cn('flex items-center gap-1', align === 'right' ? 'justify-end' : 'justify-start')}>
        <span>{label}</span>
        {isActive && (
          <span className="text-accent text-[10px] ml-0.5">
            {sortDirection === 'asc' ? '\u25B2' : '\u25BC'}
          </span>
        )}
      </div>
    </th>
  );
}

export function HoldingsTable({
  positions,
  expandedRows,
  sortField,
  sortDirection,
  onSort,
  onToggleExpand,
  onRowClick,
  onToggleFavorite,
  totals,
  currency,
  emptyMessage,
  onClearFilters,
}) {
  const sortProps = { sortField, sortDirection, onSort };

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr>
            <th className={cn(HEADER_BASE, 'w-[28px]')} />
            <th className={cn(HEADER_BASE, 'w-[24px] px-1')} />
            <th className={cn(HEADER_BASE, 'w-[32px] pr-0 pl-1')} />
            <SortableHeader field="symbol" label="Symbol" {...sortProps} />
            <SortableHeader field="name" label="Name" {...sortProps} />
            <SortableHeader field="current_price" label="Price" {...sortProps} align="right" />
            <SortableHeader field="total_quantity" label="Qty" {...sortProps} align="right" />
            <SortableHeader field="avg_cost_per_unit_native" label="Avg Cost" {...sortProps} align="right" />
            <SortableHeader field="total_cost_basis_native" label="Cost Basis" {...sortProps} align="right" />
            <SortableHeader field="total_market_value_native" label="Value" {...sortProps} align="right" />
            <SortableHeader field="total_pnl_native" label="P&L" {...sortProps} align="right" />
            <th className={cn(HEADER_BASE, 'text-center w-[48px]')}>Accts</th>
          </tr>
        </thead>

        <tbody>
          {positions.map((position) => {
            const isExpanded = expandedRows.has(position.asset_id);
            return (
              <Fragment key={position.asset_id}>
                <HoldingsRow
                  position={position}
                  isExpanded={isExpanded}
                  onToggleExpand={() => onToggleExpand(position.asset_id)}
                  onRowClick={() => onRowClick(position)}
                  onToggleFavorite={() => onToggleFavorite(position.asset_id)}
                />
                {isExpanded && position.accounts?.length > 0 && (
                  <ExpandedAccountRows
                    accounts={position.accounts}
                    currency={position.currency}
                    assetClass={position.asset_class}
                  />
                )}
              </Fragment>
            );
          })}
        </tbody>

        {positions.length > 0 && (
          <tfoot>
            <HoldingsSummaryRow
              costBasis={totals.costBasis}
              marketValue={totals.marketValue}
              pnl={totals.pnl}
              pnlPct={totals.pnlPct}
              currency={currency}
            />
          </tfoot>
        )}
      </table>

      {positions.length === 0 && (
        <div className="text-center py-12">
          <p className="text-[var(--text-secondary)]">
            {emptyMessage || 'No holdings found'}
          </p>
          {onClearFilters && (
            <button
              onClick={onClearFilters}
              className="mt-2 text-sm text-accent hover:underline cursor-pointer"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}
