import { useState } from 'react';

function GridIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path d="M3 3h18v18H3zM3 9h18M9 3v18" />
    </svg>
  );
}

function PulseIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}

function SyncIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
    </svg>
  );
}

function ArrowRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

const TIPS = [
  { icon: GridIcon, title: 'Holdings', description: 'View all positions across accounts' },
  { icon: PulseIcon, title: 'Performance', description: 'Track returns with benchmarks' },
  { icon: SyncIcon, title: 'Auto Sync', description: 'Data updates daily automatically' },
];

export function FinishStep({ onGoToDashboard, onAddAnother, defaultPortfolioName = 'My Portfolio' }) {
  const [portfolioName, setPortfolioName] = useState(defaultPortfolioName);

  return (
    <div className="max-w-2xl mx-auto text-center">
      <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
        You&apos;re all set!
      </h2>
      <p className="text-[var(--text-secondary)] text-lg mb-8 max-w-md mx-auto">
        Your portfolio is ready. Rename it if you&apos;d like, then explore your dashboard.
      </p>

      <div className="max-w-xs mx-auto mb-6">
        <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5 text-left">
          Portfolio name
        </label>
        <input
          type="text"
          value={portfolioName}
          onChange={(e) => setPortfolioName(e.target.value)}
          className="w-full px-3 py-2.5 rounded-xl border-2 border-[var(--border-primary)] bg-[var(--bg-primary)] text-sm text-center text-[var(--text-primary)] outline-none focus:border-accent"
        />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        {TIPS.map(({ icon: Icon, title, description }) => (
          <div
            key={title}
            className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-2xl p-5 text-center"
          >
            <div className="size-9 rounded-lg bg-accent-50 dark:bg-accent-900/20 text-accent flex items-center justify-center mx-auto mb-2">
              <Icon className="size-5" />
            </div>
            <h4 className="text-xs font-semibold text-[var(--text-primary)] mb-1">{title}</h4>
            <p className="text-[11px] text-[var(--text-tertiary)] leading-relaxed">{description}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col items-center gap-3">
        <button
          type="button"
          onClick={() => onGoToDashboard(portfolioName)}
          className="inline-flex items-center gap-2 min-w-[260px] justify-center px-7 py-3 rounded-xl text-base font-semibold bg-positive text-white hover:bg-positive-dark transition-colors cursor-pointer"
        >
          Go to Dashboard
          <ArrowRightIcon className="size-4" />
        </button>

        <div className="flex items-center gap-3 w-[260px] text-[var(--text-tertiary)] text-xs">
          <div className="flex-1 h-px bg-[var(--border-primary)]" />
          or
          <div className="flex-1 h-px bg-[var(--border-primary)]" />
        </div>

        <button
          type="button"
          onClick={onAddAnother}
          className="min-w-[260px] px-6 py-2.5 rounded-xl text-sm font-semibold border-2 border-[var(--border-primary)] text-[var(--text-secondary)] hover:border-accent hover:text-accent transition-colors cursor-pointer"
        >
          Add another account
        </button>

        <p className="text-xs text-[var(--text-tertiary)]">
          You can always add more accounts later from the Accounts page
        </p>
      </div>
    </div>
  );
}
