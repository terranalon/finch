import { Link } from "react-router-dom";

function FinchLogo({ size = 32 }) {
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

export default function LandingNavbar() {
  return (
    <nav className="lp-glass-nav sticky top-0 z-50 border-b border-[var(--border-primary)] px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1200px] mx-auto flex items-center justify-between h-16">
        <a href="/" className="flex items-center gap-2 no-underline">
          <FinchLogo size={32} />
          <span className="text-[22px] font-bold leading-none">
            <span className="text-[var(--accent-primary)]">Fin</span>
            <span className="text-[var(--text-primary)]">ch</span>
          </span>
        </a>

        <div className="hidden md:flex items-center gap-8">
          <a
            href="#features"
            className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] px-3 py-1.5 rounded-md transition-colors no-underline"
          >
            Features
          </a>
          <a
            href="#how-it-works"
            className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] px-3 py-1.5 rounded-md transition-colors no-underline"
          >
            How It Works
          </a>
          <a
            href="#integrations"
            className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] px-3 py-1.5 rounded-md transition-colors no-underline"
          >
            Integrations
          </a>
          <a
            href="#pricing"
            className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] px-3 py-1.5 rounded-md transition-colors no-underline"
          >
            Pricing
          </a>
        </div>

        <div className="flex items-center gap-4">
          <Link
            to="/login"
            className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline"
          >
            Sign In
          </Link>
          <Link
            to="/register"
            className="inline-flex items-center justify-center bg-[var(--accent-primary)] text-white text-sm font-medium px-4 py-2 rounded-md hover:opacity-90 transition-opacity no-underline"
          >
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  );
}
