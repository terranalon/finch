import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FinishStep } from '../FinishStep';

const DEFAULT_PROPS = {
  onGoToDashboard: vi.fn(),
  onAddAnother: vi.fn(),
};

function renderFinishStep(overrides = {}) {
  return render(<FinishStep {...DEFAULT_PROPS} {...overrides} />);
}

describe('FinishStep', () => {
  it('renders completion heading', () => {
    renderFinishStep();
    expect(screen.getByText("You're all set!")).toBeInTheDocument();
  });

  it('renders portfolio name input with default value', () => {
    renderFinishStep({ defaultPortfolioName: 'My Portfolio' });
    expect(screen.getByDisplayValue('My Portfolio')).toBeInTheDocument();
  });

  it('calls onGoToDashboard with current portfolio name', () => {
    const onGoToDashboard = vi.fn();
    renderFinishStep({ onGoToDashboard, defaultPortfolioName: 'My Portfolio' });

    fireEvent.change(screen.getByDisplayValue('My Portfolio'), { target: { value: 'Retirement Fund' } });
    fireEvent.click(screen.getByText(/go to dashboard/i));

    expect(onGoToDashboard).toHaveBeenCalledWith('Retirement Fund');
  });

  it('calls onAddAnother when secondary button clicked', () => {
    const onAddAnother = vi.fn();
    renderFinishStep({ onAddAnother });
    fireEvent.click(screen.getByText(/add another account/i));
    expect(onAddAnother).toHaveBeenCalledOnce();
  });

  it('renders feature tips', () => {
    renderFinishStep();
    expect(screen.getByText('Holdings')).toBeInTheDocument();
    expect(screen.getByText('Performance')).toBeInTheDocument();
    expect(screen.getByText('Auto Sync')).toBeInTheDocument();
  });

  it('renders hint text about adding accounts later', () => {
    renderFinishStep();
    expect(screen.getByText(/you can always add more/i)).toBeInTheDocument();
  });
});
