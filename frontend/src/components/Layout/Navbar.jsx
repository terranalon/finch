import { NavLink } from 'react-router-dom';
import { cn } from '../../lib';
import { useTheme } from '../../contexts';
import { FinchIcon, ThemeToggle } from '../ui';
import { PortfolioSelector } from './PortfolioSelector';
import { SettingsDropdown } from './SettingsDropdown';

const navLinks = [
  { to: '/', label: 'Overview' },
  { to: '/holdings', label: 'Holdings' },
  { to: '/activity', label: 'Activity' },
  { to: '/insights', label: 'Insights' },
  { to: '/assets', label: 'Assets' },
  { to: '/accounts', label: 'Accounts' },
];

export function Navbar() {
  const { isDark, toggleTheme } = useTheme();

  return (
    <nav className="sticky top-0 z-30 bg-[var(--bg-primary)] border-b border-[var(--border-primary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo and brand */}
          <div className="flex items-center gap-8">
            <NavLink to="/" className="flex items-center gap-2 text-[var(--text-primary)]">
              <FinchIcon className="size-8 text-accent" />
              <span className="text-xl font-semibold">
                <span className="text-accent">Fin</span>ch
              </span>
            </NavLink>

            {/* Navigation links */}
            <div className="hidden md:flex items-center gap-1">
              {navLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === '/'}
                  className={({ isActive }) =>
                    cn(
                      'px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-accent-light text-accent dark:bg-[var(--accent-light)] dark:text-accent-400'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
                    )
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </div>
          </div>

          {/* Right side actions */}
          <div className="flex items-center gap-2">
            <PortfolioSelector />
            <ThemeToggle isDark={isDark} onToggle={toggleTheme} />
            <SettingsDropdown />
          </div>
        </div>

        {/* Mobile navigation */}
        <div className="md:hidden pb-3 flex gap-1 overflow-x-auto">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                cn(
                  'px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap transition-colors',
                  isActive
                    ? 'bg-accent-light text-accent dark:bg-[var(--accent-light)] dark:text-accent-400'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;