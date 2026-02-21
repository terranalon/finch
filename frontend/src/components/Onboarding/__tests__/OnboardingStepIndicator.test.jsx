import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { OnboardingStepIndicator } from '../OnboardingStepIndicator';

const STEPS = ['Welcome', 'Type', 'Broker', 'Connect', 'Results', 'Finish'];

describe('OnboardingStepIndicator', () => {
  it('renders all step labels', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={1} />);
    STEPS.forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  it('highlights the current step', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={3} />);
    const currentDot = screen.getByText('3');
    expect(currentDot.className).toContain('bg-accent');
  });

  it('marks completed steps with a checkmark instead of number', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} />);
    expect(screen.queryByText('1')).not.toBeInTheDocument();
    expect(screen.queryByText('2')).not.toBeInTheDocument();
    expect(screen.queryByText('3')).not.toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('calls onStepClick when a completed step is clicked', () => {
    const onStepClick = vi.fn();
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} onStepClick={onStepClick} />);

    fireEvent.click(screen.getByText('Welcome'));
    expect(onStepClick).toHaveBeenCalledWith(1);

    fireEvent.click(screen.getByText('Broker'));
    expect(onStepClick).toHaveBeenCalledWith(3);
  });

  it('does not render a button for the current step', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} onStepClick={vi.fn()} />);
    expect(screen.getByText('Connect').closest('button')).toBeNull();
  });

  it('does not render buttons when no onStepClick handler is provided', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} />);
    expect(screen.getByText('Welcome').closest('button')).toBeNull();
  });
});
