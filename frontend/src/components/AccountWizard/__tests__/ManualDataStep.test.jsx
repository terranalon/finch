import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ManualDataStep } from '../steps/ManualDataStep';

describe('ManualDataStep', () => {
  it('renders required columns', () => {
    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
      />
    );

    expect(screen.getByText('date')).toBeInTheDocument();
    expect(screen.getByText('type')).toBeInTheDocument();
    expect(screen.getByText('symbol')).toBeInTheDocument();
    expect(screen.getByText('quantity')).toBeInTheDocument();
    expect(screen.getByText('price')).toBeInTheDocument();
    expect(screen.getByText('currency')).toBeInTheDocument();
  });

  it('renders optional columns', () => {
    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
      />
    );

    expect(screen.getByText('fees')).toBeInTheDocument();
    expect(screen.getByText('notes')).toBeInTheDocument();
  });

  it('renders template download buttons', () => {
    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
      />
    );

    expect(screen.getByText('Download CSV Template')).toBeInTheDocument();
    expect(screen.getByText('Download Excel Template')).toBeInTheDocument();
  });

  it('has accessible file drop zone', () => {
    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
      />
    );

    const dropZone = screen.getByRole('button', { name: /upload file/i });
    expect(dropZone).toHaveAttribute('tabIndex', '0');
  });

  it('disables upload button when no file selected', () => {
    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
      />
    );

    const uploadButton = screen.getByText('Upload & Import');
    expect(uploadButton).toBeDisabled();
  });

  it('calls onSkip when skip button clicked', () => {
    const onSkip = vi.fn();

    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={onSkip}
        onBack={() => {}}
      />
    );

    fireEvent.click(screen.getByText('Skip for now'));
    expect(onSkip).toHaveBeenCalled();
  });

  it('calls onBack when back button clicked', () => {
    const onBack = vi.fn();

    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={onBack}
      />
    );

    fireEvent.click(screen.getByText('Back'));
    expect(onBack).toHaveBeenCalled();
  });

  it('shows responsibility warning', () => {
    render(
      <ManualDataStep
        onComplete={() => {}}
        onSkip={() => {}}
        onBack={() => {}}
      />
    );

    expect(screen.getByText(/you are responsible for ensuring/i)).toBeInTheDocument();
  });
});
