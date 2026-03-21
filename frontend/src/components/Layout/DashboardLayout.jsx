import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { HeaderBar } from './HeaderBar';

export function DashboardLayout({ children }) {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem('sidebar-collapsed') === 'true'
  );

  const handleToggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem('sidebar-collapsed', String(next));
  };

  return (
    <div className="flex h-dvh overflow-hidden bg-[var(--bg-primary)]">
      <Sidebar collapsed={collapsed} onToggle={handleToggle} />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <HeaderBar />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
