function UnifiedDashboardMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div className="text-center pb-2.5 mb-2.5 border-b border-[var(--bg-tertiary)]">
        <div style={{ fontSize: "10px", color: "#94A3B8", marginBottom: "2px" }}>Total Portfolio Value</div>
        <div className="font-numeric" style={{ fontSize: "20px", fontWeight: 700, color: "#0F172A" }}>$247,832.15</div>
        <div className="font-numeric" style={{ fontSize: "11px", color: "#059669", marginTop: "2px" }}>+$1,247.33 (+0.51%) today</div>
      </div>
      <div>
        <div style={{ display: "flex", height: "8px", borderRadius: "4px", overflow: "hidden", marginBottom: "8px" }}>
          <div style={{ width: "38%", background: "#2563EB" }} />
          <div style={{ width: "22%", background: "#60A5FA" }} />
          <div style={{ width: "32%", background: "#F59E0B" }} />
          <div style={{ width: "8%", background: "#94A3B8" }} />
        </div>
        <div style={{ display: "flex", gap: "12px", fontSize: "10px", color: "#475569" }}>
          <span><span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: "#2563EB", marginRight: "3px" }} />Stock 38%</span>
          <span><span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: "#60A5FA", marginRight: "3px" }} />ETF 22%</span>
          <span><span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: "#F59E0B", marginRight: "3px" }} />Crypto 32%</span>
          <span><span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: "#94A3B8", marginRight: "3px" }} />Cash 8%</span>
        </div>
      </div>
    </div>
  );
}

function AutoSyncMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
        <div style={{ width: "5px", height: "5px", borderRadius: "50%", background: "#2563EB" }} />
        <span style={{ fontSize: "10px", fontWeight: 600, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.5px" }}>Feb 19, 2026</span>
      </div>
      {[
        { badge: "BUY", badgeBg: "#D1FAE5", badgeColor: "#059669", text: <>Bought <strong>50</strong> MSFT at $415.20</>, amount: "-$20,760", amountColor: "#DC2626" },
        { badge: "DIV", badgeBg: "#DBEAFE", badgeColor: "#2563EB", text: <>Dividend from <strong>AAPL</strong></>, amount: "+$96.00", amountColor: "#059669" },
        { badge: "SELL", badgeBg: "#FEE2E2", badgeColor: "#DC2626", text: <>Sold <strong>0.5</strong> BTC at $96,420</>, amount: "+$48,210", amountColor: "#059669" },
      ].map((row, i, arr) => (
        <div key={row.badge + i} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 0", borderBottom: i < arr.length - 1 ? "1px solid #F1F5F9" : "none" }}>
          <span style={{ fontSize: "9px", fontWeight: 600, padding: "2px 6px", borderRadius: "9999px", background: row.badgeBg, color: row.badgeColor }}>{row.badge}</span>
          <span style={{ fontSize: "11px", color: "#0F172A", flex: 1 }}>{row.text}</span>
          <span className="font-numeric" style={{ fontSize: "11px", color: row.amountColor }}>{row.amount}</span>
        </div>
      ))}
    </div>
  );
}

function PerformanceMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div style={{ display: "flex", gap: "6px", marginBottom: "10px" }}>
        <span style={{ fontSize: "10px", fontWeight: 600, padding: "2px 8px", borderRadius: "4px", background: "#DBEAFE", color: "#2563EB" }}>By Period</span>
        <span style={{ fontSize: "10px", fontWeight: 500, padding: "2px 8px", borderRadius: "4px", color: "#94A3B8" }}>By Asset Class</span>
      </div>
      {[
        { label: "YTD", value: "+18.7%", width: "75%", color: "#059669" },
        { label: "1Y", value: "+32.4%", width: "90%", color: "#059669" },
        { label: "S&P 500 (YTD)", value: "+12.3%", width: "50%", color: "#94A3B8", muted: true },
      ].map((row) => (
        <div key={row.label} style={{ marginBottom: row.muted ? 0 : "6px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "3px" }}>
            <span style={{ color: row.muted ? "#94A3B8" : "#475569" }}>{row.label}</span>
            <span className="font-numeric" style={{ color: row.color, fontWeight: 500 }}>{row.value}</span>
          </div>
          <div style={{ height: "6px", background: "#F1F5F9", borderRadius: "3px", overflow: "hidden" }}>
            <div style={{ width: row.width, height: "100%", background: row.muted ? "#CBD5E1" : "#059669", borderRadius: "3px" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function AssetInsightsMockup() {
  return (
    <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg p-3.5 text-xs">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px", paddingBottom: "8px", borderBottom: "1px solid #F1F5F9" }}>
        <div>
          <span style={{ fontWeight: 700, color: "#0F172A", fontSize: "13px" }}>AAPL</span>
          <span style={{ color: "#94A3B8", fontSize: "10px", marginLeft: "4px" }}>Stock</span>
        </div>
        <div className="font-numeric" style={{ fontSize: "13px", fontWeight: 600, color: "#0F172A" }}>$240.15</div>
      </div>
      <div style={{ marginBottom: "8px" }}>
        <svg viewBox="0 0 200 40" style={{ width: "100%", height: "32px" }} preserveAspectRatio="none">
          <defs>
            <linearGradient id="feat-asset-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#059669" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#059669" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0,32 C20,30 40,28 60,24 C80,20 100,26 120,18 C140,10 160,14 180,8 C190,6 200,4 200,4 L200,40 L0,40Z" fill="url(#feat-asset-grad)" />
          <path d="M0,32 C20,30 40,28 60,24 C80,20 100,26 120,18 C140,10 160,14 180,8 C190,6 200,4 200,4" fill="none" stroke="#059669" strokeWidth="1.5" />
        </svg>
        <div style={{ display: "flex", gap: "6px" }}>
          {["1W", "1M", "3M", "1Y"].map((period) => (
            <span
              key={period}
              style={{
                fontSize: "9px", fontWeight: 600, padding: "1px 6px", borderRadius: "3px",
                background: period === "1M" ? "#DBEAFE" : "#F1F5F9",
                color: period === "1M" ? "#2563EB" : "#94A3B8",
              }}
            >
              {period}
            </span>
          ))}
        </div>
      </div>
      <div style={{ fontSize: "10px", color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "4px", fontWeight: 600 }}>Your Holdings</div>
      {[
        { label: "Quantity", value: "142.5" },
        { label: "Market Value", value: "$34,221.38" },
        { label: "P&L", value: "+$5,316.88 (+18.4%)", color: "#059669" },
      ].map((row) => (
        <div key={row.label} style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", padding: "3px 0" }}>
          <span style={{ color: "#475569" }}>{row.label}</span>
          <span className="font-numeric" style={{ color: row.color ?? "#0F172A", fontWeight: 500 }}>{row.value}</span>
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
