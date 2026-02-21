import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock contexts
vi.mock('../../../contexts', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, loading: false })),
  usePortfolio: vi.fn(() => ({ refetchPortfolios: vi.fn() })),
}));

// Mock API
vi.mock('../../../lib/api', () => ({
  api: vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })),
}));

// Mock react-router navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

import { OnboardingFlow } from '../OnboardingFlow';

function renderOnboarding() {
  return render(
    <MemoryRouter>
      <OnboardingFlow />
    </MemoryRouter>
  );
}

describe('OnboardingFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders welcome step on initial load', () => {
    renderOnboarding();
    expect(screen.getByText('Welcome to Finch!')).toBeInTheDocument();
  });

  it('shows step indicator with 6 steps', () => {
    renderOnboarding();
    expect(screen.getByText('Welcome')).toBeInTheDocument();
    expect(screen.getByText('Finish')).toBeInTheDocument();
  });

  it('advances to Type step on Get Started click', () => {
    renderOnboarding();
    fireEvent.click(screen.getByText(/get started/i));
    expect(screen.getByText(/what type of account/i)).toBeInTheDocument();
  });
});
