import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BatchUploadModal } from '../BatchUploadModal';

// Mock the api function
const mockApi = vi.fn();
vi.mock('../../lib/index.js', () => ({
  api: (...args) => mockApi(...args),
  cn: (...args) => args.filter(Boolean).join(' '),
}));

// Mock crypto.randomUUID
vi.stubGlobal('crypto', { randomUUID: () => 'test-session-id' });

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  accountId: 1,
  brokerType: 'ibkr',
  supportedFormats: ['.xml'],
};

describe('BatchUploadModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <BatchUploadModal {...defaultProps} isOpen={false} />
    );
    expect(container.querySelector('[data-testid="batch-upload-modal"]')).toBeNull();
  });

  it('renders file upload area when open', () => {
    render(<BatchUploadModal {...defaultProps} />);
    expect(screen.getByText(/Drop your file here/i)).toBeInTheDocument();
  });

  it('shows supported format info', () => {
    render(<BatchUploadModal {...defaultProps} />);
    expect(screen.getByText(/XML/i)).toBeInTheDocument();
  });

  it('uploads file with session_id and shows in file list', async () => {
    mockApi.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        status: 'staged',
        source_id: 5,
        date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
        stats: {
          total_records: 42,
          session_id: 'test-session-id',
          transactions: { imported: 42, skipped: 0 },
          unique_assets_in_file: 8,
          symbols_in_file: ['AAPL', 'MSFT'],
        },
      }),
    });

    render(<BatchUploadModal {...defaultProps} />);

    // Create a mock file and trigger upload
    const file = new File(['<xml/>'], 'trades_2023.xml', { type: 'text/xml' });
    const dropZone = screen.getByRole('button', { name: /upload file/i });

    // Simulate file drop
    fireEvent.drop(dropZone, {
      dataTransfer: { files: [file] },
    });

    // Click upload button
    await waitFor(() => {
      expect(screen.getByText('trades_2023.xml')).toBeInTheDocument();
    });

    const uploadBtn = screen.getByRole('button', { name: /upload & stage/i });
    fireEvent.click(uploadBtn);

    await waitFor(() => {
      expect(mockApi).toHaveBeenCalledWith(
        '/broker-data/upload/1',
        expect.objectContaining({ method: 'POST' })
      );
    });

    // Verify session_id was included in form data
    const callArgs = mockApi.mock.calls[0];
    const formData = callArgs[1].body;
    expect(formData instanceof FormData).toBe(true);
    expect(formData.get('session_id')).toBe('test-session-id');

    // Verify file appears in list
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument(); // transactions
    });
  });

  it('enables finalize button after uploading files', async () => {
    mockApi.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        status: 'staged',
        source_id: 5,
        date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
        stats: { total_records: 42, transactions: { imported: 42 }, unique_assets_in_file: 8, symbols_in_file: [] },
      }),
    });

    render(<BatchUploadModal {...defaultProps} />);

    // Finalize should be disabled initially
    expect(screen.getByRole('button', { name: /finalize import/i })).toBeDisabled();

    // Upload a file
    const file = new File(['<xml/>'], 'trades.xml', { type: 'text/xml' });
    const dropZone = screen.getByRole('button', { name: /upload file/i });
    fireEvent.drop(dropZone, { dataTransfer: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('trades.xml')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /upload & stage/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /finalize import/i })).not.toBeDisabled();
    });
  });

  it('calls finalize endpoint and shows results', async () => {
    // First call: upload
    mockApi.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        status: 'staged',
        source_id: 5,
        date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
        stats: { total_records: 42, transactions: { imported: 42 }, unique_assets_in_file: 8, symbols_in_file: [] },
      }),
    });
    // Second call: finalize
    mockApi.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        status: 'completed',
        sources_finalized: 1,
        date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
        synthetic_cleanup: { deleted_sources: 0, deleted_transactions: 0 },
        holdings_reconstruction: { holdings_updated: 8 },
        validation: null,
      }),
    });

    render(<BatchUploadModal {...defaultProps} />);

    // Upload file
    const file = new File(['<xml/>'], 'trades.xml', { type: 'text/xml' });
    fireEvent.drop(screen.getByRole('button', { name: /upload file/i }), {
      dataTransfer: { files: [file] },
    });
    await waitFor(() => screen.getByText('trades.xml'));
    fireEvent.click(screen.getByRole('button', { name: /upload & stage/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /finalize import/i })).not.toBeDisabled();
    });

    // Click finalize
    fireEvent.click(screen.getByRole('button', { name: /finalize import/i }));

    await waitFor(() => {
      expect(mockApi).toHaveBeenCalledWith(
        '/broker-data/finalize-batch/1?session_id=test-session-id',
        expect.objectContaining({ method: 'POST' })
      );
    });

    // Should show completion
    await waitFor(() => {
      expect(screen.getByText(/finalized/i)).toBeInTheDocument();
    });
  });

  it('shows green validation banner when all positions match', async () => {
    mockApi
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'staged', source_id: 5,
          date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
          stats: { total_records: 10, transactions: { imported: 10 }, unique_assets_in_file: 3, symbols_in_file: [] },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'completed', sources_finalized: 1,
          date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
          synthetic_cleanup: { deleted_sources: 1, deleted_transactions: 5 },
          holdings_reconstruction: { holdings_updated: 3 },
          validation: {
            is_valid: true, positions_checked: 3, positions_matched: 3, discrepancies: [],
          },
        }),
      });

    render(<BatchUploadModal {...defaultProps} />);

    // Upload + finalize
    const file = new File(['<xml/>'], 't.xml', { type: 'text/xml' });
    fireEvent.drop(screen.getByRole('button', { name: /upload file/i }), { dataTransfer: { files: [file] } });
    await waitFor(() => screen.getByText('t.xml'));
    fireEvent.click(screen.getByRole('button', { name: /upload & stage/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /finalize import/i })).not.toBeDisabled());
    fireEvent.click(screen.getByRole('button', { name: /finalize import/i }));

    await waitFor(() => {
      expect(screen.getByText(/3\/3 positions match/i)).toBeInTheDocument();
    });
  });

  it('shows red validation banner when positions are missing', async () => {
    mockApi
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'staged', source_id: 5,
          date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
          stats: { total_records: 10, transactions: { imported: 10 }, unique_assets_in_file: 3, symbols_in_file: [] },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          status: 'completed', sources_finalized: 1,
          date_range: { start_date: '2023-01-01', end_date: '2023-12-31' },
          synthetic_cleanup: { deleted_sources: 1, deleted_transactions: 5 },
          holdings_reconstruction: { holdings_updated: 2 },
          validation: {
            is_valid: false, positions_checked: 3, positions_matched: 1,
            discrepancies: [
              { type: 'missing_position', symbol: 'AAPL', message: 'AAPL: position missing' },
              { type: 'quantity_mismatch', symbol: 'MSFT', message: 'MSFT: expected 50, got 30' },
            ],
          },
        }),
      });

    render(<BatchUploadModal {...defaultProps} />);

    const file = new File(['<xml/>'], 't.xml', { type: 'text/xml' });
    fireEvent.drop(screen.getByRole('button', { name: /upload file/i }), { dataTransfer: { files: [file] } });
    await waitFor(() => screen.getByText('t.xml'));
    fireEvent.click(screen.getByRole('button', { name: /upload & stage/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /finalize import/i })).not.toBeDisabled());
    fireEvent.click(screen.getByRole('button', { name: /finalize import/i }));

    await waitFor(() => {
      expect(screen.getByText(/1\/3 positions match/i)).toBeInTheDocument();
    });
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<BatchUploadModal {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });
});
