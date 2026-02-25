import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('../../contexts', () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, loading: false })),
}));

vi.mock('../../lib/api', () => ({
  api: vi.fn(),
}));

import { api } from '../../lib/api';
import { OnboardingGuard } from '../OnboardingGuard';

function renderWithRouter(initialPath, routes) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>{routes}</Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('OnboardingGuard', () => {
  beforeEach(() => vi.clearAllMocks());

  const ROUTES = [
    <Route key="/" path="/" element={
      <OnboardingGuard><div>Dashboard</div></OnboardingGuard>
    } />,
    <Route key="/onboarding" path="/onboarding" element={<div>Onboarding</div>} />,
  ];

  it('renders children when user has accounts', async () => {
    api.mockResolvedValue({ ok: true, json: () => Promise.resolve({ total: 1, items: [{ id: 1 }] }) });
    renderWithRouter('/', ROUTES);
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  it('redirects to /onboarding when user has zero accounts', async () => {
    api.mockResolvedValue({ ok: true, json: () => Promise.resolve({ total: 0, items: [] }) });
    renderWithRouter('/', ROUTES);
    await waitFor(() => {
      expect(screen.getByText('Onboarding')).toBeInTheDocument();
    });
  });
});
