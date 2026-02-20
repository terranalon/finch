import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AssetChart from '../AssetChart';

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  AreaChart: ({ children }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  CartesianGrid: () => null,
  defs: () => null,
  linearGradient: () => null,
  stop: () => null,
}));

vi.mock('../../../hooks/useChartColors', () => ({
  useChartColors: () => ({
    accent: '#3b82f6',
    positive: '#22c55e',
    negative: '#ef4444',
    borderPrimary: '#e2e8f0',
    textTertiary: '#94a3b8',
  }),
}));

vi.mock('../../../lib/index.js', () => ({
  formatCurrency: (v) => `$${Number(v || 0).toFixed(2)}`,
  cn: (...args) => args.filter(Boolean).join(' '),
}));

const mockPriceHistory = {
  data: [
    { date: '2026-01-01', close: 230.00 },
    { date: '2026-01-15', close: 235.50 },
    { date: '2026-02-01', close: 237.42 },
  ],
};

const onPeriodChange = vi.fn();

describe('AssetChart', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders "No price history available" when data is null', () => {
    render(<AssetChart priceHistory={null} activePeriod="1y" onPeriodChange={onPeriodChange} currency="USD" />);
    expect(screen.getByText(/no price history available/i)).toBeInTheDocument();
  });

  it('renders "No price history available" when data array is empty', () => {
    render(<AssetChart priceHistory={{ data: [] }} activePeriod="1y" onPeriodChange={onPeriodChange} currency="USD" />);
    expect(screen.getByText(/no price history available/i)).toBeInTheDocument();
  });

  it('renders all period buttons', () => {
    render(<AssetChart priceHistory={mockPriceHistory} activePeriod="1y" onPeriodChange={onPeriodChange} currency="USD" />);
    expect(screen.getByRole('button', { name: '1D' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '5D' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '1M' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '3M' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '6M' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '1Y' })).toBeInTheDocument();
  });

  it('highlights the active period button', () => {
    render(<AssetChart priceHistory={mockPriceHistory} activePeriod="1y" onPeriodChange={onPeriodChange} currency="USD" />);
    const activeBtn = screen.getByRole('button', { name: '1Y' });
    expect(activeBtn.className).toContain('bg-accent');
    const inactiveBtn = screen.getByRole('button', { name: '1M' });
    expect(inactiveBtn.className).not.toContain('bg-accent');
  });

  it('calls onPeriodChange with correct value when period button clicked', () => {
    render(<AssetChart priceHistory={mockPriceHistory} activePeriod="1y" onPeriodChange={onPeriodChange} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: '1M' }));
    expect(onPeriodChange).toHaveBeenCalledWith('1mo');
  });

  it('renders chart container when data is provided', () => {
    render(<AssetChart priceHistory={mockPriceHistory} activePeriod="1y" onPeriodChange={onPeriodChange} currency="USD" />);
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument();
  });
});
