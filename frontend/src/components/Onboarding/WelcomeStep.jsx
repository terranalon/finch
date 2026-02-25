function ChartBarIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path d="M18 20V10M12 20V4M6 20v-6" />
    </svg>
  );
}

function SyncIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
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

function ArrowRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </svg>
  );
}

const FEATURES = [
  { icon: ChartBarIcon, title: 'Unified Dashboard', description: 'See all accounts and assets in a single view' },
  { icon: SyncIcon, title: 'Auto Sync', description: 'Automatic daily imports from connected brokers' },
  { icon: PulseIcon, title: 'True Performance', description: 'Time-weighted returns excluding deposits' },
];

export function WelcomeStep({ onContinue }) {
  return (
    <div className="max-w-2xl mx-auto text-center">
      <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3">
        Welcome to Finch!
      </h2>
      <p className="text-[var(--text-secondary)] text-lg mb-10 max-w-md mx-auto">
        Track all your investments in one place. Connect your broker accounts and get real-time insights into your portfolio performance.
      </p>

      <div className="grid grid-cols-3 gap-4 mb-10">
        {FEATURES.map(({ icon: Icon, title, description }) => (
          <div
            key={title}
            className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-2xl p-5 text-center"
          >
            <div className="size-11 rounded-xl bg-accent-50 dark:bg-accent-900/20 text-accent flex items-center justify-center mx-auto mb-3">
              <Icon className="size-6" />
            </div>
            <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-1">{title}</h4>
            <p className="text-xs text-[var(--text-tertiary)] leading-relaxed">{description}</p>
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={onContinue}
        className="inline-flex items-center gap-2 px-7 py-3 rounded-xl text-base font-semibold bg-accent text-white hover:bg-accent-hover transition-colors cursor-pointer"
      >
        Get Started
        <ArrowRightIcon className="size-4" />
      </button>
    </div>
  );
}
