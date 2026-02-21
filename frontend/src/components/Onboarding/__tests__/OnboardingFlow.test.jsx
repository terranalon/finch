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

describe('OnboardingFlow navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('navigates through Type -> Broker steps', async () => {
    renderOnboarding();

    // Step 1: Welcome
    fireEvent.click(screen.getByText(/get started/i));

    // Step 2: Type - click Brokerage
    await waitFor(() => {
      expect(screen.getByText(/what type of account/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Brokerage'));

    // Step 3: Broker selection should show
    await waitFor(() => {
      expect(screen.getByText(/select your broker/i)).toBeInTheDocument();
    });
  });

  it('back button on Broker step returns to Type', async () => {
    renderOnboarding();
    fireEvent.click(screen.getByText(/get started/i));

    await waitFor(() => {
      expect(screen.getByText(/what type of account/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Brokerage'));

    await waitFor(() => {
      expect(screen.getByText(/select your broker/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText(/back to account types/i));

    await waitFor(() => {
      expect(screen.getByText(/what type of account/i)).toBeInTheDocument();
    });
  });
});
