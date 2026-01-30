import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrokerLogo } from '../BrokerLogo';

describe('BrokerLogo', () => {
  it('renders image for known broker', () => {
    render(<BrokerLogo type="ibkr" />);
    const img = screen.getByRole('img');
    expect(img).toHaveAttribute('src', expect.stringContaining('brandfetch'));
  });

  it('renders fallback for unknown broker', () => {
    render(<BrokerLogo type="unknown" />);
    expect(screen.getByText('UNKN')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<BrokerLogo type="kraken" className="custom-class" />);
    const img = screen.getByRole('img');
    expect(img).toHaveClass('custom-class');
  });

  it('renders correct logo for each known broker', () => {
    const brokers = ['ibkr', 'meitav', 'kraken', 'bit2c', 'binance'];

    brokers.forEach((broker) => {
      const { unmount } = render(<BrokerLogo type={broker} />);
      const img = screen.getByRole('img');
      expect(img).toHaveAttribute('alt', `${broker} logo`);
      unmount();
    });
  });
});
