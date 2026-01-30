import { CheckIcon, SparklesIcon } from '../icons.jsx';

export function SuccessStep({ broker, accountDetails, skippedData, onViewAccount, onAddAnother, onDone }) {
  const isManual = !broker;

  return (
    <div className="max-w-lg mx-auto text-center">
      <div className="size-20 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-6">
        <CheckIcon className="size-10 text-emerald-600 dark:text-emerald-400" />
      </div>

      <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3">
        You're all set!
      </h2>
      <p className="text-gray-500 dark:text-gray-400 text-lg mb-8">
        Your {isManual ? '' : `${broker.name} `}account has been added to your portfolio.
      </p>

      {/* Account summary card */}
      <div className="p-6 rounded-2xl bg-gray-50 dark:bg-gray-800/50 border-2 border-gray-200 dark:border-gray-700 text-left mb-8">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
          {accountDetails?.name || 'My Account'}
        </h3>
        {accountDetails?.description && (
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            {accountDetails.description}
          </p>
        )}
        <p className="text-gray-500 dark:text-gray-400 mt-2">
          {broker?.name || 'Manual'} · {accountDetails?.accountType || 'Investment'} · {accountDetails?.currency || 'USD'}
        </p>

        {skippedData && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3 text-amber-600 dark:text-amber-400">
              <SparklesIcon className="size-5" />
              <span className="font-medium">Import your data to start tracking</span>
            </div>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="space-y-3">
        <button
          type="button"
          onClick={onViewAccount}
          className="w-full px-6 py-3.5 rounded-xl text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 transition-colors cursor-pointer"
        >
          View Account
        </button>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onAddAnother}
            className="flex-1 px-6 py-3 rounded-xl text-base font-semibold border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
          >
            Add Another
          </button>
          <button
            type="button"
            onClick={onDone}
            className="flex-1 px-6 py-3 rounded-xl text-base font-semibold border-2 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
