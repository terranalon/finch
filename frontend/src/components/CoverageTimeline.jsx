/**
 * CoverageTimeline -- visualizes per-file date ranges with gap highlighting.
 *
 * Used in BatchUploadModal (during upload) and Accounts page (data coverage).
 */

const PALETTE = [
  { segment: 'bg-blue-500 dark:bg-blue-400', dot: 'bg-blue-500' },
  { segment: 'bg-emerald-500 dark:bg-emerald-400', dot: 'bg-emerald-500' },
  { segment: 'bg-purple-500 dark:bg-purple-400', dot: 'bg-purple-500' },
  { segment: 'bg-amber-500 dark:bg-amber-400', dot: 'bg-amber-500' },
  { segment: 'bg-rose-500 dark:bg-rose-400', dot: 'bg-rose-500' },
  { segment: 'bg-cyan-500 dark:bg-cyan-400', dot: 'bg-cyan-500' },
];

function formatDateShort(date) {
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

function daysBetween(a, b) {
  return Math.max(1, (new Date(b) - new Date(a)) / (1000 * 60 * 60 * 24));
}

export function CoverageTimeline({ files = [], gaps = [] }) {
  if (files.length === 0) return null;

  // Compute overall range from all files
  const allDates = files.flatMap((f) => [new Date(f.startDate), new Date(f.endDate)]);
  const minDate = new Date(Math.min(...allDates));
  const maxDate = new Date(Math.max(...allDates));
  const totalDays = daysBetween(minDate, maxDate);

  // Build file segments as percentages
  const fileSegments = files.map((file, idx) => {
    const start = daysBetween(minDate, file.startDate);
    const width = daysBetween(file.startDate, file.endDate);
    const color = PALETTE[idx % PALETTE.length];
    return {
      ...file,
      leftPercent: ((start - 1) / totalDays) * 100,
      widthPercent: (width / totalDays) * 100,
      colorClass: color.segment,
      dotClass: color.dot,
    };
  });

  // Build gap segments as percentages
  const gapSegments = gaps.map((gap) => {
    const start = daysBetween(minDate, gap.start_date);
    const width = daysBetween(gap.start_date, gap.end_date);
    return {
      ...gap,
      leftPercent: ((start - 1) / totalDays) * 100,
      widthPercent: (width / totalDays) * 100,
    };
  });

  return (
    <div data-testid="coverage-timeline">
      {/* Date range labels */}
      <div className="flex justify-between text-xs text-[var(--text-tertiary)] mb-2">
        <span>{formatDateShort(minDate)}</span>
        <span>{formatDateShort(maxDate)}</span>
      </div>

      {/* Timeline bar */}
      <div className="relative h-3 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
        {/* File coverage segments */}
        {fileSegments.map((seg, idx) => (
          <div
            key={idx}
            className={`absolute top-0 bottom-0 ${seg.colorClass} rounded-full`}
            style={{ left: `${seg.leftPercent}%`, width: `${Math.max(1, seg.widthPercent)}%` }}
            title={`${seg.fileName}: ${seg.transactions} transactions`}
          />
        ))}
        {/* Gap overlays */}
        {gapSegments.map((gap, idx) => (
          <div
            key={`gap-${idx}`}
            className="absolute top-0 bottom-0 bg-amber-400/60 dark:bg-amber-500/60"
            style={{ left: `${gap.leftPercent}%`, width: `${Math.max(1, gap.widthPercent)}%` }}
            title={`${gap.days} day gap`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="mt-3 space-y-1">
        {fileSegments.map((seg, idx) => (
          <div key={idx} className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${seg.dotClass}`} />
            <span className="truncate max-w-[140px]" title={seg.fileName}>
              {seg.fileName}
            </span>
            <span className="text-[var(--text-tertiary)]">
              {seg.transactions} transactions
            </span>
          </div>
        ))}
        {gaps.length > 0 && (
          <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-400" />
            {gaps.length === 1
              ? `${gaps[0].days} day gap`
              : `${gaps.length} gaps detected`}
          </div>
        )}
      </div>
    </div>
  );
}
