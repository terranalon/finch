import { cn } from '../../lib/index.js';

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M5 12l5 5L20 7" />
    </svg>
  );
}

export function OnboardingStepIndicator({ steps, currentStep, onStepClick }) {
  return (
    <div className="flex items-center justify-center py-6 px-6 bg-[var(--bg-secondary)]/50 border-b border-[var(--border-primary)] flex-wrap gap-y-3">
      {steps.map((label, i) => {
        const stepNum = i + 1;
        const isCompleted = stepNum < currentStep;
        const isCurrent = stepNum === currentStep;
        const isClickable = isCompleted && !!onStepClick;

        const dotClass = cn(
          'size-9 rounded-full flex items-center justify-center text-sm font-semibold transition-colors',
          isCompleted && 'bg-accent text-white',
          isCurrent && 'bg-accent text-white ring-4 ring-accent/20',
          !isCompleted && !isCurrent && 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] border-2 border-[var(--border-primary)]',
          isClickable && 'hover:bg-accent-hover'
        );

        const labelClass = cn(
          'text-xs mt-1.5 font-medium whitespace-nowrap transition-colors',
          isCurrent ? 'text-accent font-semibold' : 'text-[var(--text-tertiary)]',
          isClickable && 'group-hover:text-accent'
        );

        const stepContent = (
          <>
            <div className={dotClass}>
              {isCompleted ? <CheckIcon /> : stepNum}
            </div>
            <span className={labelClass}>{label}</span>
          </>
        );

        return (
          <div key={label} className="flex items-center">
            {isClickable ? (
              <button
                type="button"
                onClick={() => onStepClick(stepNum)}
                className="flex flex-col items-center group cursor-pointer"
                aria-label={`Go back to ${label} step`}
              >
                {stepContent}
              </button>
            ) : (
              <div className="flex flex-col items-center">
                {stepContent}
              </div>
            )}
            {i < steps.length - 1 && (
              <div
                className={cn(
                  'w-10 h-0.5 mx-2',
                  isCompleted ? 'bg-accent' : 'bg-[var(--border-primary)]'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
