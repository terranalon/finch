import { BrokerLogo } from '../BrokerLogo.jsx';
import { getBrokersByCategory } from '../constants/brokerConfig.js';
import { ArrowLeftIcon } from '../icons.jsx';

export function BrokerSelectionStep({ category, onSelect, onBack }) {
  const brokers = getBrokersByCategory(category.id);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)] mb-3 text-balance">
          Select your {category.id === 'crypto' ? 'exchange' : 'broker'}
        </h2>
        <p className="text-[var(--text-tertiary)] text-lg text-pretty">
          Choose from our supported {category.id === 'crypto' ? 'exchanges' : 'brokers'}.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {brokers.map((broker) => (
          <button
            key={broker.type}
            onClick={() => onSelect(broker)}
            className="flex items-center gap-4 p-5 sm:p-6 rounded-2xl border-2 border-[var(--border-primary)] hover:border-accent hover:bg-accent-50/50 dark:hover:bg-accent-900/20 transition-all text-left group cursor-pointer"
          >
            <BrokerLogo type={broker.type} />
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-[var(--text-primary)] group-hover:text-accent dark:group-hover:text-accent-400">
                {broker.name}
              </h3>
              <div className="flex gap-2 mt-2">
                {broker.hasApi && (
                  <span className="px-2 py-0.5 rounded text-xs font-semibold bg-positive-light dark:bg-positive-bg-dark text-positive dark:text-positive-dark">
                    API
                  </span>
                )}
                <span className="px-2 py-0.5 rounded text-xs font-semibold bg-[var(--bg-tertiary)] text-[var(--text-secondary)]">
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
          className="flex items-center gap-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <ArrowLeftIcon className="size-5" />
          <span className="font-medium">Back to account types</span>
        </button>
      </div>
    </div>
  );
}
