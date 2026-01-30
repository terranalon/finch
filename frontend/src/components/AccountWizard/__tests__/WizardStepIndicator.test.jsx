import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { WizardStepIndicator } from '../WizardStepIndicator';

describe('WizardStepIndicator', () => {
  it('renders all 5 steps', () => {
    render(
      <WizardStepIndicator
        currentStep={1}
        maxReachedStep={1}
        skippedSteps={[]}
        onStepClick={() => {}}
      />
    );
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Broker')).toBeInTheDocument();
    expect(screen.getByText('Details')).toBeInTheDocument();
    expect(screen.getByText('Connect')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('allows clicking completed steps before current', () => {
    const onStepClick = vi.fn();
    render(
      <WizardStepIndicator
        currentStep={3}
        maxReachedStep={3}
        skippedSteps={[]}
        onStepClick={onStepClick}
      />
    );
    fireEvent.click(screen.getByText('Type'));
    expect(onStepClick).toHaveBeenCalledWith(1);
  });

  it('prevents clicking skipped steps', () => {
    const onStepClick = vi.fn();
    render(
      <WizardStepIndicator
        currentStep={3}
        maxReachedStep={3}
        skippedSteps={[2]}
        onStepClick={onStepClick}
      />
    );
    fireEvent.click(screen.getByText('Broker'));
    expect(onStepClick).not.toHaveBeenCalled();
  });

  it('disables all navigation when on step 5 (terminal)', () => {
    const onStepClick = vi.fn();
    render(
      <WizardStepIndicator
        currentStep={5}
        maxReachedStep={5}
        skippedSteps={[]}
        onStepClick={onStepClick}
      />
    );
    fireEvent.click(screen.getByText('Type'));
    expect(onStepClick).not.toHaveBeenCalled();
  });

  it('prevents clicking steps beyond maxReachedStep', () => {
    const onStepClick = vi.fn();
    render(
      <WizardStepIndicator
        currentStep={2}
        maxReachedStep={2}
        skippedSteps={[]}
        onStepClick={onStepClick}
      />
    );
    fireEvent.click(screen.getByText('Details'));
    expect(onStepClick).not.toHaveBeenCalled();
  });

  it('prevents clicking the current step', () => {
    const onStepClick = vi.fn();
    render(
      <WizardStepIndicator
        currentStep={2}
        maxReachedStep={2}
        skippedSteps={[]}
        onStepClick={onStepClick}
      />
    );
    fireEvent.click(screen.getByText('Broker'));
    expect(onStepClick).not.toHaveBeenCalled();
  });
});
