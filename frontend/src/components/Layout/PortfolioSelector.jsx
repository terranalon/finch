import { useState, useRef, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { cn } from '../../lib';
import { usePortfolio } from '../../contexts';
import { useClickOutside } from '../../hooks/useClickOutside';

function ChevronDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function BriefcaseIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0M12 12.75h.008v.008H12v-.008Z" />
    </svg>
  );
}

function CheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

function AdjustmentsIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75" />
    </svg>
  );
}

export function PortfolioSelector() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();
  const { portfolios, selectedPortfolioId, selectedPortfolio, selectPortfolio, showCombinedView, loading } = usePortfolio();

  useClickOutside(dropdownRef, useCallback(() => setIsOpen(false), []));

  const handleSelect = (portfolioId) => {
    if (portfolioId === selectedPortfolioId) {
      setIsOpen(false);
      return;
    }

    setIsOpen(false);
    selectPortfolio(portfolioId);

    if (location.pathname !== '/') {
      navigate('/');
    }
  };

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

          {[...portfolios].sort((a, b) => Number(b.is_default) - Number(a.is_default)).map((portfolio) => {
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

          <div className="border-t border-[var(--border-primary)] my-1" />
          <button
            onClick={() => { setIsOpen(false); navigate('/portfolios'); }}
            className={cn(
              'w-full px-4 py-2 flex items-center gap-2',
              'text-sm font-medium text-accent hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer'
            )}
          >
            <AdjustmentsIcon className="w-4 h-4" />
            Manage Portfolios
          </button>
        </div>
      )}
    </div>
  );
}
