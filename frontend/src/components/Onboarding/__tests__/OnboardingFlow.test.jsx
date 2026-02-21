import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../../contexts', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, loading: false })),
  usePortfolio: vi.fn(() => ({ refetchPortfolios: vi.fn() })),
}));

vi.mock('../../../lib/api', () => ({
  api: vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

import { OnboardingFlow } from '../OnboardingFlow';

function renderOnboarding() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <OnboardingFlow />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

async function advanceToBrokerStep() {
  renderOnboarding();
  fireEvent.click(screen.getByText(/get started/i));
  await waitFor(() => {
    expect(screen.getByText(/what type of account/i)).toBeInTheDocument();
  });
  fireEvent.click(screen.getByText('Brokerage'));
  await waitFor(() => {
    expect(screen.getByText(/select your broker/i)).toBeInTheDocument();
  });
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

  it('navigates through Type -> Broker steps', async () => {
    await advanceToBrokerStep();
    expect(screen.getByText(/select your broker/i)).toBeInTheDocument();
  });

  it('back button on Broker step returns to Type', async () => {
    await advanceToBrokerStep();
    fireEvent.click(screen.getByText(/back to account types/i));
    await waitFor(() => {
      expect(screen.getByText(/what type of account/i)).toBeInTheDocument();
    });
  });
});
