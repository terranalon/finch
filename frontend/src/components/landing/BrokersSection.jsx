const BROKER_CATEGORIES = [
  {
    label: "International Brokers",
    brokers: [
      {
        name: "Interactive Brokers",
        icon: (
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="4" y="8" width="20" height="12" rx="2" stroke="#475569" strokeWidth="1.5" />
            <path d="M9 14h4M17 11v6" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "Israeli Brokers",
    brokers: [
      {
        name: "Meitav",
        icon: (
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="8" stroke="#475569" strokeWidth="1.5" />
            <path d="M10 14h8M14 10v8" stroke="#475569" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        ),
      },
      {
        name: "Bit2C",
        icon: (
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <path d="M8 8h12v12H8z" stroke="#475569" strokeWidth="1.5" />
            <path d="M12 8v12M8 14h12" stroke="#475569" strokeWidth="1.5" />
          </svg>
        ),
      },
    ],
  },
  {
    label: "Crypto Exchanges",
    brokers: [
      {
        name: "Kraken",
        icon: (
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <path d="M14 4L6 20h4l4-8 4 8h4L14 4z" stroke="#475569" strokeWidth="1.5" strokeLinejoin="round" />
          </svg>
        ),
      },
      {
        name: "Binance",
        icon: (
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <path d="M14 6L8 10v8l6 4 6-4v-8l-6-4z" stroke="#475569" strokeWidth="1.5" strokeLinejoin="round" />
            <path d="M14 14v8M8 10l6 4 6-4" stroke="#475569" strokeWidth="1.5" />
          </svg>
        ),
      },
    ],
  },
];

export default function BrokersSection() {
  return (
    <section
      id="integrations"
      className="lp-fade-up scroll-mt-20 bg-[var(--bg-secondary)] border-y border-[var(--border-primary)] py-14 px-8"
    >
      <div className="max-w-[1200px] mx-auto text-center">
        <div className="text-[14px] font-medium text-[var(--text-tertiary)] uppercase tracking-[1.5px] mb-10">
          Connect your favorite brokers and exchanges
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-[900px] mx-auto">
          {BROKER_CATEGORIES.map((cat) => (
            <div key={cat.label}>
              <div className="text-[12px] font-semibold text-[var(--text-secondary)] uppercase tracking-[0.8px] mb-5 pb-3 border-b border-[var(--border-primary)]">
                {cat.label}
              </div>
              <div className="flex items-start justify-center gap-6 flex-wrap">
                {cat.brokers.map((broker) => (
                  <div
                    key={broker.name}
                    className="flex flex-col items-center gap-2.5"
                  >
                    <div className="w-14 h-14 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)] flex items-center justify-center hover:border-[var(--accent-primary)] hover:ring-[3px] hover:ring-[var(--accent-light)] transition-all cursor-default">
                      {broker.icon}
                    </div>
                    <span className="text-[12px] font-medium text-[var(--text-secondary)]">
                      {broker.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
