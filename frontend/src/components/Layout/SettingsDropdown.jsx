import { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../../lib';
import { useAuth, useCurrency } from '../../contexts';
import { useClickOutside } from '../../hooks/useClickOutside';

function CogIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}

function ProfileIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}

function ArrowRightStartOnRectangleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15" />
    </svg>
  );
}

function CurrencyIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

export function SettingsDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { user, logout } = useAuth();
  const { currency, setCurrency, supportedCurrencies } = useCurrency();
  const navigate = useNavigate();

  useClickOutside(dropdownRef, useCallback(() => setIsOpen(false), []));

  const handleLogout = async () => {
    setIsOpen(false);
    await logout();
    navigate('/login');
  };

  const handleSettingsClick = () => {
    setIsOpen(false);
    navigate('/settings');
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'p-2 rounded-md transition-colors cursor-pointer',
          'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
          isOpen && 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
        )}
        aria-label="Settings menu"
        aria-expanded={isOpen}
      >
        <ProfileIcon className="w-5 h-5" />
      </button>

      {isOpen && (
        <div className={cn(
          'absolute right-0 mt-2 w-64 rounded-lg shadow-lg',
          'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
          'py-2 z-50'
        )}>
          {user && (
            <>
              <div className="px-4 py-2">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {user.username || user.email}
                </p>
                <p className="text-xs text-[var(--text-tertiary)] truncate">
                  {user.email}
                </p>
              </div>
              <div className="border-t border-[var(--border-primary)] my-1" />
            </>
          )}

          <div className="px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                <CurrencyIcon className="w-4 h-4" />
                <span className="text-sm">Currency</span>
              </div>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className={cn(
                  'bg-[var(--bg-tertiary)] text-sm font-medium text-[var(--text-primary)]',
                  'border border-[var(--border-primary)] rounded-md px-2 py-1',
                  'hover:bg-[var(--bg-primary)] transition-colors cursor-pointer',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent'
                )}
                aria-label="Select display currency"
              >
                {supportedCurrencies.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.code}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="border-t border-[var(--border-primary)] my-1" />

          <button
            onClick={handleSettingsClick}
            className={cn(
              'w-full px-4 py-2 flex items-center gap-3',
              'text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
              'hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer'
            )}
          >
            <CogIcon className="w-4 h-4" />
            <span>Settings</span>
          </button>

          {user && (
            <button
              onClick={handleLogout}
              className={cn(
                'w-full px-4 py-2 flex items-center gap-3',
                'text-sm text-[var(--text-secondary)] hover:text-negative',
                'hover:bg-negative-bg dark:hover:bg-negative-bg-dark/20 transition-colors cursor-pointer'
              )}
            >
              <ArrowRightStartOnRectangleIcon className="w-4 h-4" />
              <span>Log out</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
