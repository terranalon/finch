import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';

import { api } from '../lib/api';

export function OnboardingGuard({ children }) {
  const [hasAccounts, setHasAccounts] = useState(null); // null = loading

  useEffect(() => {
    async function checkAccounts() {
      try {
        const response = await api('/accounts');
        if (response.ok) {
          const accounts = await response.json();
          setHasAccounts(accounts.length > 0);
        } else {
          setHasAccounts(true); // On error, don't block dashboard
        }
      } catch {
        setHasAccounts(true);
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

  if (!hasAccounts) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}
