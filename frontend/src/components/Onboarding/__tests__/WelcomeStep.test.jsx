import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { WelcomeStep } from '../WelcomeStep';

describe('WelcomeStep', () => {
  it('renders welcome heading', () => {
    render(<WelcomeStep onContinue={() => {}} />);
    expect(screen.getByText('Welcome to Finch!')).toBeInTheDocument();
  });

  it('renders feature cards', () => {
    render(<WelcomeStep onContinue={() => {}} />);
    expect(screen.getByText('Unified Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Auto Sync')).toBeInTheDocument();
    expect(screen.getByText('True Performance')).toBeInTheDocument();
  });

  it('calls onContinue when Get Started is clicked', () => {
    const onContinue = vi.fn();
    render(<WelcomeStep onContinue={onContinue} />);
    fireEvent.click(screen.getByText(/get started/i));
    expect(onContinue).toHaveBeenCalledOnce();
  });
});
