import { Link } from "react-router-dom";
import FinchLogo from "../landing/FinchLogo";

export default function AuthNavbar({ page }) {
  return (
    <nav className="lp-glass-nav sticky top-0 z-50 border-b border-[var(--border-primary)] px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1200px] mx-auto flex items-center justify-between h-16">
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2 no-underline" aria-label="Finch">
            <FinchLogo size={32} />
            <span className="text-[22px] font-bold leading-none">
              <span className="text-[var(--accent-primary)]">Fin</span>
              <span className="text-[var(--text-primary)]">ch</span>
            </span>
          </Link>
          <Link
            to="/"
            className="flex items-center gap-1 text-[13px] font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] px-2 py-1 rounded-md transition-colors no-underline"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
            Home
          </Link>
        </div>
        <div className="flex items-center gap-4">
          {page === "login" ? (
            <Link
              to="/register"
              className="inline-flex items-center justify-center bg-[var(--accent-primary)] text-white text-sm font-medium px-4 py-2 rounded-md hover:opacity-90 transition-opacity no-underline"
            >
              Get Started
            </Link>
          ) : (
            <Link
              to="/login"
              className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
