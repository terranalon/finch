import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AccountDetailsStep } from '../steps/AccountDetailsStep';

const defaultProps = {
  broker: { name: 'Kraken', defaultCurrency: 'USD' },
  category: { defaultAccountType: 'Crypto' },
  existingAccountNames: [],
  onSubmit: vi.fn(),
  onBack: vi.fn(),
};

describe('AccountDetailsStep', () => {
  it('suggests default name when no existing accounts', () => {
    render(<AccountDetailsStep {...defaultProps} />);
    expect(screen.getByDisplayValue('My Kraken Account')).toBeInTheDocument();
  });

  it('suggests numbered name when default already exists', () => {
    render(
      <AccountDetailsStep
        {...defaultProps}
        existingAccountNames={['My Kraken Account']}
      />
    );
    expect(screen.getByDisplayValue('My Kraken Account #2')).toBeInTheDocument();
  });

  it('suggests #3 when both base and #2 exist', () => {
    render(
      <AccountDetailsStep
        {...defaultProps}
        existingAccountNames={['My Kraken Account', 'My Kraken Account #2']}
      />
    );
    expect(screen.getByDisplayValue('My Kraken Account #3')).toBeInTheDocument();
  });

  it('is case-insensitive when checking for duplicates', () => {
    render(
      <AccountDetailsStep
        {...defaultProps}
        existingAccountNames={['my kraken account']}
      />
    );
    expect(screen.getByDisplayValue('My Kraken Account #2')).toBeInTheDocument();
  });

  it('uses generic name when no broker specified', () => {
    render(<AccountDetailsStep {...defaultProps} broker={null} />);
    expect(screen.getByDisplayValue('My Account')).toBeInTheDocument();
  });
});
