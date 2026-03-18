import { useRef, useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn, formatCurrency } from '../../lib';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { Skeleton } from '../ui';

function ChevronLeftIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

export function AccountStrip({ accounts, loading, currency }) {
  const scrollRef = useRef(null);
  const navigate = useNavigate();
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(false);

  const totalValue = useMemo(
    () => accounts?.reduce((sum, a) => sum + (a.value || 0), 0) || 0,
    [accounts]
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const check = () => {
      setShowLeft(el.scrollLeft > 4);
      setShowRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
    };
    check();
    el.addEventListener('scroll', check, { passive: true });
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => { el.removeEventListener('scroll', check); ro.disconnect(); };
  }, [accounts]);

  const scroll = (dir) => {
    scrollRef.current?.scrollBy({ left: dir * 240, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="flex gap-3 mb-5">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-[88px] w-[220px] flex-shrink-0 rounded-lg" />)}
      </div>
    );
  }

  if (!accounts || accounts.length === 0) return null;

  return (
    <div className="relative mb-5 group">
      {showLeft && (
        <button
          onClick={() => scroll(-1)}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-primary)] flex items-center justify-center text-[var(--text-tertiary)] hover:text-[var(--text-primary)] shadow-sm cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <ChevronLeftIcon />
        </button>
      )}
      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {[...accounts].sort((a, b) => (b.value || 0) - (a.value || 0)).map((account) => {
          const allocationPct = totalValue > 0 ? (account.value / totalValue) * 100 : 0;
          return (
            <div
              key={account.id}
              onClick={() => navigate(`/accounts/${account.id}`)}
              className={cn(
                'flex-shrink-0 w-[220px] p-4 rounded-lg cursor-pointer transition-all',
                'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                'hover:border-[var(--text-faint)] hover:bg-[var(--bg-tertiary)]'
              )}
            >
              <div className="flex items-center gap-2.5 mb-2">
                <BrokerLogo type={account.broker_type} className="w-7 h-7 rounded-md" />
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold truncate">{account.name}</div>
                  <div className="text-[10px] font-medium text-[var(--text-tertiary)] truncate">
                    {account.institution || account.type || 'Account'}
                  </div>
                </div>
              </div>
              <div className="flex items-baseline justify-between">
                <div className="text-[15px] font-bold font-mono tabular-nums">
                  {formatCurrency(account.value, currency)}
                </div>
                <div className="text-[10px] font-mono tabular-nums text-[var(--text-tertiary)]">
                  {allocationPct.toFixed(1)}%
                </div>
              </div>
              {account.holding_count > 0 && (
                <div className="text-[10px] text-[var(--text-tertiary)] mt-1">
                  {account.holding_count} holding{account.holding_count !== 1 ? 's' : ''}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {showRight && (
        <button
          onClick={() => scroll(1)}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-7 h-7 rounded-full bg-[var(--bg-secondary)] border border-[var(--border-primary)] flex items-center justify-center text-[var(--text-tertiary)] hover:text-[var(--text-primary)] shadow-sm cursor-pointer opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <ChevronRightIcon />
        </button>
      )}
    </div>
  );
}
