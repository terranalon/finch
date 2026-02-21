import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';

import { api } from '../../lib/api';
import { OnboardingFlow } from './OnboardingFlow';

export function OnboardingRoute() {
  const [hasAccounts, setHasAccounts] = useState(null);

  useEffect(() => {
    async function checkAccounts() {
      try {
        const response = await api('/accounts');
        if (response.ok) {
          const data = await response.json();
          setHasAccounts(data.total > 0);
        } else {
          setHasAccounts(false);
        }
      } catch {
        setHasAccounts(false);
      }
    }
    checkAccounts();
  }, []);

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
