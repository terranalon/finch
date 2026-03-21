import { useState, useRef, useCallback } from 'react';
import { cn } from '../../lib';
import { CalendarIcon, ChevronDownIcon } from './icons';
import { useClickOutside } from '../../hooks/useClickOutside';

const DATE_RANGES = [
  { id: 'all', label: 'All Time', days: null },
  { id: '7d', label: 'Last 7 Days', days: 7 },
  { id: '30d', label: 'Last 30 Days', days: 30 },
  { id: '90d', label: 'Last 90 Days', days: 90 },
  { id: 'ytd', label: 'Year to Date', days: 'ytd' },
];

export function DateRangeFilter({ value, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const [showCustom, setShowCustom] = useState(value.type === 'custom');
  const [customStart, setCustomStart] = useState(value.startDate || '');
  const [customEnd, setCustomEnd] = useState(value.endDate || '');
  const dropdownRef = useRef(null);

  useClickOutside(dropdownRef, useCallback(() => setIsOpen(false), []));

  const handlePresetSelect = (preset) => {
    onChange({ type: 'preset', preset: preset.id, label: preset.label });
    setShowCustom(false);
    setIsOpen(false);
  };

  const handleCustomApply = () => {
    if (customStart && customEnd) {
      onChange({
        type: 'custom',
        startDate: customStart,
        endDate: customEnd,
        label: `${customStart} - ${customEnd}`,
      });
      setIsOpen(false);
    }
  };

  const displayLabel = value.label || 'All Time';
  const isCustomActive = value.type === 'custom';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-1.5 px-3 py-[7px] rounded-lg cursor-pointer',
          'bg-[var(--bg-elevated)] border border-[var(--border)]',
          'text-xs font-medium text-[var(--text-secondary)]',
          'hover:bg-[var(--bg-card-hover)] transition-colors',
          isCustomActive && 'border-accent'
        )}
      >
        <CalendarIcon className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        <span>{displayLabel}</span>
        <ChevronDownIcon className={cn('w-3.5 h-3.5 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 min-w-[220px] bg-[var(--bg-card)] border border-[var(--border)] rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.4)] z-50 py-1">
          {DATE_RANGES.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePresetSelect(preset)}
              className={cn(
                'w-full px-3 py-2 text-xs text-left transition-colors cursor-pointer rounded-md mx-auto',
                value.type === 'preset' && value.preset === preset.id
                  ? 'bg-accent/10 text-accent'
                  : 'hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)]'
              )}
            >
              {preset.label}
            </button>
          ))}

          <div className="h-px bg-[var(--border)] my-1" />

          <button
            onClick={() => setShowCustom(!showCustom)}
            className={cn(
              'flex items-center justify-between w-full px-3 py-2 text-xs text-left transition-colors cursor-pointer',
              showCustom || isCustomActive
                ? 'bg-accent/10 text-accent'
                : 'hover:bg-[var(--bg-elevated)] text-[var(--text-secondary)]'
            )}
          >
            <span>Custom Range</span>
            <ChevronDownIcon className={cn('w-3.5 h-3.5 transition-transform', showCustom && 'rotate-180')} />
          </button>

          {showCustom && (
            <div className="px-3 py-3 space-y-3">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-[11px] text-[var(--text-muted)] mb-1 block">From</label>
                  <input
                    type="date"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                    className="w-full px-2 py-1.5 rounded text-[11px] bg-[var(--bg-elevated)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
                <div className="flex-1">
                  <label className="text-[11px] text-[var(--text-muted)] mb-1 block">To</label>
                  <input
                    type="date"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                    className="w-full px-2 py-1.5 rounded text-[11px] bg-[var(--bg-elevated)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-none focus:border-accent transition-colors"
                  />
                </div>
              </div>
              <button
                onClick={handleCustomApply}
                disabled={!customStart || !customEnd}
                className={cn(
                  'w-full py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                  customStart && customEnd
                    ? 'bg-accent text-white hover:bg-accent/90'
                    : 'bg-[var(--bg-elevated)] text-[var(--text-muted)] cursor-not-allowed'
                )}
              >
                Apply
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
