import { useEffect } from "react";
import { useTheme } from "../../contexts";
import AuthNavbar from "./AuthNavbar";
import "../landing/landing.css";

const VALUE_PROPS = [
  "Connect IBKR, Kraken, Meitav & more",
  "Automatic daily transaction sync",
  "Returns calculated with deposits excluded",
];

function MiniDashboard() {
  const holdings = [
    { icon: "A", bg: "#333", ticker: "AAPL", ret: "+18.4%", gain: true },
    { icon: "M", bg: "#0078D4", ticker: "MSFT", ret: "+24.1%", gain: true },
    { icon: "B", bg: "#F7931A", ticker: "BTC", ret: "+142.3%", gain: true },
  ];

  return (
    <div className="bg-white border border-[var(--border-primary)] rounded-[10px] overflow-hidden shadow-[0_8px_30px_rgba(0,0,0,0.08)] max-w-[360px]">
      <div className="flex items-center gap-[5px] px-3 py-2 bg-[var(--bg-secondary)] border-b border-[var(--border-primary)]">
        <div className="w-[7px] h-[7px] rounded-full bg-[#FCA5A5]" />
        <div className="w-[7px] h-[7px] rounded-full bg-[#FCD34D]" />
        <div className="w-[7px] h-[7px] rounded-full bg-[#6EE7B7]" />
      </div>
      <div className="p-3.5">
        <div className="font-numeric text-xl font-bold text-[var(--text-primary)]">$247,832.15</div>
        <div className="font-numeric text-xs font-semibold text-[#059669] mt-0.5">+$1,247.33 (+0.51%)</div>
        <svg viewBox="0 0 320 50" preserveAspectRatio="none" className="w-full h-10 mt-2.5" aria-hidden="true">
          <defs>
            <linearGradient id="auth-cg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2563EB" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#2563EB" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0,40 C20,38 40,35 60,32 C80,29 100,27 120,22 C140,17 160,25 180,20 C200,16 220,14 240,11 C260,8 280,10 300,7 L320,5 L320,50 L0,50Z" fill="url(#auth-cg)" />
          <path d="M0,40 C20,38 40,35 60,32 C80,29 100,27 120,22 C140,17 160,25 180,20 C200,16 220,14 240,11 C260,8 280,10 300,7 L320,5" fill="none" stroke="#2563EB" strokeWidth="2" />
        </svg>
        {holdings.map((h) => (
          <div key={h.ticker} className="flex justify-between items-center py-[7px] border-t border-[var(--bg-secondary)] text-xs">
            <span className="flex items-center gap-1.5 font-semibold text-[var(--text-primary)]">
              <span className="w-[18px] h-[18px] rounded-full flex items-center justify-center text-[8px] font-bold text-white" style={{ background: h.bg }}>{h.icon}</span>
              {h.ticker}
            </span>
            <span className={`font-numeric font-semibold ${h.gain ? "text-[#059669]" : "text-[#DC2626]"}`}>{h.ret}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CheckIcon() {
  return (
    <span className="flex-shrink-0 w-[18px] h-[18px] bg-[var(--accent-light)] rounded-full flex items-center justify-center mt-px">
      <svg viewBox="0 0 12 12" fill="none" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" className="w-2.5 h-2.5" aria-hidden="true">
        <path d="M2.5 6l2.5 2.5 4.5-4.5" />
      </svg>
    </span>
  );
}

export default function AuthLayout({ children, page }) {
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    const prev = theme;
    if (prev !== "light") setTheme("light");
    return () => {
      if (prev !== "light") setTheme(prev);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-dvh bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <AuthNavbar page={page} />
      <div className="grid grid-cols-1 lg:grid-cols-2 min-h-[calc(100dvh-64px)]">
        <div className="hidden lg:flex flex-col justify-center px-12 xl:px-16 py-16 relative overflow-hidden">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: "radial-gradient(ellipse 80% 50% at 50% 30%, rgba(37,99,235,0.06), transparent)" }}
          />
          <div className="relative z-10 max-w-[420px]">
            <h1 className="text-[38px] font-bold leading-[1.1] tracking-[-0.025em] text-[var(--text-primary)] mb-4">
              Know your{" "}
              <span className="text-[var(--accent-primary)]">real</span>{" "}
              performance.
            </h1>
            <p className="text-base leading-[1.7] text-[var(--text-secondary)] mb-8">
              Finch connects to your brokers, imports transactions automatically,
              and shows you what spreadsheets never could.
            </p>
            <MiniDashboard />
            <ul className="list-none mt-5 space-y-2">
              {VALUE_PROPS.map((text) => (
                <li key={text} className="flex items-start gap-2.5 text-sm text-[var(--text-secondary)]">
                  <CheckIcon />
                  {text}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="flex items-center justify-center px-6 py-12 bg-[var(--bg-secondary)] lg:border-l lg:border-[var(--border-primary)]">
          <div className="w-full max-w-[400px]">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
