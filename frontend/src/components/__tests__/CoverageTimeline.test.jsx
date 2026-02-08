import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CoverageTimeline } from '../CoverageTimeline';

describe('CoverageTimeline', () => {
  it('renders nothing when files array is empty', () => {
    const { container } = render(<CoverageTimeline files={[]} />);
    expect(container.querySelector('[data-testid="coverage-timeline"]')).toBeNull();
  });

  it('renders timeline with a single file', () => {
    render(
      <CoverageTimeline
        files={[
          {
            fileName: '2023_trades.xml',
            startDate: '2023-01-01',
            endDate: '2023-12-31',
            transactions: 42,
          },
        ]}
      />
    );

    expect(screen.getByText('2023_trades.xml')).toBeInTheDocument();
    expect(screen.getByText(/42 transactions/)).toBeInTheDocument();
  });

  it('renders timeline with multiple files', () => {
    render(
      <CoverageTimeline
        files={[
          { fileName: '2022.xml', startDate: '2022-01-01', endDate: '2022-12-31', transactions: 30 },
          { fileName: '2023.xml', startDate: '2023-01-01', endDate: '2023-12-31', transactions: 50 },
        ]}
      />
    );

    expect(screen.getByText('2022.xml')).toBeInTheDocument();
    expect(screen.getByText('2023.xml')).toBeInTheDocument();
  });

  it('renders gap indicators when gaps are provided', () => {
    render(
      <CoverageTimeline
        files={[
          { fileName: '2022.xml', startDate: '2022-01-01', endDate: '2022-06-30', transactions: 20 },
          { fileName: '2023.xml', startDate: '2023-01-01', endDate: '2023-12-31', transactions: 40 },
        ]}
        gaps={[
          { start_date: '2022-07-01', end_date: '2022-12-31', days: 184 },
        ]}
      />
    );

    expect(screen.getByText(/184 day gap/)).toBeInTheDocument();
  });

  it('shows date range labels', () => {
    render(
      <CoverageTimeline
        files={[
          { fileName: 'trades.xml', startDate: '2022-01-15', endDate: '2024-06-30', transactions: 100 },
        ]}
      />
    );

    expect(screen.getByText(/Jan 2022/)).toBeInTheDocument();
    expect(screen.getByText(/Jun 2024/)).toBeInTheDocument();
  });
});
