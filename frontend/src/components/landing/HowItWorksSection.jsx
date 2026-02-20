const STEPS = [
  {
    title: "Connect",
    desc: "Link your broker accounts in seconds. API keys stay encrypted on your device.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="w-[26px] h-[26px] text-[var(--accent-primary)]">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    title: "Sync",
    desc: "Transactions import automatically, every day. No manual work, no missed trades.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="w-[26px] h-[26px] text-[var(--accent-primary)]">
        <path d="M21 2v6h-6" />
        <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
        <path d="M3 22v-6h6" />
        <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
      </svg>
    ),
  },
  {
    title: "Analyze",
    desc: "See your real performance across everything. Benchmark, compare, and grow.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" className="w-[26px] h-[26px] text-[var(--accent-primary)]">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
  },
];

export default function HowItWorksSection() {
  return (
    <section
      id="how-it-works"
      className="lp-fade-up scroll-mt-20 bg-[var(--bg-secondary)] border-y border-[var(--border-primary)] py-24 px-8"
    >
      <div className="max-w-[1200px] mx-auto">
        <div className="text-center mb-14">
          <div className="text-[13px] font-semibold text-[var(--accent-primary)] uppercase tracking-[1.5px] mb-3">
            How It Works
          </div>
          <h2 className="text-[36px] font-bold text-[var(--text-primary)] tracking-[-0.02em] mb-4">
            Three steps to clarity
          </h2>
          <p className="text-[16px] text-[var(--text-secondary)] max-w-[560px] mx-auto leading-relaxed">
            Get your complete portfolio picture in under five minutes.
          </p>
        </div>

        <div className="lp-steps-line grid grid-cols-1 md:grid-cols-3 gap-10 relative">
          {STEPS.map((step) => (
            <div key={step.title} className="text-center relative">
              <div className="w-16 h-16 rounded-full bg-[var(--accent-light)] border-2 border-[var(--accent-primary)] flex items-center justify-center mx-auto mb-5 relative z-10">
                {step.icon}
              </div>
              <h3 className="text-[18px] font-semibold text-[var(--text-primary)] mb-2">
                {step.title}
              </h3>
              <p className="text-[14px] text-[var(--text-secondary)] leading-[1.5] max-w-[260px] mx-auto">
                {step.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
