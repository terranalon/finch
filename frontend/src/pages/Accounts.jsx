/**
 * Accounts Page - Grid card layout with allocation strip and detail sidebar.
 *
 * API endpoints (via useAccountsData hook):
 * - GET /api/accounts
 * - GET /api/dashboard/summary
 * - GET /api/positions
 */

import { useState, useEffect } from 'react';
import { api } from '../lib';
import { usePortfolio } from '../contexts';
import { useAccountsData } from '../hooks/useAccountsData';
import { PageContainer } from '../components/layout';
import { Skeleton } from '../components/ui';
import { AllocationStrip, AccountGrid, AccountSidebar } from '../components/accounts';
import { AccountWizard } from '../components/AccountWizard';
import { PlusIcon } from '../components/accounts/icons';

export default function Accounts() {
  const { selectedPortfolioId } = usePortfolio();
  const {
    accounts, accountHoldings, totalValue,
    loading, error, currency, refresh,
  } = useAccountsData();

  const [selectedAccount, setSelectedAccount] = useState(null);
  const [showWizard, setShowWizard] = useState(false);
  const [linkableAccounts, setLinkableAccounts] = useState([]);

  // Derive live account from accounts array to avoid stale snapshot after refresh
  const liveSelectedAccount = selectedAccount
    ? accounts.find((a) => a.id === selectedAccount.id) ?? null
    : null;

  // Fetch linkable accounts when wizard opens
  useEffect(() => {
    if (showWizard && selectedPortfolioId) {
      api(`/portfolios/${selectedPortfolioId}/linkable-accounts`)
        .then((res) => (res.ok ? res.json() : []))
        .then((data) => setLinkableAccounts(data))
        .catch(() => setLinkableAccounts([]));
    }
  }, [showWizard, selectedPortfolioId]);

  const handleCardClick = (account) => setSelectedAccount(account);
  const handleCloseSidebar = () => setSelectedAccount(null);
  const handleAddAccount = () => setShowWizard(true);

  // Throws on failure so the sidebar can surface the error to the user.
  // Uses unlink endpoint for accounts shared across multiple portfolios.
  const handleDelete = async (accountId) => {
    const account = accounts.find((a) => a.id === accountId);
    const isShared = (account?.portfolio_ids?.length ?? 0) > 1;
    const endpoint = isShared && selectedPortfolioId
      ? `/portfolios/${selectedPortfolioId}/accounts/${accountId}`
      : `/accounts/${accountId}`;

    const res = await api(endpoint, { method: 'DELETE' });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.message || 'Failed to delete account');
    }
    setSelectedAccount(null);
    refresh();
  };

  // Throws on failure so the sidebar can surface the error to the user.
  const handleRename = async (accountId, newName) => {
    const res = await api(`/accounts/${accountId}`, {
      method: 'PUT',
      body: JSON.stringify({ name: newName }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.message || 'Failed to rename account');
    }
    refresh();
  };

  if (loading) {
    return (
      <PageContainer className="mx-0 max-w-none">
        <div className="flex items-start justify-between mb-5">
          <div>
            <h1 className="text-[22px] font-bold tracking-[-0.3px] text-[var(--text-primary)]">Accounts</h1>
            <Skeleton className="h-4 w-32 mt-1" />
          </div>
          <Skeleton className="h-9 w-32 rounded-lg" />
        </div>
        <AllocationStrip loading />
        <div className="grid grid-cols-[repeat(auto-fill,minmax(340px,1fr))] gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-[220px] w-full rounded-xl" />
          ))}
        </div>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer className="mx-0 max-w-none">
        <h1 className="text-[22px] font-bold tracking-[-0.3px] text-[var(--text-primary)] mb-5">Accounts</h1>
        <div className="text-center py-12">
          <p className="text-[var(--negative)] mb-2">Error loading accounts</p>
          <p className="text-[var(--text-secondary)] text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:bg-[var(--accent-hover)] transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer className="mx-0 max-w-none">
      {/* Title bar */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h1 className="text-[22px] font-bold tracking-[-0.3px] text-[var(--text-primary)]">
            Accounts
          </h1>
          <p className="text-[13px] text-[var(--text-tertiary)] mt-0.5">
            {accounts.length} account{accounts.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={handleAddAccount}
          className="flex items-center gap-1.5 px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg text-[13px] font-semibold hover:bg-[var(--accent-hover)] transition-colors cursor-pointer whitespace-nowrap"
        >
          <PlusIcon className="w-4 h-4" />
          Add Account
        </button>
      </div>

      {/* Allocation strip */}
      {accounts.length > 0 && (
        <AllocationStrip
          accounts={accounts}
          totalValue={totalValue}
          currency={currency}
        />
      )}

      {/* Account grid */}
      {accounts.length === 0 ? (
        <EmptyState onAddAccount={handleAddAccount} />
      ) : (
        <AccountGrid
          accounts={accounts}
          accountHoldings={accountHoldings}
          currency={currency}
          onCardClick={handleCardClick}
          onAddAccount={handleAddAccount}
        />
      )}

      {/* Account detail sidebar */}
      <AccountSidebar
        account={liveSelectedAccount}
        holdings={liveSelectedAccount ? accountHoldings.get(liveSelectedAccount.id) || [] : []}
        currency={currency}
        onClose={handleCloseSidebar}
        onDelete={handleDelete}
        onRename={handleRename}
      />

      {/* Account creation wizard */}
      <AccountWizard
        isOpen={showWizard}
        onClose={() => {
          setShowWizard(false);
          refresh();
        }}
        portfolioId={selectedPortfolioId}
        linkableAccounts={linkableAccounts}
        existingAccountNames={accounts.map((a) => a.name)}
      />
    </PageContainer>
  );
}

function EmptyState({ onAddAccount }) {
  return (
    <div className="text-center py-16">
      <div className="inline-flex p-4 rounded-full bg-[var(--bg-secondary)] mb-4">
        <svg className="w-12 h-12 text-[var(--text-tertiary)]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-[var(--text-primary)]">No accounts yet</h3>
      <p className="text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
        Add your first investment account to start tracking your portfolio.
      </p>
      <button
        onClick={onAddAccount}
        className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--accent-primary)] text-white hover:bg-[var(--accent-hover)] transition-colors cursor-pointer"
      >
        <PlusIcon className="w-4 h-4" />
        Add Account
      </button>
    </div>
  );
}
