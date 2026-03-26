import { useState, useRef, useCallback } from 'react';
import { cn } from '../../lib';
import { CalendarIcon, ChevronDownIcon } from './icons';
import { useClickOutside } from '../../hooks/useClickOutside';

const DATE_RANGES = [
  { id: 'all', label: 'All Time' },
  { id: '7d', label: 'Last 7 Days' },
  { id: '30d', label: 'Last 30 Days' },
  { id: '90d', label: 'Last 90 Days' },
  { id: 'ytd', label: 'Year to Date' },
];

const DATE_INPUT_CLASS =
  'w-full px-2 py-1.5 rounded text-[11px] bg-[var(--bg-tertiary)] border border-[var(--border-primary)] text-[var(--text-primary)] focus:outline-none focus:border-accent transition-colors';

function DateInput({ label, value, onChange }) {
  return (
    <div className="flex-1">
      <label className="text-[11px] text-[var(--text-tertiary)] mb-1 block">{label}</label>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={DATE_INPUT_CLASS}
      />
    </div>
  );
}

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

  const canApplyCustom = customStart && customEnd;

  const handleCustomApply = () => {
    if (!canApplyCustom) return;
    onChange({
      type: 'custom',
      startDate: customStart,
      endDate: customEnd,
      label: `${customStart} - ${customEnd}`,
    });
    setIsOpen(false);
  };

  const displayLabel = value.label || 'All Time';
  const isCustomActive = value.type === 'custom';
  const isPresetActive = (presetId) => value.type === 'preset' && value.preset === presetId;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-1.5 px-3 py-[7px] rounded-lg cursor-pointer',
          'bg-[var(--bg-tertiary)] border border-[var(--border-primary)]',
          'text-xs font-medium text-[var(--text-secondary)]',
          'hover:border-[var(--text-faint)] transition-colors',
          isCustomActive && 'border-accent'
        )}
      >
        <CalendarIcon className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
        <span>{displayLabel}</span>
        <ChevronDownIcon className={cn('w-3.5 h-3.5 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 min-w-[220px] bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-[0_8px_32px_rgba(0,0,0,0.4)] z-50 p-2">
          {DATE_RANGES.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePresetSelect(preset)}
              className={cn(
                'w-full px-2.5 py-[7px] text-xs text-left transition-colors cursor-pointer rounded-md mx-auto',
                isPresetActive(preset.id)
                  ? 'bg-accent/10 text-accent font-semibold'
                  : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
              )}
            >
              {preset.label}
            </button>
          ))}

          <div className="h-px bg-[var(--border-primary)] my-1" />

          <button
            onClick={() => setShowCustom(!showCustom)}
            className={cn(
              'flex items-center justify-between w-full px-3 py-2 text-xs text-left transition-colors cursor-pointer',
              showCustom || isCustomActive
                ? 'bg-accent/10 text-accent'
                : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
            )}
          >
            <span>Custom Range</span>
            <ChevronDownIcon className={cn('w-3.5 h-3.5 transition-transform', showCustom && 'rotate-180')} />
          </button>

          {showCustom && (
            <div className="px-3 py-3 space-y-3">
              <div className="flex gap-2">
                <DateInput label="From" value={customStart} onChange={setCustomStart} />
                <DateInput label="To" value={customEnd} onChange={setCustomEnd} />
              </div>
              <button
                onClick={handleCustomApply}
                disabled={!canApplyCustom}
                className={cn(
                  'w-full py-2 rounded-lg text-xs font-medium transition-colors cursor-pointer',
                  canApplyCustom
                    ? 'bg-accent text-white hover:bg-accent/90'
                    : 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] cursor-not-allowed'
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
