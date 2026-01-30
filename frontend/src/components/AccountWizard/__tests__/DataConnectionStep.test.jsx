import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DataConnectionStep } from '../steps/DataConnectionStep';

const mockBrokerWithApi = {
  name: 'Interactive Brokers',
  type: 'ibkr',
  hasApi: true,
  supportedFormats: ['.xml'],
  fields: {
    api: [
      { key: 'flex_token', label: 'Flex Token', type: 'password', placeholder: 'Enter token' },
      { key: 'flex_query_id', label: 'Query ID', type: 'text', placeholder: 'Enter ID' },
    ],
  },
};

const mockBrokerFileOnly = {
  name: 'Meitav Trade',
  type: 'meitav',
  hasApi: false,
  supportedFormats: ['.xlsx'],
  fields: {},
};

describe('DataConnectionStep', () => {
  it('renders API connection tab when broker has API', () => {
    render(
      <DataConnectionStep
        broker={mockBrokerWithApi}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
        onTestCredentials={() => {}}
      />
    );
    expect(screen.getByText('Connect via API')).toBeInTheDocument();
    expect(screen.getByText('Upload File')).toBeInTheDocument();
  });

  it('hides API tab when broker has no API', () => {
    render(
      <DataConnectionStep
        broker={mockBrokerFileOnly}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
        onTestCredentials={() => {}}
      />
    );
    expect(screen.queryByText('Connect via API')).not.toBeInTheDocument();
  });

  it('renders credential fields for API brokers', () => {
    render(
      <DataConnectionStep
        broker={mockBrokerWithApi}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
        onTestCredentials={() => {}}
      />
    );
    expect(screen.getByText('Flex Token')).toBeInTheDocument();
    expect(screen.getByText('Query ID')).toBeInTheDocument();
  });

  it('calls onTestCredentials when test button clicked', async () => {
    const onTestCredentials = vi.fn().mockResolvedValue({ status: 'success' });

    render(
      <DataConnectionStep
        broker={mockBrokerWithApi}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
        onTestCredentials={onTestCredentials}
      />
    );

    // Fill in credentials
    const tokenInput = screen.getByPlaceholderText('Enter token');
    const queryInput = screen.getByPlaceholderText('Enter ID');
    fireEvent.change(tokenInput, { target: { value: 'test-token' } });
    fireEvent.change(queryInput, { target: { value: '12345' } });

    // Click test button
    const testButton = screen.getByText('Test Connection');
    fireEvent.click(testButton);

    await waitFor(() => {
      expect(onTestCredentials).toHaveBeenCalledWith({
        flex_token: 'test-token',
        flex_query_id: '12345',
      });
    });
  });

  it('shows success message after successful test', async () => {
    const onTestCredentials = vi.fn().mockResolvedValue({ status: 'success' });

    render(
      <DataConnectionStep
        broker={mockBrokerWithApi}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
        onTestCredentials={onTestCredentials}
      />
    );

    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(screen.getByText('Connection successful!')).toBeInTheDocument();
    });
  });

  it('shows error message after failed test', async () => {
    const onTestCredentials = vi.fn().mockRejectedValue(new Error('Invalid credentials'));

    render(
      <DataConnectionStep
        broker={mockBrokerWithApi}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
        onTestCredentials={onTestCredentials}
      />
    );

    fireEvent.click(screen.getByText('Test Connection'));

    await waitFor(() => {
      expect(screen.getByText('Connection failed')).toBeInTheDocument();
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });
  });

  it('has accessible file drop zone', () => {
    render(
      <DataConnectionStep
        broker={mockBrokerFileOnly}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
        onTestCredentials={() => {}}
      />
    );

    const dropZone = screen.getByRole('button', { name: /upload file/i });
    expect(dropZone).toHaveAttribute('tabIndex', '0');
  });

  it('calls onSkip when skip button clicked', () => {
    const onSkip = vi.fn();

    render(
      <DataConnectionStep
        broker={mockBrokerWithApi}
        onComplete={() => {}}
        onSkip={onSkip}
        onBack={() => {}}
        onTestCredentials={() => {}}
      />
    );

    fireEvent.click(screen.getByText('Skip for now'));
    expect(onSkip).toHaveBeenCalled();
  });

  it('calls onBack when back button clicked', () => {
    const onBack = vi.fn();

    render(
      <DataConnectionStep
        broker={mockBrokerWithApi}
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={onBack}
        onTestCredentials={() => {}}
      />
    );

    fireEvent.click(screen.getByText('Back'));
    expect(onBack).toHaveBeenCalled();
  });
});
