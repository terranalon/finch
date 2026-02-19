import { Link } from "react-router-dom";

function DashboardMockup() {
  return (
    <div className="lp-mockup-3d bg-white border border-[var(--border-primary)] rounded-lg overflow-hidden">
      {/* Browser chrome */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-[var(--bg-secondary)] border-b border-[var(--border-primary)]">
        <div className="w-2.5 h-2.5 rounded-full bg-[#FCA5A5]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#FCD34D]" />
        <div className="w-2.5 h-2.5 rounded-full bg-[#6EE7B7]" />
      </div>

      {/* Mockup body */}
      <div className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <div className="font-numeric text-[28px] font-bold text-[var(--text-primary)] leading-tight">
              $247,832.15
            </div>
            <div className="font-numeric text-sm font-semibold text-[#059669] mt-1">
              +$1,247.33 (+0.51%)
            </div>
          </div>
          <div className="flex gap-2">
            <span className="text-[11px] font-medium px-2.5 py-1 rounded-md bg-[var(--accent-light)] text-[var(--accent-primary)] border border-[var(--accent-primary)]">
              All
            </span>
            <span className="text-[11px] font-medium px-2.5 py-1 rounded-md bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-primary)]">
              IBKR
            </span>
            <span className="text-[11px] font-medium px-2.5 py-1 rounded-md bg-[var(--bg-tertiary)] text-[var(--text-secondary)] border border-[var(--border-primary)]">
              Kraken
            </span>
          </div>
        </div>

        {/* Chart */}
        <div className="mb-5 h-[100px]">
          <svg
            viewBox="0 0 500 100"
            preserveAspectRatio="none"
            className="w-full h-full"
          >
            <defs>
              <linearGradient id="hero-chartGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2563EB" stopOpacity="0.15" />
                <stop offset="100%" stopColor="#2563EB" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path
              d="M0,80 C30,75 60,70 90,65 C120,60 150,55 180,45 C210,35 240,50 270,42 C300,34 330,28 360,22 C390,16 420,20 450,15 C480,10 500,8 500,8 L500,100 L0,100Z"
              fill="url(#hero-chartGrad)"
            />
            <path
              d="M0,80 C30,75 60,70 90,65 C120,60 150,55 180,45 C210,35 240,50 270,42 C300,34 330,28 360,22 C390,16 420,20 450,15 C480,10 500,8 500,8"
              fill="none"
              stroke="#2563EB"
              strokeWidth="2.5"
            />
          </svg>
        </div>

        {/* Holdings table */}
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-left text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wide py-2 border-b border-[var(--border-primary)]">
                Asset
              </th>
              <th className="text-left text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wide py-2 border-b border-[var(--border-primary)]">
                Shares
              </th>
              <th className="text-left text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wide py-2 border-b border-[var(--border-primary)]">
                Value
              </th>
              <th className="text-right text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wide py-2 border-b border-[var(--border-primary)]">
                Return
              </th>
            </tr>
          </thead>
          <tbody>
            {[
              { icon: "A", bg: "#333", ticker: "AAPL", shares: "142.5", value: "$34,218.75", ret: "+18.4%", gain: true },
              { icon: "M", bg: "#0078D4", ticker: "MSFT", shares: "85.0", value: "$35,275.00", ret: "+24.1%", gain: true },
              { icon: "B", bg: "#F7931A", ticker: "BTC", shares: "1.847", value: "$178,120.40", ret: "+142.3%", gain: true },
              { icon: "E", bg: "#627EEA", ticker: "ETH", shares: "3.21", value: "$8,718.00", ret: "-5.2%", gain: false },
            ].map((row) => (
              <tr key={row.ticker}>
                <td className="text-[13px] py-2.5 border-b border-[var(--bg-secondary)] text-[var(--text-primary)]">
                  <span className="flex items-center gap-2 font-semibold">
                    <span
                      className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                      style={{ background: row.bg }}
                    >
                      {row.icon}
                    </span>
                    {row.ticker}
                  </span>
                </td>
                <td className="font-numeric text-[13px] py-2.5 border-b border-[var(--bg-secondary)] text-[var(--text-primary)]">
                  {row.shares}
                </td>
                <td className="font-numeric text-[13px] py-2.5 border-b border-[var(--bg-secondary)] text-[var(--text-primary)]">
                  {row.value}
                </td>
                <td
                  className={`font-numeric text-[13px] py-2.5 border-b border-[var(--bg-secondary)] text-right font-medium ${
                    row.gain ? "text-[#059669]" : "text-[#DC2626]"
                  }`}
                >
                  {row.ret}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function HeroSection() {
  return (
    <div className="lp-hero-glow">
      <section className="grid grid-cols-1 lg:grid-cols-[1fr_1.15fr] gap-16 items-center max-w-[1200px] mx-auto px-8 pt-24 pb-20">
        {/* Left: text content */}
        <div className="lp-fade-up max-w-[520px]">
          <h1 className="text-[54px] max-sm:text-[32px] sm:text-[38px] lg:text-[54px] font-bold leading-[1.08] text-[var(--text-primary)] tracking-[-0.025em] mb-6">
            Know your{" "}
            <span className="text-[var(--accent-primary)]">real</span>{" "}
            performance.
          </h1>
          <p className="text-[18px] leading-[1.7] text-[var(--text-secondary)] mb-9">
            Finch connects to your brokers, imports transactions automatically,
            and shows you what spreadsheets never could.
          </p>
          <div className="flex max-sm:flex-col gap-3.5">
            <Link
              to="/register"
              className="inline-flex items-center justify-center bg-[var(--accent-primary)] text-white text-[15px] font-semibold px-7 py-3.5 rounded-md hover:opacity-90 transition-opacity no-underline max-sm:w-full"
            >
              Get Started Free
            </Link>
            <a
              href="#features"
              className="inline-flex items-center justify-center bg-[var(--bg-tertiary)] text-[var(--text-primary)] text-[15px] font-semibold px-7 py-3.5 rounded-md hover:bg-[var(--border-primary)] transition-colors no-underline max-sm:w-full"
            >
              See How It Works
            </a>
          </div>
        </div>

        {/* Right: dashboard mockup */}
        <div className="lp-fade-up">
          <DashboardMockup />
        </div>
      </section>
    </div>
  );
}
