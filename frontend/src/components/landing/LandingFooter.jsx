import { Link } from "react-router-dom";

function FinchLogo({ size = 24 }) {
  return (
    <svg viewBox="0 0 32 32" fill="#2563EB" width={size} height={size}>
      <path
        d="M4 16c0-1.5 1-2.5 2-3l8-5c1-.5 2-.5 3 0l8 5c1 .5 2 1.5 2 3s-1 2.5-2 3l-3 2v3c0 1-1 2-2 2h-8c-1 0-2-1-2-2v-3l-3-2c-1-.5-2-1.5-2-3z"
        fillRule="evenodd"
      />
      <path d="M16 9l6 4-6 3-6-3 6-4z" fill="#2563EB" opacity="0.3" />
    </svg>
  );
}

export default function LandingFooter() {
  return (
    <footer className="border-t border-[var(--border-primary)] py-8 px-8">
      <div className="max-w-[1200px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex flex-col md:flex-row items-center gap-4">
          <a href="/" className="flex items-center gap-2 no-underline">
            <FinchLogo size={24} />
            <span className="text-base font-bold leading-none">
              <span className="text-[var(--accent-primary)]">Fin</span>
              <span className="text-[var(--text-primary)]">ch</span>
            </span>
          </a>
          <span className="text-[13px] text-[var(--text-tertiary)]">
            2026 Finch. All rights reserved.
          </span>
        </div>

        <div className="flex flex-wrap justify-center gap-6">
          <a
            href="#features"
            className="text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline"
          >
            Features
          </a>
          <a
            href="#integrations"
            className="text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline"
          >
            Integrations
          </a>
          <a
            href="#pricing"
            className="text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline"
          >
            Pricing
          </a>
          <Link
            to="/login"
            className="text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline"
          >
            Sign In
          </Link>
          <Link
            to="/register"
            className="text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline"
          >
            Register
          </Link>
        </div>
      </div>
    </footer>
  );
}
