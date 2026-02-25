import { Navigate } from 'react-router-dom';

import { useHasAccounts } from '../../hooks/useHasAccounts';
import { OnboardingFlow } from './OnboardingFlow';

export function OnboardingRoute() {
  const hasAccounts = useHasAccounts(false);

  if (hasAccounts === null) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent" />
      </div>
    );
  }

  if (hasAccounts) {
    return <Navigate to="/" replace />;
  }

  return <OnboardingFlow />;
}
