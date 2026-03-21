import { NavLink } from 'react-router-dom';
import { cn } from '../../lib';
import { FinchIcon } from '../ui';

function OverviewIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function HoldingsIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" />
      <path d="M3 5v14a2 2 0 0 0 2 2h16v-5" />
      <path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
    </svg>
  );
}

function ActivityIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 8v4l3 3" />
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

function InsightsIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M3 3v18h18" />
      <path d="m19 9-5 5-4-4-3 3" />
    </svg>
  );
}

function AssetsIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v12" />
      <path d="M15.5 9.4c-.6-.7-1.5-1.1-2.5-1.2h-1.2c-1.3.1-2.3 1.2-2.3 2.5 0 1.4 1 2.5 2.3 2.5h1.5c1.3 0 2.3 1.1 2.3 2.5s-1 2.4-2.3 2.5H12c-1 0-1.9-.5-2.5-1.2" />
    </svg>
  );
}

function AccountsIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M2 20h20" />
      <path d="M5 20V8l7-5 7 5v12" />
      <path d="M9 20v-5h6v5" />
    </svg>
  );
}

function CollapseIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

const navItems = [
  { to: '/', label: 'Overview', icon: OverviewIcon, end: true },
  { to: '/holdings', label: 'Holdings', icon: HoldingsIcon },
  { to: '/activity', label: 'Activity', icon: ActivityIcon },
  { to: '/insights', label: 'Insights', icon: InsightsIcon },
  { to: '/assets', label: 'Assets', icon: AssetsIcon },
  { to: '/accounts', label: 'Accounts', icon: AccountsIcon },
];

export function Sidebar({ collapsed, onToggle }) {
  return (
    <nav
      className={cn(
        'h-dvh flex flex-col border-r border-[var(--border-primary)] bg-[var(--bg-primary)] transition-[width] duration-200 overflow-hidden select-none flex-shrink-0',
        collapsed ? 'w-16' : 'w-[220px]'
      )}
    >
      {/* Brand */}
      <div
        className={cn(
          'h-[52px] flex items-center gap-2.5 border-b border-[var(--border-primary)] flex-shrink-0',
          collapsed ? 'justify-center px-0' : 'px-[18px]'
        )}
      >
        <FinchIcon className="size-[30px] text-accent flex-shrink-0" />
        {!collapsed && (
          <span className="text-base font-bold whitespace-nowrap">
            <span className="text-accent">Fin</span>ch
          </span>
        )}
      </div>

      {/* Nav items */}
      <div className="flex-1 py-2.5 px-2 flex flex-col gap-0.5">
        {!collapsed && (
          <span className="text-[10px] font-semibold text-[var(--text-faint)] uppercase tracking-wider px-3.5 pt-4 pb-1.5">
            Main
          </span>
        )}
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg text-[13.5px] font-medium transition-all whitespace-nowrap',
                collapsed ? 'justify-center p-3' : 'px-3.5 py-[11px]',
                isActive
                  ? 'bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] font-semibold'
                  : 'text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)]'
              )
            }
          >
            <item.icon className="w-[19px] h-[19px] flex-shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </div>

      {/* Collapse toggle */}
      <div className="px-2 py-2.5 border-t border-[var(--border-primary)] flex-shrink-0">
        <button
          onClick={onToggle}
          className={cn(
            'flex items-center justify-center gap-2 w-full p-2 rounded-lg',
            'text-[var(--text-faint)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-tertiary)]',
            'transition-all text-xs cursor-pointer'
          )}
        >
          <CollapseIcon
            className={cn('w-4 h-4 transition-transform', collapsed && 'rotate-180')}
          />
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>
    </nav>
  );
}
