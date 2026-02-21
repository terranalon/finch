import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
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
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>{routes}</Routes>
    </MemoryRouter>
  );
}

describe('OnboardingGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when user has accounts', async () => {
    api.mockResolvedValue({ ok: true, json: () => Promise.resolve({ total: 1, items: [{ id: 1 }] }) });

    renderWithRouter('/', [
      <Route key="/" path="/" element={
        <OnboardingGuard><div>Dashboard</div></OnboardingGuard>
      } />,
      <Route key="/onboarding" path="/onboarding" element={<div>Onboarding</div>} />,
    ]);

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  it('redirects to /onboarding when user has zero accounts', async () => {
    api.mockResolvedValue({ ok: true, json: () => Promise.resolve({ total: 0, items: [] }) });

    renderWithRouter('/', [
      <Route key="/" path="/" element={
        <OnboardingGuard><div>Dashboard</div></OnboardingGuard>
      } />,
      <Route key="/onboarding" path="/onboarding" element={<div>Onboarding</div>} />,
    ]);

    await waitFor(() => {
      expect(screen.getByText('Onboarding')).toBeInTheDocument();
    });
  });
});
