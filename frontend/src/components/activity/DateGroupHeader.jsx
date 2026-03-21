import { formatDate } from '../../lib';

export function DateGroupHeader({ date }) {
  // Append T00:00:00 to parse as local time, avoiding timezone-shift on date-only strings
  const label = formatDate(date + 'T00:00:00', { format: 'full' });

  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="w-2 h-2 rounded-full bg-accent flex-shrink-0" />
      <h2 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide whitespace-nowrap">
        {label}
      </h2>
      <div className="flex-1 h-px bg-[var(--border)]" />
    </div>
  );
}
