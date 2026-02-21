import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../../contexts', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, loading: false })),
  usePortfolio: vi.fn(() => ({ refetchPortfolios: vi.fn() })),
}));

vi.mock('../../../lib/api', () => ({
  api: vi.fn(),
}));

import { api } from '../../../lib/api';
import { OnboardingRoute } from '../OnboardingRoute';

function renderOnboardingRoute() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route path="/onboarding" element={<OnboardingRoute />} />
          <Route path="/" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('OnboardingRoute', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders onboarding when user has zero accounts', async () => {
    api.mockResolvedValue({ ok: true, json: () => Promise.resolve({ total: 0, items: [] }) });
    renderOnboardingRoute();
    await waitFor(() => {
      expect(screen.getByText('Welcome to Finch!')).toBeInTheDocument();
    });
  });

  it('redirects to dashboard when user has accounts', async () => {
    api.mockResolvedValue({ ok: true, json: () => Promise.resolve({ total: 1, items: [{ id: 1 }] }) });
    renderOnboardingRoute();
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });
});
