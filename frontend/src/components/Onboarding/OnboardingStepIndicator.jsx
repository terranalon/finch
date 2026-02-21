import { cn } from '../../lib/index.js';

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
      <path d="M5 12l5 5L20 7" />
    </svg>
  );
}

export function OnboardingStepIndicator({ steps, currentStep }) {
  return (
    <div className="flex items-center justify-center py-5 px-5 bg-[var(--bg-secondary)]/50 border-b border-[var(--border-primary)] flex-wrap gap-y-2">
      {steps.map((label, i) => {
        const stepNum = i + 1;
        const isCompleted = stepNum < currentStep;
        const isCurrent = stepNum === currentStep;

        return (
          <div key={label} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'size-7 rounded-full flex items-center justify-center text-xs font-semibold',
                  isCompleted && 'bg-accent text-white',
                  isCurrent && 'bg-accent text-white ring-3 ring-accent-100',
                  !isCompleted && !isCurrent && 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] border-2 border-[var(--border-primary)]'
                )}
              >
                {isCompleted ? <CheckIcon /> : stepNum}
              </div>
              <span
                className={cn(
                  'text-[10px] mt-1 font-medium whitespace-nowrap',
                  isCurrent ? 'text-accent font-semibold' : 'text-[var(--text-tertiary)]'
                )}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={cn(
                  'w-8 h-0.5 mx-1',
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
