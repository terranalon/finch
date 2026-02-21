import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
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
