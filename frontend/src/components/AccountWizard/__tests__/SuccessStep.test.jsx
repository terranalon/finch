import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SuccessStep } from '../steps/SuccessStep';

// Mock BatchUploadModal to avoid testing its internals here
vi.mock('../../BatchUploadModal.jsx', () => ({
  BatchUploadModal: ({ isOpen }) => isOpen ? <div data-testid="batch-upload-modal" /> : null,
}));

const defaultProps = {
  broker: { name: 'Interactive Brokers', type: 'ibkr', supportedFormats: ['.xml'] },
  accountDetails: { name: 'My IBKR', accountType: 'Investment', currency: 'USD' },
  skippedData: false,
  hasSnapshotData: false,
  createdAccountId: 1,
  onViewAccount: vi.fn(),
  onAddAnother: vi.fn(),
  onDone: vi.fn(),
};

describe('SuccessStep', () => {
  it('renders success message', () => {
    render(<SuccessStep {...defaultProps} />);
    expect(screen.getByText(/all set/i)).toBeInTheDocument();
  });

  it('does not show upload history section when hasSnapshotData is false', () => {
    render(<SuccessStep {...defaultProps} hasSnapshotData={false} />);
    expect(screen.queryByText(/Upload History/i)).not.toBeInTheDocument();
  });

  it('shows upload history section when hasSnapshotData is true', () => {
    render(<SuccessStep {...defaultProps} hasSnapshotData={true} />);
    expect(screen.getByText(/doesn't include historical transactions/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload history/i })).toBeInTheDocument();
  });

  it('shows "do this later" note in snapshot mode', () => {
    render(<SuccessStep {...defaultProps} hasSnapshotData={true} />);
    expect(screen.getByText(/later/i)).toBeInTheDocument();
  });

  it('opens batch upload modal when Upload History clicked', () => {
    render(<SuccessStep {...defaultProps} hasSnapshotData={true} />);
    fireEvent.click(screen.getByRole('button', { name: /upload history/i }));
    expect(screen.getByTestId('batch-upload-modal')).toBeInTheDocument();
  });

  it('calls onViewAccount when View Account clicked', () => {
    const onViewAccount = vi.fn();
    render(<SuccessStep {...defaultProps} onViewAccount={onViewAccount} />);
    fireEvent.click(screen.getByText('View Account'));
    expect(onViewAccount).toHaveBeenCalled();
  });
});
