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

  it('marks completed steps with a checkmark', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} />);
    // Steps 1-3 should be completed (show checkmark SVG, not number)
    expect(screen.queryByText('1')).not.toBeInTheDocument();
    expect(screen.queryByText('2')).not.toBeInTheDocument();
    expect(screen.queryByText('3')).not.toBeInTheDocument();
    // Step 4 should show number
    expect(screen.getByText('4')).toBeInTheDocument();
  });
});

describe('OnboardingStepIndicator — clickable steps', () => {
  it('calls onStepClick with the correct step number when a completed step is clicked', () => {
    const onStepClick = vi.fn();
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} onStepClick={onStepClick} />);
    // Step 1 label is visible and completed — click it
    fireEvent.click(screen.getByText('Welcome'));
    expect(onStepClick).toHaveBeenCalledWith(1);
  });

  it('calls onStepClick with the correct number for any completed step', () => {
    const onStepClick = vi.fn();
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} onStepClick={onStepClick} />);
    fireEvent.click(screen.getByText('Broker'));
    expect(onStepClick).toHaveBeenCalledWith(3);
  });

  it('does not render a button for the current step', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} onStepClick={vi.fn()} />);
    // 'Connect' is step 4 (current) — should not be a button
    const connectLabel = screen.getByText('Connect');
    expect(connectLabel.closest('button')).toBeNull();
  });

  it('does not call onStepClick when no handler is provided', () => {
    render(<OnboardingStepIndicator steps={STEPS} currentStep={4} />);
    // No onStepClick — completed steps should not be buttons
    const welcomeLabel = screen.getByText('Welcome');
    expect(welcomeLabel.closest('button')).toBeNull();
  });
});
