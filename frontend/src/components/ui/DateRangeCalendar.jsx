import { useState, useMemo, useRef, useCallback } from 'react';
import { cn } from '../../lib';
import { useClickOutside } from '../../hooks/useClickOutside';

const DAY_LABELS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function toDateStr(year, month, day) {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function buildCells(year, month) {
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayOfWeek = new Date(year, month, 1).getDay();
  const result = [];
  for (let i = 0; i < firstDayOfWeek; i++) result.push(null);
  for (let day = 1; day <= daysInMonth; day++) {
    result.push({ day, dateStr: toDateStr(year, month, day) });
  }
  while (result.length % 7 !== 0) result.push(null);
  return result;
}

/**
 * Dual-month date range calendar with dark mode support.
 *
 * Shows two months side by side. Two-click interaction: first click sets
 * range start, second sets range end (auto-swaps if end < start).
 * Fires onChange(start, end) on completion. Shows a hover preview band
 * while selecting.
 *
 * @param {string} className - Extra classes for positioning
 * @param {string} initialStart - Pre-selected start date (YYYY-MM-DD)
 * @param {string} initialEnd - Pre-selected end date (YYYY-MM-DD)
 * @param {Function} onChange - Called with (startStr, endStr) when range is complete
 * @param {Function} onClose - Called when clicking outside
 */
export function DateRangeCalendar({ className, initialStart, initialEnd, onChange, onClose }) {
  const ref = useRef(null);
  const today = new Date();
  const todayStr = toDateStr(today.getFullYear(), today.getMonth(), today.getDate());

  // Left panel starts on the month of initialStart (or previous month if today)
  const initDate = initialStart ? new Date(initialStart + 'T00:00:00') : today;
  const [viewYear, setViewYear] = useState(initDate.getFullYear());
  const [viewMonth, setViewMonth] = useState(initDate.getMonth());
  const [rangeStart, setRangeStart] = useState(initialStart || null);
  const [rangeEnd, setRangeEnd] = useState(initialEnd || null);
  const [hoverDate, setHoverDate] = useState(null);

  useClickOutside(ref, useCallback(() => onClose?.(), [onClose]));

  // Right panel = next month after left panel
  const rightMonth = viewMonth === 11 ? 0 : viewMonth + 1;
  const rightYear = viewMonth === 11 ? viewYear + 1 : viewYear;

  const prevMonth = () => {
    if (viewMonth === 0) { setViewYear((y) => y - 1); setViewMonth(11); }
    else setViewMonth((m) => m - 1);
  };

  const nextMonth = () => {
    if (viewMonth === 11) { setViewYear((y) => y + 1); setViewMonth(0); }
    else setViewMonth((m) => m + 1);
  };

  const handleDayClick = (dateStr) => {
    if (!rangeStart || rangeEnd) {
      setRangeStart(dateStr);
      setRangeEnd(null);
    } else {
      const [s, e] = dateStr < rangeStart ? [dateStr, rangeStart] : [rangeStart, dateStr];
      setRangeStart(s);
      setRangeEnd(e);
      onChange?.(s, e);
    }
  };

  // Effective range for visual highlighting (includes hover preview)
  const [effStart, effEnd] = useMemo(() => {
    if (!rangeStart) return [null, null];
    const end = rangeEnd || hoverDate;
    if (!end) return [rangeStart, rangeStart];
    return rangeStart <= end ? [rangeStart, end] : [end, rangeStart];
  }, [rangeStart, rangeEnd, hoverDate]);

  const hasRange = effStart && effEnd && effStart !== effEnd;

  const leftCells = useMemo(() => buildCells(viewYear, viewMonth), [viewYear, viewMonth]);
  const rightCells = useMemo(() => buildCells(rightYear, rightMonth), [rightYear, rightMonth]);

  const renderDay = (cell, i) => {
    if (!cell) return <div key={i} className="h-8" />;
    const { day, dateStr } = cell;
    const isToday = dateStr === todayStr;
    const isFuture = dateStr > todayStr;
    const isSelected = dateStr === effStart || dateStr === effEnd;
    const inRange = hasRange && dateStr > effStart && dateStr < effEnd;
    const isRangeStart = hasRange && dateStr === effStart;
    const isRangeEnd = hasRange && dateStr === effEnd;

    return (
      <div
        key={i}
        className={cn(
          'h-8 flex items-center justify-center',
          inRange && !isFuture && 'bg-[var(--accent-light)]',
          isRangeStart && !isFuture && 'bg-[var(--accent-light)] rounded-l-full',
          isRangeEnd && !isFuture && 'bg-[var(--accent-light)] rounded-r-full',
        )}
      >
        <button
          onClick={() => !isFuture && handleDayClick(dateStr)}
          onMouseEnter={() => { if (!isFuture && rangeStart && !rangeEnd) setHoverDate(dateStr); }}
          className={cn(
            'w-7 h-7 flex items-center justify-center rounded-full text-xs transition-colors',
            isFuture
              ? 'text-[var(--text-tertiary)] opacity-30 cursor-default'
              : isSelected
                ? 'bg-accent text-white font-semibold cursor-pointer'
                : 'text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] cursor-pointer',
            isToday && !isSelected && 'font-semibold ring-1 ring-accent',
          )}
        >
          {day}
        </button>
      </div>
    );
  };

  const dayHeaders = (
    <div className="grid grid-cols-7 mb-1">
      {DAY_LABELS.map((d) => (
        <div key={d} className="h-7 flex items-center justify-center text-[10px] font-medium text-[var(--text-tertiary)]">
          {d}
        </div>
      ))}
    </div>
  );

  return (
    <div
      ref={ref}
      className={cn(
        'bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg p-4',
        className,
      )}
    >
      {/* Header with month navigation */}
      <div className="flex items-center mb-2">
        <button
          onClick={prevMonth}
          className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] transition-colors cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <span className="flex-1 text-center text-sm font-semibold text-[var(--text-primary)]">
          {MONTH_NAMES[viewMonth]} {viewYear}
        </span>
        <div className="w-7" />
        <span className="flex-1 text-center text-sm font-semibold text-[var(--text-primary)]">
          {MONTH_NAMES[rightMonth]} {rightYear}
        </span>
        <button
          onClick={nextMonth}
          className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] transition-colors cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      </div>

      {/* Two month grids side by side */}
      <div className="flex gap-6" onMouseLeave={() => setHoverDate(null)}>
        {/* Left month */}
        <div className="w-[252px]">
          {dayHeaders}
          <div className="grid grid-cols-7">{leftCells.map(renderDay)}</div>
        </div>

        {/* Divider */}
        <div className="w-px bg-[var(--border-primary)]" />

        {/* Right month */}
        <div className="w-[252px]">
          {dayHeaders}
          <div className="grid grid-cols-7">{rightCells.map(renderDay)}</div>
        </div>
      </div>

      {/* Selection hint */}
      <div className="mt-3 text-center text-[10px] text-[var(--text-tertiary)]">
        {!rangeStart || rangeEnd ? 'Select start date' : 'Select end date'}
      </div>
    </div>
  );
}
