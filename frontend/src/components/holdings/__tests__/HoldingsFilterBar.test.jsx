import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../lib', () => ({
  cn: (...args) => args.filter(Boolean).join(' '),
}));

vi.mock('../../../hooks/useClickOutside', () => ({
  useClickOutside: vi.fn(),
}));

import { HoldingsFilterBar } from '../HoldingsFilterBar';

const defaultProps = {
  searchQuery: '',
  onSearchChange: vi.fn(),
  accounts: [
    { id: 1, name: 'IBKR Main' },
    { id: 2, name: 'Kraken' },
  ],
  selectedAccounts: [1, 2],
  onAccountsChange: vi.fn(),
  assetClasses: ['Equity', 'Crypto'],
  selectedClasses: ['Equity', 'Crypto'],
  onClassesChange: vi.fn(),
  sectors: ['Technology', 'Finance'],
  selectedSectors: ['Technology', 'Finance'],
  onSectorsChange: vi.fn(),
  onClearAll: vi.fn(),
};

describe('HoldingsFilterBar', () => {
  it('renders search input', () => {
    render(<HoldingsFilterBar {...defaultProps} />);
    expect(screen.getByPlaceholderText(/search by symbol or name/i)).toBeInTheDocument();
  });

  it('calls onSearchChange when typing', () => {
    const onSearchChange = vi.fn();
    render(<HoldingsFilterBar {...defaultProps} onSearchChange={onSearchChange} />);
    fireEvent.change(screen.getByPlaceholderText(/search by symbol or name/i), {
      target: { value: 'AAPL' },
    });
    expect(onSearchChange).toHaveBeenCalledWith('AAPL');
  });

  it('renders filter icon button', () => {
    render(<HoldingsFilterBar {...defaultProps} />);
    expect(screen.getByTitle('Filters')).toBeInTheDocument();
  });

  it('opens filter panel on icon click', () => {
    render(<HoldingsFilterBar {...defaultProps} />);
    fireEvent.click(screen.getByTitle('Filters'));
    expect(screen.getByText('Accounts')).toBeInTheDocument();
    expect(screen.getByText('Asset Class')).toBeInTheDocument();
    expect(screen.getByText('Sector')).toBeInTheDocument();
  });

  it('shows badge when filters are active', () => {
    render(
      <HoldingsFilterBar
        {...defaultProps}
        selectedAccounts={[1]}  // Only 1 of 2 selected = active filter
      />
    );
    // Badge should show "1" for 1 active filter group
    const badge = screen.getByTestId('filter-badge');
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toBe('1');
  });

  it('hides badge when no filters are active', () => {
    render(<HoldingsFilterBar {...defaultProps} />);
    expect(screen.queryByTestId('filter-badge')).not.toBeInTheDocument();
  });
});
