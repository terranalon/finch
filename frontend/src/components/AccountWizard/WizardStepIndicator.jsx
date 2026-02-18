import { cn } from '../../lib/index.js';

import { CheckIcon } from './icons.jsx';

const STEPS = [
  { num: 1, label: 'Type' },
  { num: 2, label: 'Broker' },
  { num: 3, label: 'Details' },
  { num: 4, label: 'Connect' },
  { num: 5, label: 'Done' },
];

export function WizardStepIndicator({ currentStep, maxReachedStep, skippedSteps = [], onStepClick, locked = false }) {
  const canClickStep = (stepNum) => {
    if (locked) return false; // Account persisted -- navigation locked
    if (currentStep === 5) return false; // Terminal step - no navigation
    if (skippedSteps.includes(stepNum)) return false; // Skipped steps disabled
    if (stepNum >= currentStep) return false; // Can't go forward via indicator
    return stepNum <= maxReachedStep; // Only completed steps
  };

  return (
    <div className="flex items-center justify-center gap-2 sm:gap-4">
      {STEPS.map((step, idx) => {
        const isCompleted = currentStep > step.num;
        const isCurrent = currentStep === step.num;
        const isSkipped = skippedSteps.includes(step.num);
        const isClickable = canClickStep(step.num);

        return (
          <div key={step.num} className="flex items-center gap-2 sm:gap-4">
            <button
              onClick={() => isClickable && onStepClick(step.num)}
              disabled={!isClickable}
              className={cn(
                'flex items-center gap-2 group',
                isClickable ? 'cursor-pointer' : 'cursor-default'
              )}
            >
              <div
                className={cn(
                  'size-8 sm:size-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all',
                  isCompleted && !isSkipped && 'bg-positive text-white',
                  isCompleted && !isSkipped && isClickable && 'group-hover:bg-positive-dark group-hover:ring-4 group-hover:ring-positive-light dark:group-hover:ring-positive-bg-dark',
                  isCurrent && 'bg-accent text-white ring-4 ring-accent-light dark:ring-accent-900/50',
                  !isCompleted && !isCurrent && 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]',
                  isSkipped && 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)]'
                )}
              >
                {isCompleted && !isSkipped ? (
                  <CheckIcon className="size-4 sm:size-5" />
                ) : (
                  step.num
                )}
              </div>
              <span
                className={cn(
                  'text-sm font-medium hidden md:block transition-colors',
                  isCompleted && !isSkipped && 'text-[var(--text-primary)]',
                  isCompleted && !isSkipped && isClickable && 'group-hover:text-positive dark:group-hover:text-positive-dark',
                  isCurrent && 'text-[var(--text-primary)]',
                  !isCompleted && !isCurrent && 'text-[var(--text-tertiary)]'
                )}
              >
                {step.label}
              </span>
            </button>
            {idx < STEPS.length - 1 && (
              <div
                className={cn(
                  'w-8 sm:w-12 lg:w-16 h-1 rounded-full transition-colors',
                  currentStep > step.num && !skippedSteps.includes(step.num + 1)
                    ? 'bg-positive'
                    : 'bg-[var(--bg-tertiary)]'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
