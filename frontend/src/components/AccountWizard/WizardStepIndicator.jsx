import { cn } from '../../lib';

const STEPS = [
  { num: 1, label: 'Type' },
  { num: 2, label: 'Broker' },
  { num: 3, label: 'Details' },
  { num: 4, label: 'Connect' },
  { num: 5, label: 'Done' },
];

function CheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

export function WizardStepIndicator({ currentStep, maxReachedStep, skippedSteps = [], onStepClick }) {
  const canClickStep = (stepNum) => {
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
                  isCompleted && !isSkipped && 'bg-emerald-500 text-white',
                  isCompleted && !isSkipped && isClickable && 'group-hover:bg-emerald-600 group-hover:ring-4 group-hover:ring-emerald-100 dark:group-hover:ring-emerald-900/50',
                  isCurrent && 'bg-blue-600 text-white ring-4 ring-blue-100 dark:ring-blue-900/50',
                  !isCompleted && !isCurrent && 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400',
                  isSkipped && 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
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
                  isCompleted && !isSkipped && 'text-gray-900 dark:text-white',
                  isCompleted && !isSkipped && isClickable && 'group-hover:text-emerald-600 dark:group-hover:text-emerald-400',
                  isCurrent && 'text-gray-900 dark:text-white',
                  !isCompleted && !isCurrent && 'text-gray-400 dark:text-gray-500'
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
                    ? 'bg-emerald-500'
                    : 'bg-gray-200 dark:bg-gray-700'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
