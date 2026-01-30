function XIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

function PlayIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z" />
    </svg>
  );
}

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
      <div className="relative w-full max-w-2xl bg-white dark:bg-gray-900 shadow-2xl overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              {instructions.title}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Step-by-step guide</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors cursor-pointer"
          >
            <XIcon className="size-6 text-gray-500" />
          </button>
        </div>

        <div className="p-6">
          {/* Video placeholder */}
          <div className="aspect-video bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center mb-8">
            <div className="text-center">
              <PlayIcon className="size-16 text-gray-400 mx-auto mb-2" />
              <p className="text-gray-500 dark:text-gray-400">Video tutorial placeholder</p>
            </div>
          </div>

          {/* Steps */}
          <div className="space-y-6">
            {instructions.steps.map((step, idx) => (
              <div key={idx} className="flex gap-4">
                <div className="flex-shrink-0 size-8 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold">
                  {idx + 1}
                </div>
                <div className="flex-1">
                  <p className="text-gray-900 dark:text-white">
                    {step}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Note */}
          {instructions.note && (
            <div className="mt-8 p-5 rounded-xl bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800">
              <h4 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">Note</h4>
              <p className="text-sm text-blue-700 dark:text-blue-400">
                {instructions.note}
              </p>
            </div>
          )}

          {/* Help section */}
          <div className="mt-8 p-5 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
            <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Need help?</h4>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              If you're having trouble, check out our FAQ or contact support.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
