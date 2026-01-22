import { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { cn } from '../../lib';
import { useTheme, useCurrency, useAuth, usePortfolio } from '../../contexts';
import { FinchIcon, ThemeToggle } from '../ui';

/**
 * Settings gear icon
 */
function Cog6ToothIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}

/**
 * Logout icon (arrow right from box)
 */
function ArrowRightStartOnRectangleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15" />
    </svg>
  );
}

/**
 * Currency icon
 */
function CurrencyIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

/**
 * Chevron down icon
 */
function ChevronDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

/**
 * Briefcase icon for portfolio
 */
function BriefcaseIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0M12 12.75h.008v.008H12v-.008Z" />
    </svg>
  );
}

/**
 * Check icon for selected item
 */
function CheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

const navLinks = [
  { to: '/', label: 'Overview' },
  { to: '/holdings', label: 'Holdings' },
  { to: '/activity', label: 'Activity' },
  { to: '/insights', label: 'Insights' },
  { to: '/assets', label: 'Assets' },
  { to: '/accounts', label: 'Accounts' },
];

/**
 * Settings dropdown menu with user info, currency, settings link, and logout
 */
function SettingsDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { user, logout } = useAuth();
  const { currency, setCurrency, supportedCurrencies } = useCurrency();
  const navigate = useNavigate();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
      {/* Settings button */}
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
        <Cog6ToothIcon className="w-5 h-5" />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className={cn(
          'absolute right-0 mt-2 w-64 rounded-lg shadow-lg',
          'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
          'py-2 z-50'
        )}>
          {/* User info */}
          {user && (
            <>
              <div className="px-4 py-2">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {user.name || 'User'}
                </p>
                <p className="text-xs text-[var(--text-tertiary)] truncate">
                  {user.email}
                </p>
              </div>
              <div className="border-t border-[var(--border-primary)] my-1" />
            </>
          )}

          {/* Currency selector */}
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

          {/* Settings link */}
          <button
            onClick={handleSettingsClick}
            className={cn(
              'w-full px-4 py-2 flex items-center gap-3',
              'text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
              'hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer'
            )}
          >
            <Cog6ToothIcon className="w-4 h-4" />
            <span>Settings</span>
          </button>

          {/* Logout */}
          {user && (
            <button
              onClick={handleLogout}
              className={cn(
                'w-full px-4 py-2 flex items-center gap-3',
                'text-sm text-[var(--text-secondary)] hover:text-red-600',
                'hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer'
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

/**
 * Portfolio selector dropdown
 */
function PortfolioSelector() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const { portfolios, selectedPortfolioId, selectedPortfolio, selectPortfolio, showCombinedView, loading } = usePortfolio();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (portfolioId) => {
    selectPortfolio(portfolioId);
    setIsOpen(false);
  };

  // Don't render if loading or no portfolios
  if (loading || portfolios.length === 0) {
    return null;
  }

  const displayName = selectedPortfolio ? selectedPortfolio.name : 'All Portfolios';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg transition-colors cursor-pointer',
          'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
          'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
          isOpen && 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-accent'
        )}
        aria-label="Select portfolio"
        aria-expanded={isOpen}
      >
        <BriefcaseIcon className="w-4 h-4" />
        <span className="text-sm font-medium max-w-[120px] truncate hidden sm:inline">{displayName}</span>
        <ChevronDownIcon className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className={cn(
          'absolute right-0 mt-2 w-56 rounded-lg shadow-lg',
          'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
          'py-2 z-50'
        )}>
          {/* All Portfolios option - only show if user has enabled combined view */}
          {showCombinedView && (
            <>
              <button
                onClick={() => handleSelect(null)}
                className={cn(
                  'w-full px-4 py-2 flex items-center gap-3 text-left',
                  'text-sm hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer',
                  !selectedPortfolioId
                    ? 'text-accent font-medium'
                    : 'text-[var(--text-secondary)]'
                )}
              >
                <span className="flex-1">All Portfolios</span>
                {!selectedPortfolioId && <CheckIcon className="w-4 h-4" />}
              </button>

              {portfolios.length > 0 && (
                <div className="border-t border-[var(--border-primary)] my-1" />
              )}
            </>
          )}

          {/* Individual portfolios */}
          {portfolios.map((portfolio) => {
            // Format total value in portfolio's default currency
            const formattedValue = portfolio.total_value != null
              ? new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency: portfolio.default_currency || 'USD',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                }).format(portfolio.total_value)
              : null;

            return (
              <button
                key={portfolio.id}
                onClick={() => handleSelect(portfolio.id)}
                className={cn(
                  'w-full px-4 py-2 flex items-center gap-2 text-left',
                  'text-sm hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer',
                  selectedPortfolioId === portfolio.id
                    ? 'text-accent font-medium'
                    : 'text-[var(--text-secondary)]'
                )}
              >
                <span className="flex-1 truncate">{portfolio.name}</span>
                {formattedValue && (
                  <span className="text-xs text-[var(--text-tertiary)] font-mono">
                    {formattedValue}
                  </span>
                )}
                {selectedPortfolioId === portfolio.id && (
                  <CheckIcon className="w-4 h-4 flex-shrink-0" />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Main navigation bar for Finch
 */
export function Navbar() {
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="sticky top-0 z-30 bg-[var(--bg-primary)] border-b border-[var(--border-primary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and brand */}
          <div className="flex items-center gap-8">
            <NavLink to="/" className="flex items-center gap-2 text-[var(--text-primary)]">
              <FinchIcon className="size-8 text-accent" />
              <span className="text-xl font-semibold">
                <span className="text-accent">Fin</span>ch
              </span>
            </NavLink>

            {/* Navigation links */}
            <div className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    cn(
                      'px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-accent-light text-accent dark:bg-[var(--accent-light)] dark:text-accent-400'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
                    )
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </div>
          </div>

          {/* Right side actions */}
          <div className="flex items-center gap-2">
            <PortfolioSelector />
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
            <SettingsDropdown />
          </div>
        </div>

        {/* Mobile navigation */}
        <div className="md:hidden pb-3 flex gap-1 overflow-x-auto">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                cn(
                  'px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors',
                  isActive
                    ? 'bg-accent-light text-accent dark:bg-[var(--accent-light)] dark:text-accent-400'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;