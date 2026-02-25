import { Navigate } from 'react-router-dom';

import { useHasAccounts } from '../hooks/useHasAccounts';

export function OnboardingGuard({ children }) {
  const hasAccounts = useHasAccounts(true);

  if (hasAccounts === null) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    );
  }

  if (!hasAccounts) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}
