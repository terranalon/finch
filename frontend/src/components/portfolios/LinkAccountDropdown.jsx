import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { usePortfolioPage } from '../../contexts/PortfolioPageContext';
import { PlusIcon } from './icons';
import { useClickOutside } from '../../hooks/useClickOutside';

export function LinkAccountDropdown({ portfolioId }) {
  const { linkAccount, fetchLinkableAccounts } = usePortfolioPage();
  const [isOpen, setIsOpen] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [linking, setLinking] = useState(null);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  useClickOutside(dropdownRef, useCallback(() => setIsOpen(false), []));

  const handleOpen = async () => {
    setIsOpen(true);
    setLoadingAccounts(true);
    try {
      const data = await fetchLinkableAccounts(portfolioId);
      setAccounts(data);
    } catch {
      setAccounts([]);
    } finally {
      setLoadingAccounts(false);
    }
  };

  const handleLink = async (accountId) => {
    setLinking(accountId);
    await linkAccount(portfolioId, accountId);
    setLinking(null);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={handleOpen}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--text-secondary)] border border-[var(--border-primary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
      >
        <PlusIcon className="w-3.5 h-3.5" />
        Link Account
      </button>

      {isOpen && (
        <div className="absolute left-0 bottom-full mb-1.5 w-64 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg z-40 py-1">
          {loadingAccounts ? (
            <p className="px-4 py-3 text-sm text-[var(--text-tertiary)]">Loading...</p>
          ) : accounts.length === 0 ? (
            <div className="px-4 py-3">
              <p className="text-sm text-[var(--text-secondary)] mb-1">All accounts are already linked.</p>
              <button
                onClick={() => { setIsOpen(false); navigate('/accounts'); }}
                className="text-xs text-accent hover:underline cursor-pointer"
              >
                Manage accounts
              </button>
            </div>
          ) : (
            accounts.map((account) => (
              <button
                key={account.id}
                onClick={() => handleLink(account.id)}
                disabled={linking === account.id}
                className="w-full px-3 py-2 flex items-center gap-2.5 hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer disabled:opacity-50 text-left"
              >
                <BrokerLogo type={account.broker_type} className="size-7 rounded-md object-contain flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-[var(--text-primary)] truncate">{account.name}</p>
                  <p className="text-xs text-[var(--text-tertiary)]">{account.account_type}</p>
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
