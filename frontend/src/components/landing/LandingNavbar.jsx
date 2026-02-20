import { Link } from "react-router-dom";
import FinchLogo from "./FinchLogo";

const NAV_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How It Works" },
  { href: "#integrations", label: "Integrations" },
  { href: "#pricing", label: "Pricing" },
];

function NavLink({ href, children }) {
  return (
    <a
      href={href}
      className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] px-3 py-1.5 rounded-md transition-colors no-underline"
    >
      {children}
    </a>
  );
}

export default function LandingNavbar() {
  return (
    <nav className="lp-glass-nav sticky top-0 z-50 border-b border-[var(--border-primary)] px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1200px] mx-auto flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <FinchLogo size={32} />
          <span className="text-[22px] font-bold leading-none">
            <span className="text-[var(--accent-primary)]">Fin</span>
            <span className="text-[var(--text-primary)]">ch</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((link) => (
            <NavLink key={link.href} href={link.href}>
              {link.label}
            </NavLink>
          ))}
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
