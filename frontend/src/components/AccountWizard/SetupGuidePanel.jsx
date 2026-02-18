import { PlayIcon, XIcon } from './icons.jsx';

export function SetupGuidePanel({ broker, guideType, onClose }) {
  const instructions = broker?.instructions?.[guideType];

  if (!instructions) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[60] flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Panel */}
      <div className="relative w-full max-w-2xl bg-[var(--bg-primary)] shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-[var(--bg-primary)] border-b border-[var(--border-primary)] px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-xl font-bold text-[var(--text-primary)]">
              {instructions.title}
            </h2>
            <p className="text-sm text-[var(--text-tertiary)]">Step-by-step guide</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <XIcon className="size-6 text-[var(--text-tertiary)]" />
          </button>
        </div>

        <div className="p-6">
          {/* Video placeholder */}
          <div className="aspect-video bg-[var(--bg-tertiary)] rounded-2xl flex items-center justify-center mb-8">
            <div className="text-center">
              <PlayIcon className="size-16 text-[var(--text-tertiary)] mx-auto mb-2" />
              <p className="text-[var(--text-tertiary)]">Video tutorial placeholder</p>
            </div>
          </div>

          {/* Steps */}
          <div className="space-y-6">
            {instructions.steps.map((step, idx) => (
              <div key={idx} className="flex gap-4">
                <div className="flex-shrink-0 size-8 rounded-full bg-accent text-white flex items-center justify-center font-bold">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <p className="text-[var(--text-primary)]">
                    {step}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Note */}
          {instructions.note && (
            <div className="mt-8 p-5 rounded-xl bg-accent-50 dark:bg-accent-900/20 border border-accent-200 dark:border-accent-800">
              <h4 className="font-semibold text-accent-900 dark:text-accent-300 mb-2">Note</h4>
              <p className="text-sm text-accent-700 dark:text-accent-400">
                {instructions.note}
              </p>
            </div>
          )}

          {/* Help section */}
          <div className="mt-8 p-5 rounded-xl bg-[var(--bg-secondary)] border border-[var(--border-primary)]">
            <h4 className="font-semibold text-[var(--text-primary)] mb-2">Need help?</h4>
            <p className="text-sm text-[var(--text-secondary)]">
              If you're having trouble, check out our FAQ or contact support.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
