import { Link } from "react-router-dom";
import FinchLogo from "./FinchLogo";

const FOOTER_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#integrations", label: "Integrations" },
  { href: "#pricing", label: "Pricing" },
  { to: "/login", label: "Sign In" },
  { to: "/register", label: "Register" },
];

const LINK_CLASS =
  "text-[13px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors no-underline";

function FooterLink({ href, to, children }) {
  if (to) {
    return (
      <Link to={to} className={LINK_CLASS}>
        {children}
      </Link>
    );
  }
  return (
    <a href={href} className={LINK_CLASS}>
      {children}
    </a>
  );
}

export default function LandingFooter() {
  return (
    <footer className="border-t border-[var(--border-primary)] py-8 px-8">
      <div className="max-w-[1200px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex flex-col md:flex-row items-center gap-4">
          <Link to="/" className="flex items-center gap-2 no-underline">
            <FinchLogo size={24} />
            <span className="text-base font-bold leading-none">
              <span className="text-[var(--accent-primary)]">Fin</span>
              <span className="text-[var(--text-primary)]">ch</span>
            </span>
          </Link>
          <span className="text-[13px] text-[var(--text-tertiary)]">
            2026 Finch. All rights reserved.
          </span>
        </div>

        <div className="flex flex-wrap justify-center gap-6">
          {FOOTER_LINKS.map((link) => (
            <FooterLink key={link.label} href={link.href} to={link.to}>
              {link.label}
            </FooterLink>
          ))}
        </div>
      </div>
    </footer>
  );
}
