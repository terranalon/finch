import { BrokerLogo } from '../BrokerLogo.jsx';
import { getBrokersByCategory } from '../constants/brokerConfig.js';
import { ArrowLeftIcon } from '../icons.jsx';

export function BrokerSelectionStep({ category, onSelect, onBack }) {
  const brokers = getBrokersByCategory(category.id);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-3 text-balance">
          Select your {category.id === 'crypto' ? 'exchange' : 'broker'}
        </h2>
        <p className="text-gray-500 dark:text-gray-400 text-lg text-pretty">
          Choose from our supported {category.id === 'crypto' ? 'exchanges' : 'brokers'}.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {brokers.map((broker) => (
          <button
            key={broker.type}
            onClick={() => onSelect(broker)}
            className="flex items-center gap-4 p-5 sm:p-6 rounded-2xl border-2 border-gray-200 dark:border-gray-700 hover:border-blue-500 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-all text-left group cursor-pointer"
          >
            <BrokerLogo type={broker.type} />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                {broker.name}
              </h3>
              <div className="flex gap-2 mt-2">
                {broker.hasApi && (
                  <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400">
                    API
                  </span>
                )}
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                  {broker.supportedFormats.map(f => f.replace('.', '').toUpperCase()).join(', ')}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-8">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
        >
          <ArrowLeftIcon className="size-5" />
          <span className="font-medium">Back to account types</span>
        </button>
      </div>
    </div>
  );
}
