function formatDateHeader(dateStr) {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

export function DateGroupHeader({ date }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="w-2 h-2 rounded-full bg-accent flex-shrink-0" />
      <h2 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide whitespace-nowrap">
        {formatDateHeader(date)}
      </h2>
      <div className="flex-1 h-px bg-[var(--border)]" />
    </div>
  );
}
