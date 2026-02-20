const ALLOCATION_SEGMENTS = [
  { width: "38%", color: "#2563EB", label: "Stock 38%" },
  { width: "22%", color: "#60A5FA", label: "ETF 22%" },
  { width: "32%", color: "#F59E0B", label: "Crypto 32%" },
  { width: "8%", color: "#94A3B8", label: "Cash 8%" },
];

const TRANSACTIONS = [
  { badge: "BUY", badgeBg: "#D1FAE5", badgeColor: "#059669", text: <>Bought <strong>50</strong> MSFT at $415.20</>, amount: "-$20,760", amountColor: "#DC2626" },
  { badge: "DIV", badgeBg: "#DBEAFE", badgeColor: "#2563EB", text: <>Dividend from <strong>AAPL</strong></>, amount: "+$96.00", amountColor: "#059669" },
  { badge: "SELL", badgeBg: "#FEE2E2", badgeColor: "#DC2626", text: <>Sold <strong>0.5</strong> BTC at $96,420</>, amount: "+$48,210", amountColor: "#059669" },
];

const PERFORMANCE_ROWS = [
  { label: "YTD", value: "+18.7%", width: "75%", color: "#059669" },
  { label: "1Y", value: "+32.4%", width: "90%", color: "#059669" },
  { label: "S&P 500 (YTD)", value: "+12.3%", width: "50%", color: "#94A3B8", muted: true },
];

const HOLDINGS_ROWS = [
  { label: "Quantity", value: "142.5" },
  { label: "Market Value", value: "$34,221.38" },
  { label: "P&L", value: "+$5,316.88 (+18.4%)", color: "#059669" },
];

function UnifiedDashboardMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div className="text-center pb-2.5 mb-2.5 border-b border-[var(--bg-tertiary)]">
        <div className="text-[10px] text-[#94A3B8] mb-0.5">Total Portfolio Value</div>
        <div className="font-numeric text-[20px] font-bold text-[#0F172A]">$247,832.15</div>
        <div className="font-numeric text-[11px] text-[#059669] mt-0.5">+$1,247.33 (+0.51%) today</div>
      </div>
      <div>
        <div className="flex h-2 rounded overflow-hidden mb-2">
          {ALLOCATION_SEGMENTS.map((seg) => (
            <div key={seg.label} style={{ width: seg.width, background: seg.color }} />
          ))}
        </div>
        <div className="flex gap-3 text-[10px] text-[#475569]">
          {ALLOCATION_SEGMENTS.map((seg) => (
            <span key={seg.label}>
              <span
                className="inline-block w-1.5 h-1.5 rounded-full mr-[3px]"
                style={{ background: seg.color }}
              />
              {seg.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function AutoSyncMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div className="flex items-center gap-1.5 mb-2">
        <div className="w-[5px] h-[5px] rounded-full bg-[#2563EB]" />
        <span className="text-[10px] font-semibold text-[#94A3B8] uppercase tracking-[0.5px]">Feb 19, 2026</span>
      </div>
      {TRANSACTIONS.map((row, i) => (
        <div
          key={row.badge + i}
          className={`flex items-center gap-2 py-1.5 ${
            i < TRANSACTIONS.length - 1 ? "border-b border-[#F1F5F9]" : ""
          }`}
        >
          <span
            className="text-[9px] font-semibold px-1.5 py-px rounded-full"
            style={{ background: row.badgeBg, color: row.badgeColor }}
          >
            {row.badge}
          </span>
          <span className="text-[11px] text-[#0F172A] flex-1">{row.text}</span>
          <span className="font-numeric text-[11px]" style={{ color: row.amountColor }}>{row.amount}</span>
        </div>
      ))}
    </div>
  );
}

function PerformanceMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div className="flex gap-1.5 mb-2.5">
        <span className="text-[10px] font-semibold px-2 py-px rounded bg-[#DBEAFE] text-[#2563EB]">By Period</span>
        <span className="text-[10px] font-medium px-2 py-px rounded text-[#94A3B8]">By Asset Class</span>
      </div>
      {PERFORMANCE_ROWS.map((row) => (
        <div key={row.label} className={row.muted ? "" : "mb-1.5"}>
          <div className="flex justify-between text-[11px] mb-[3px]">
            <span className={row.muted ? "text-[#94A3B8]" : "text-[#475569]"}>{row.label}</span>
            <span className="font-numeric font-medium" style={{ color: row.color }}>{row.value}</span>
          </div>
          <div className="h-1.5 bg-[#F1F5F9] rounded-[3px] overflow-hidden">
            <div
              className="h-full rounded-[3px]"
              style={{ width: row.width, background: row.muted ? "#CBD5E1" : "#059669" }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function AssetInsightsMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div className="flex items-center justify-between mb-2 pb-2 border-b border-[#F1F5F9]">
        <div>
          <span className="font-bold text-[#0F172A] text-[13px]">AAPL</span>
          <span className="text-[#94A3B8] text-[10px] ml-1">Stock</span>
        </div>
        <div className="font-numeric text-[13px] font-semibold text-[#0F172A]">$240.15</div>
      </div>
      <div className="mb-2">
        <svg viewBox="0 0 200 40" className="w-full h-8" preserveAspectRatio="none">
          <defs>
            <linearGradient id="feat-asset-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#059669" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#059669" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0,32 C20,30 40,28 60,24 C80,20 100,26 120,18 C140,10 160,14 180,8 C190,6 200,4 200,4 L200,40 L0,40Z" fill="url(#feat-asset-grad)" />
          <path d="M0,32 C20,30 40,28 60,24 C80,20 100,26 120,18 C140,10 160,14 180,8 C190,6 200,4 200,4" fill="none" stroke="#059669" strokeWidth="1.5" />
        </svg>
        <div className="flex gap-1.5">
          {["1W", "1M", "3M", "1Y"].map((period) => (
            <span
              key={period}
              className={`text-[9px] font-semibold px-1.5 py-px rounded-[3px] ${
                period === "1M"
                  ? "bg-[#DBEAFE] text-[#2563EB]"
                  : "bg-[#F1F5F9] text-[#94A3B8]"
              }`}
            >
              {period}
            </span>
          ))}
        </div>
      </div>
      <div className="text-[10px] text-[#94A3B8] uppercase tracking-[0.5px] mb-1 font-semibold">Your Holdings</div>
      {HOLDINGS_ROWS.map((row) => (
        <div key={row.label} className="flex justify-between text-[11px] py-[3px]">
          <span className="text-[#475569]">{row.label}</span>
          <span className="font-numeric font-medium" style={{ color: row.color ?? "#0F172A" }}>{row.value}</span>
        </div>
      ))}
    </div>
  );
}

const FEATURES = [
  {
    title: "Unified Dashboard",
    desc: "See all your investments in one place -- stocks, crypto, bonds -- across every broker.",
    mockup: <UnifiedDashboardMockup />,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    title: "Automatic Sync",
    desc: "Transactions flow in automatically. No CSV uploads, no manual entry, no missed trades.",
    mockup: <AutoSyncMockup />,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M21 2v6h-6" />
        <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
        <path d="M3 22v-6h6" />
        <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
      </svg>
    ),
  },
  {
    title: "Performance Analytics",
    desc: "True time-weighted returns. Benchmark against S&P 500. Know exactly how you're doing.",
    mockup: <PerformanceMockup />,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
  },
  {
    title: "Asset-Level Insights",
    desc: "Drill into any holding -- price history, allocation weight, return attribution.",
    mockup: <AssetInsightsMockup />,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="11" cy="11" r="8" />
        <path d="M21 21l-4.35-4.35" />
        <path d="M11 8v6M8 11h6" />
      </svg>
    ),
  },
];

export default function FeaturesSection() {
  return (
    <section
      id="features"
      className="lp-fade-up scroll-mt-20 py-24 px-8 max-w-[1200px] mx-auto"
    >
      <div className="text-center mb-14">
        <div className="text-[13px] font-semibold text-[var(--accent-primary)] uppercase tracking-[1.5px] mb-3">
          Features
        </div>
        <h2 className="text-[36px] font-bold text-[var(--text-primary)] tracking-[-0.02em] mb-4">
          Everything you need to track smarter
        </h2>
        <p className="text-[16px] text-[var(--text-secondary)] max-w-[560px] mx-auto leading-relaxed">
          Built for investors who use multiple brokers and want the full
          picture -- without the spreadsheet gymnastics.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {FEATURES.map((feat) => (
          <div
            key={feat.title}
            className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg p-6 hover:border-[var(--accent-primary)] hover:-translate-y-0.5 hover:shadow-lg transition-all"
          >
            <div className="w-10 h-10 rounded-lg bg-[var(--accent-light)] flex items-center justify-center mb-4 text-[var(--accent-primary)] [&>svg]:w-5 [&>svg]:h-5">
              {feat.icon}
            </div>
            <h3 className="text-[18px] font-semibold text-[var(--text-primary)] mb-2">
              {feat.title}
            </h3>
            <p className="text-[14px] leading-relaxed text-[var(--text-secondary)] mb-5">
              {feat.desc}
            </p>
            {feat.mockup}
          </div>
        ))}
      </div>
    </section>
  );
}
