import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AssetAbout from '../AssetAbout';

vi.mock('../../../lib/index.js', () => ({
  cn: (...args) => args.filter(Boolean).join(' '),
}));

const stockAsset = {
  asset_class: 'Stock',
  name: 'Apple Inc.',
  description: 'Apple Inc. designs, manufactures, and markets smartphones and computers.',
  sector: 'Technology',
  industry: 'Consumer Electronics',
  ceo: 'Tim Cook',
  employees: 164000,
  website: 'https://apple.com',
};

const etfAsset = {
  asset_class: 'ETF',
  name: 'Vanguard S&P 500',
  description: 'Tracks the S&P 500 index.',
  sector: 'Equity',
  fund_family: 'Vanguard',
  website: 'https://vanguard.com',
};

const cryptoAsset = {
  asset_class: 'Crypto',
  name: 'Bitcoin',
  description: 'Bitcoin is a decentralized digital currency.',
  website: 'https://bitcoin.org',
};

describe('AssetAbout', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders "About" title', () => {
    render(<AssetAbout asset={stockAsset} />);
    expect(screen.getByText('About')).toBeInTheDocument();
  });

  it('shows asset description text', () => {
    render(<AssetAbout asset={stockAsset} />);
    expect(screen.getByText(stockAsset.description)).toBeInTheDocument();
  });

  it('shows "No description available." when description is null', () => {
    render(<AssetAbout asset={{ ...stockAsset, description: null }} />);
    expect(screen.getByText('No description available.')).toBeInTheDocument();
  });

  it('toggles body visibility on header click (collapse/expand)', () => {
    render(<AssetAbout asset={stockAsset} />);
    // Starts expanded - description visible
    expect(screen.getByText(stockAsset.description)).toBeInTheDocument();
    // Click header to collapse
    fireEvent.click(screen.getByRole('button', { name: /about/i }));
    expect(screen.queryByText(stockAsset.description)).not.toBeInTheDocument();
    // Click again to expand
    fireEvent.click(screen.getByRole('button', { name: /about/i }));
    expect(screen.getByText(stockAsset.description)).toBeInTheDocument();
  });

  it('shows Stock meta rows: Sector, Industry, CEO, Employees, Website', () => {
    render(<AssetAbout asset={stockAsset} />);
    expect(screen.getByText('Sector')).toBeInTheDocument();
    expect(screen.getByText('Industry')).toBeInTheDocument();
    expect(screen.getByText('CEO')).toBeInTheDocument();
    expect(screen.getByText('Employees')).toBeInTheDocument();
    expect(screen.getByText('Website')).toBeInTheDocument();
  });

  it('shows ETF meta rows: Sector, Fund Family, Website', () => {
    render(<AssetAbout asset={etfAsset} />);
    expect(screen.getByText('Sector')).toBeInTheDocument();
    expect(screen.getByText('Fund Family')).toBeInTheDocument();
    expect(screen.getByText('Website')).toBeInTheDocument();
    expect(screen.queryByText('CEO')).not.toBeInTheDocument();
  });

  it('shows Crypto meta rows: Website (no CEO/Industry)', () => {
    render(<AssetAbout asset={cryptoAsset} />);
    expect(screen.getByText('Website')).toBeInTheDocument();
    expect(screen.queryByText('CEO')).not.toBeInTheDocument();
    expect(screen.queryByText('Industry')).not.toBeInTheDocument();
  });

  it('renders website as external link with correct href', () => {
    render(<AssetAbout asset={stockAsset} />);
    const link = screen.getByRole('link', { name: /apple\.com/i });
    expect(link).toHaveAttribute('href', 'https://apple.com');
    expect(link).toHaveAttribute('target', '_blank');
  });
});
