import { useState, useEffect } from 'react';
import { cn } from '../../lib';
import { SUPPORTED_CURRENCIES } from '../../contexts';
import { XMarkIcon } from './icons';

export function PortfolioModal({ isOpen, onClose, portfolio, onSave, loading }) {
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [description, setDescription] = useState('');

  const isEditing = !!portfolio;

  function getSubmitLabel() {
    if (loading) return 'Saving...';
    if (isEditing) return 'Save Changes';
    return 'Create Portfolio';
  }

  useEffect(() => {
    if (isOpen) {
      if (portfolio) {
        setName(portfolio.name || '');
        setCurrency(portfolio.default_currency || 'USD');
        setDescription(portfolio.description || '');
      } else {
        setName('');
        setCurrency('USD');
        setDescription('');
      }
    }
  }, [isOpen, portfolio]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSave({
      name: name.trim(),
      default_currency: currency,
      description: description.trim() || null,
    });
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[var(--bg-primary)] rounded-xl shadow-xl max-w-md w-full">
          <div className="flex items-center justify-between p-4 border-b border-[var(--border-primary)]">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              {isEditing ? 'Edit Portfolio' : 'Create Portfolio'}
            </h2>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
            >
              <XMarkIcon className="w-5 h-5 text-[var(--text-secondary)]" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                Portfolio Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., US Investments, Retirement"
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm',
                  'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                )}
                autoFocus
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                Default Currency
              </label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm',
                  'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
                  'cursor-pointer'
                )}
                disabled={loading}
              >
                {SUPPORTED_CURRENCIES.map((c) => (
                  <option key={c.code} value={c.code}>{c.code}</option>
                ))}
              </select>
              <p className="text-xs text-[var(--text-tertiary)] mt-1">
                Values will be displayed in this currency when viewing this portfolio
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                Description <span className="text-[var(--text-tertiary)]">(optional)</span>
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add notes about this portfolio..."
                rows={3}
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm resize-none',
                  'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                )}
                disabled={loading}
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors cursor-pointer disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !name.trim()}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
              >
                {getSubmitLabel()}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
