import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

vi.mock('../../../lib', () => ({
  cn: (...args) => args.filter(Boolean).join(' '),
  formatCurrency: (v) => `$${Number(v).toFixed(2)}`,
  formatPercent: (v) => `${Number(v).toFixed(2)}%`,
  getChangeColor: (v) => (v >= 0 ? 'text-positive' : 'text-negative'),
  getChangeIndicator: (v) => (v >= 0 ? '+' : '-'),
}));

import { HoldingsSummaryRow } from '../HoldingsSummaryRow';

function renderSummary(props = {}) {
  return render(
    <table>
      <tfoot>
        <HoldingsSummaryRow
          costBasis={50000}
          marketValue={60000}
          pnl={10000}
          pnlPct={20}
          currency="USD"
          {...props}
        />
      </tfoot>
    </table>
  );
}

describe('HoldingsSummaryRow', () => {
  it('renders "All Holdings" label', () => {
    renderSummary();
    expect(screen.getByText('All Holdings')).toBeInTheDocument();
  });

  it('renders cost basis, market value, and P&L', () => {
    renderSummary();
    expect(screen.getByText('Cost Basis')).toBeInTheDocument();
    expect(screen.getByText('Market Value')).toBeInTheDocument();
    expect(screen.getByText('Total P&L')).toBeInTheDocument();
    expect(screen.getByText('$50000.00')).toBeInTheDocument();
    expect(screen.getByText('$60000.00')).toBeInTheDocument();
  });
});
