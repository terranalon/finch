import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { FinishStep } from '../FinishStep';

describe('FinishStep', () => {
  it('renders completion heading', () => {
    render(<FinishStep onGoToDashboard={() => {}} onAddAnother={() => {}} />);
    expect(screen.getByText("You're all set!")).toBeInTheDocument();
  });

  it('renders portfolio name input with default value', () => {
    render(<FinishStep onGoToDashboard={() => {}} onAddAnother={() => {}} defaultPortfolioName="My Portfolio" />);
    expect(screen.getByDisplayValue('My Portfolio')).toBeInTheDocument();
  });

  it('calls onGoToDashboard with current portfolio name', () => {
    const onGoToDashboard = vi.fn();
    render(<FinishStep onGoToDashboard={onGoToDashboard} onAddAnother={() => {}} defaultPortfolioName="My Portfolio" />);
    const input = screen.getByDisplayValue('My Portfolio');
    fireEvent.change(input, { target: { value: 'Retirement Fund' } });
    fireEvent.click(screen.getByText(/go to dashboard/i));
    expect(onGoToDashboard).toHaveBeenCalledWith('Retirement Fund');
  });

  it('calls onAddAnother when secondary button clicked', () => {
    const onAddAnother = vi.fn();
    render(<FinishStep onGoToDashboard={() => {}} onAddAnother={onAddAnother} />);
    fireEvent.click(screen.getByText(/add another account/i));
    expect(onAddAnother).toHaveBeenCalledOnce();
  });

  it('renders feature tips', () => {
    render(<FinishStep onGoToDashboard={() => {}} onAddAnother={() => {}} />);
    expect(screen.getByText('Holdings')).toBeInTheDocument();
    expect(screen.getByText('Performance')).toBeInTheDocument();
    expect(screen.getByText('Auto Sync')).toBeInTheDocument();
  });

  it('renders hint text about adding accounts later', () => {
    render(<FinishStep onGoToDashboard={() => {}} onAddAnother={() => {}} />);
    expect(screen.getByText(/you can always add more/i)).toBeInTheDocument();
  });
});
