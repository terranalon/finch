import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RecentActivity from '../RecentActivity';

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

const sellRow = { id: 'trade-2', date: '2026-03-05', type: 'sell', quantity: 4, price: 120, total: 480, account: 'IBKR' };
const buyRow = { id: 'trade-1', date: '2026-01-10', type: 'buy', quantity: 10, price: 100, total: -1000, account: 'IBKR' };
const dividendRow = { id: 'div-9', date: '2026-02-01', type: 'DIVIDEND', quantity: null, price: null, total: 12.5, account: 'Kraken' };

const activity = [sellRow, dividendRow];

describe('RecentActivity', () => {
  it('renders the "Recent Activity" title', () => {
    renderWithRouter(<RecentActivity activity={activity} activityCount={2} currency="USD" />);
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
  });

  it('renders one row per activity item with its account', () => {
    renderWithRouter(<RecentActivity activity={activity} activityCount={2} currency="USD" />);
    expect(screen.getByText(/IBKR/)).toBeInTheDocument();
    expect(screen.getByText(/Kraken/)).toBeInTheDocument();
  });

  it('shows a "View all N transactions" link when activityCount exceeds shown rows', () => {
    renderWithRouter(<RecentActivity activity={activity} activityCount={8} currency="USD" />);
    const link = screen.getByRole('link', { name: /View all 8 transactions/ });
    expect(link).toHaveAttribute('href', '/activity');
  });

  it('hides the "View all" link when activityCount equals the shown rows', () => {
    renderWithRouter(<RecentActivity activity={activity} activityCount={2} currency="USD" />);
    expect(screen.queryByText(/View all/)).not.toBeInTheDocument();
  });

  it('renders an empty state and no "View all" link when there is no activity', () => {
    renderWithRouter(<RecentActivity activity={[]} activityCount={0} currency="USD" />);
    expect(screen.queryByText(/View all/)).not.toBeInTheDocument();
    expect(screen.queryByText(/IBKR/)).not.toBeInTheDocument();
  });

  it('renders a sell row with a positive (+) amount', () => {
    renderWithRouter(<RecentActivity activity={[sellRow]} activityCount={1} currency="USD" />);
    expect(screen.getByText(/\+.*480/)).toBeInTheDocument();
  });

  it('renders a buy row with a negative (-) amount', () => {
    renderWithRouter(<RecentActivity activity={[buyRow]} activityCount={1} currency="USD" />);
    expect(screen.getByText(/-.*1,?000/)).toBeInTheDocument();
  });

  it('renders a dividend row with a positive (+) amount', () => {
    renderWithRouter(<RecentActivity activity={[dividendRow]} activityCount={1} currency="USD" />);
    expect(screen.getByText(/\+.*12\.5/)).toBeInTheDocument();
  });

  it('includes the "@ price" meta segment for a trade row with a quantity', () => {
    renderWithRouter(<RecentActivity activity={[sellRow]} activityCount={1} currency="USD" />);
    expect(screen.getByText(/@/)).toBeInTheDocument();
  });

  it('omits the "@ price" meta segment for a dividend row with no quantity', () => {
    renderWithRouter(<RecentActivity activity={[dividendRow]} activityCount={1} currency="USD" />);
    expect(screen.queryByText(/@/)).not.toBeInTheDocument();
  });

  it('renders "--" and not "$NaN" when total is undefined', () => {
    const row = { id: 'x', date: '2026-04-01', type: 'sell', quantity: null, price: null, total: undefined, account: 'IBKR' };
    renderWithRouter(<RecentActivity activity={[row]} activityCount={1} currency="USD" />);
    expect(screen.getByText('--')).toBeInTheDocument();
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });
});
