/**
 * Settings Page Mock - Finch Redesign
 *
 * Purpose: User settings, preferences, and account management
 *
 * This is a static mock with hardcoded data for review.
 * After approval, it will be wired up to real API endpoints.
 */

import { useState } from 'react';
import { cn } from '../lib';
import { api } from '../lib/api';
import { useTheme, useCurrency, usePortfolio, useAuth } from '../contexts';
import { PageContainer } from '../components/layout';
import { ChangePassword } from '../components/ChangePassword';
import { TotpSetup, EmailOtpSetup, DisableMfa, RegenerateRecoveryCodes } from '../components/MfaSetup';

// ============================================
// MOCK DATA - Replace with real API data later
// ============================================

const MOCK_USER = {
  name: 'John Doe',
  email: 'john.doe@example.com',
  avatar: null,
  created_at: '2023-01-15',
};

const SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'ILS', 'JPY', 'CAD', 'AUD'];

// ============================================
// ICONS
// ============================================

function UserCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}

function SwatchIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.098 19.902a3.75 3.75 0 0 0 5.304 0l6.401-6.402M6.75 21A3.75 3.75 0 0 1 3 17.25V4.125C3 3.504 3.504 3 4.125 3h5.25c.621 0 1.125.504 1.125 1.125v4.072M6.75 21a3.75 3.75 0 0 0 3.75-3.75V8.197M6.75 21h13.125c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125h-4.072M10.5 8.197l2.88-2.88c.438-.439 1.15-.439 1.59 0l3.712 3.713c.44.44.44 1.152 0 1.59l-2.879 2.88M6.75 17.25h.008v.008H6.75v-.008Z" />
    </svg>
  );
}

function CurrencyDollarIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function BellIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
    </svg>
  );
}

function ShieldCheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
    </svg>
  );
}

function SunIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
    </svg>
  );
}

function MoonIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
    </svg>
  );
}

function ComputerDesktopIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" />
    </svg>
  );
}

function BriefcaseIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0M12 12.75h.008v.008H12v-.008Z" />
    </svg>
  );
}

function PencilIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
    </svg>
  );
}

function TrashIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
    </svg>
  );
}

function PlusIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

// ============================================
// COMPONENTS
// ============================================

function SettingsSection({ icon: Icon, title, description, children }) {
  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden shadow-sm dark:shadow-none">
      <div className="p-6 border-b border-[var(--border-primary)]">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-accent/10">
            <Icon className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
            <p className="text-sm text-[var(--text-secondary)]">{description}</p>
          </div>
        </div>
      </div>
      <div className="p-6">{children}</div>
    </div>
  );
}

function FormField({ label, children, hint }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-[var(--text-primary)]">{label}</label>
      {children}
      {hint && <p className="text-xs text-[var(--text-tertiary)]">{hint}</p>}
    </div>
  );
}

function ThemeSelector({ value, onChange }) {
  const options = [
    { id: 'light', label: 'Light', icon: SunIcon },
    { id: 'dark', label: 'Dark', icon: MoonIcon },
    { id: 'system', label: 'System', icon: ComputerDesktopIcon },
  ];

  return (
    <div className="flex gap-3">
      {options.map((option) => {
        const Icon = option.icon;
        const isSelected = value === option.id;

        return (
          <button
            key={option.id}
            onClick={() => onChange(option.id)}
            className={cn(
              'flex-1 flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-colors cursor-pointer',
              isSelected
                ? 'border-accent bg-accent/5'
                : 'border-[var(--border-primary)] hover:border-[var(--border-secondary)]'
            )}
          >
            <Icon className={cn('w-6 h-6', isSelected ? 'text-accent' : 'text-[var(--text-secondary)]')} />
            <span className={cn('text-sm font-medium', isSelected ? 'text-accent' : 'text-[var(--text-secondary)]')}>
              {option.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function Toggle({ checked, onChange, label }) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <span className="text-sm text-[var(--text-primary)]">{label}</span>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative w-11 h-6 rounded-full transition-colors cursor-pointer',
          checked ? 'bg-accent' : 'bg-[var(--border-secondary)]'
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform shadow-sm',
            checked && 'translate-x-5'
          )}
        />
      </button>
    </label>
  );
}

function StarIcon({ className, filled }) {
  if (filled) {
    return (
      <svg className={className} viewBox="0 0 24 24" fill="currentColor">
        <path fillRule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.007 5.404.433c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.433 2.082-5.006z" clipRule="evenodd" />
      </svg>
    );
  }
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
    </svg>
  );
}

function XMarkIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}

// ============================================
// PORTFOLIO MODAL
// ============================================

function PortfolioModal({ isOpen, onClose, portfolio, onSave, loading }) {
  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [description, setDescription] = useState('');

  const isEditing = !!portfolio;

  // Reset form when modal opens/closes or portfolio changes
  React.useEffect(() => {
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
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[var(--bg-primary)] rounded-xl shadow-xl max-w-md w-full">
          {/* Header */}
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

          {/* Form */}
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
                  <option key={c} value={c}>{c}</option>
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
                {loading ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Portfolio'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

function PortfolioManagement() {
  const { portfolios, refetchPortfolios } = usePortfolio();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPortfolio, setEditingPortfolio] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const openCreateModal = () => {
    setEditingPortfolio(null);
    setModalOpen(true);
  };

  const openEditModal = (portfolio) => {
    setEditingPortfolio(portfolio);
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setEditingPortfolio(null);
  };

  const handleSave = async (data) => {
    setLoading(true);
    setError('');
    try {
      const isEditing = !!editingPortfolio;
      const url = isEditing ? `/portfolios/${editingPortfolio.id}` : '/portfolios';
      const method = isEditing ? 'PUT' : 'POST';

      const response = await api(url, {
        method,
        body: JSON.stringify(data),
      });

      if (response.ok) {
        closeModal();
        await refetchPortfolios();
      } else {
        const result = await response.json();
        setError(result.detail || `Failed to ${isEditing ? 'update' : 'create'} portfolio`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefault = async (portfolioId) => {
    setLoading(true);
    setError('');
    try {
      const response = await api(`/portfolios/${portfolioId}/set-default`, {
        method: 'PUT',
      });

      if (response.ok) {
        await refetchPortfolios();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to set default portfolio');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (portfolioId) => {
    if (!window.confirm('Are you sure you want to delete this portfolio?')) return;

    setLoading(true);
    setError('');
    try {
      const response = await api(`/portfolios/${portfolioId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await refetchPortfolios();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to delete portfolio');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SettingsSection
      icon={BriefcaseIcon}
      title="Portfolios"
      description="Manage your investment portfolios"
    >
      <div className="space-y-3">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => setError('')}
              className="text-red-600 dark:text-red-400 hover:underline cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Portfolio List */}
        {portfolios.map((portfolio) => (
          <div
            key={portfolio.id}
            className={cn(
              "flex items-center justify-between p-4 rounded-lg",
              portfolio.is_default
                ? "bg-accent/5 border border-accent/30"
                : "bg-[var(--bg-tertiary)]"
            )}
          >
            <div className="flex items-center gap-3">
              {portfolio.is_default && (
                <StarIcon className="w-5 h-5 text-amber-500" filled />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-[var(--text-primary)]">
                    {portfolio.name}
                  </p>
                  {portfolio.is_default && (
                    <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                      Default
                    </span>
                  )}
                </div>
                <p className="text-xs text-[var(--text-secondary)]">
                  {portfolio.account_count || 0} account{(portfolio.account_count || 0) !== 1 ? 's' : ''} · {portfolio.default_currency || 'USD'}
                  {portfolio.description && ` · ${portfolio.description}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!portfolio.is_default && (
                <button
                  onClick={() => handleSetDefault(portfolio.id)}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-lg text-xs font-medium text-[var(--text-secondary)] hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 border border-[var(--border-primary)] hover:border-amber-300 dark:hover:border-amber-700 transition-colors cursor-pointer disabled:opacity-50"
                >
                  Set as Default
                </button>
              )}
              <button
                onClick={() => openEditModal(portfolio)}
                className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-primary)] transition-colors cursor-pointer"
                title="Edit portfolio"
              >
                <PencilIcon className="w-4 h-4" />
              </button>
              {portfolios.length > 1 && (portfolio.account_count || 0) === 0 && !portfolio.is_default && (
                <button
                  onClick={() => handleDelete(portfolio.id)}
                  className="p-2 rounded-lg text-[var(--text-secondary)] hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors cursor-pointer"
                  title="Delete portfolio"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}

        {/* Create New Portfolio Button */}
        <button
          onClick={openCreateModal}
          className={cn(
            'w-full p-4 rounded-lg border-2 border-dashed',
            'border-[var(--border-primary)] hover:border-accent',
            'text-[var(--text-secondary)] hover:text-accent',
            'transition-colors cursor-pointer text-sm',
            'flex items-center justify-center gap-2'
          )}
        >
          <PlusIcon className="w-4 h-4" />
          Create New Portfolio
        </button>
      </div>

      {/* Portfolio Modal */}
      <PortfolioModal
        isOpen={modalOpen}
        onClose={closeModal}
        portfolio={editingPortfolio}
        onSave={handleSave}
        loading={loading}
      />
    </SettingsSection>
  );
}

// ============================================
// SECURITY SECTION
// ============================================

function SecuritySection() {
  const [modal, setModal] = useState(null); // null, 'password', 'totp', 'email', 'disable', 'regenerate'
  const [mfaEnabled, setMfaEnabled] = useState(false);

  // In a real app, you'd fetch MFA status from the API
  // For now, we track it locally after setup

  const closeModal = () => setModal(null);

  const handleMfaComplete = () => {
    setMfaEnabled(true);
    closeModal();
  };

  const handleMfaDisabled = () => {
    setMfaEnabled(false);
    closeModal();
  };

  return (
    <SettingsSection
      icon={ShieldCheckIcon}
      title="Security"
      description="Password and authentication settings"
    >
      <div className="space-y-4">
        {/* Password */}
        <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--bg-tertiary)]">
          <div>
            <p className="text-sm font-medium text-[var(--text-primary)]">Password</p>
            <p className="text-xs text-[var(--text-secondary)]">Change your account password</p>
          </div>
          <button
            onClick={() => setModal('password')}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
          >
            Change Password
          </button>
        </div>

        {/* Two-Factor Authentication */}
        <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">Two-factor authentication</p>
              <p className="text-xs text-[var(--text-secondary)]">
                {mfaEnabled
                  ? 'Your account is protected with 2FA'
                  : 'Add an extra layer of security to your account'}
              </p>
            </div>
            {mfaEnabled ? (
              <span className="px-2 py-1 rounded text-xs font-medium bg-positive/10 text-positive">
                Enabled
              </span>
            ) : (
              <span className="px-2 py-1 rounded text-xs font-medium bg-[var(--text-tertiary)]/10 text-[var(--text-tertiary)]">
                Not enabled
              </span>
            )}
          </div>

          {!mfaEnabled ? (
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => setModal('totp')}
                className="flex-1 px-3 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
              >
                Set up Authenticator App
              </button>
              <button
                onClick={() => setModal('email')}
                className="flex-1 px-3 py-2 rounded-lg text-sm font-medium bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
              >
                Use Email OTP
              </button>
            </div>
          ) : (
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => setModal('regenerate')}
                className="flex-1 px-3 py-2 rounded-lg text-sm font-medium bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
              >
                Regenerate Recovery Codes
              </button>
              <button
                onClick={() => setModal('disable')}
                className="px-3 py-2 rounded-lg text-sm font-medium text-negative hover:bg-negative/10 transition-colors cursor-pointer"
              >
                Disable
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {modal && (
        <>
          <div className="fixed inset-0 bg-black/50 z-50" onClick={closeModal} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="bg-[var(--bg-primary)] rounded-xl shadow-xl max-w-md w-full p-6">
              {modal === 'password' && (
                <ChangePassword onComplete={closeModal} onCancel={closeModal} />
              )}
              {modal === 'totp' && (
                <TotpSetup onComplete={handleMfaComplete} onCancel={closeModal} />
              )}
              {modal === 'email' && (
                <EmailOtpSetup onComplete={handleMfaComplete} onCancel={closeModal} />
              )}
              {modal === 'disable' && (
                <DisableMfa onComplete={handleMfaDisabled} onCancel={closeModal} />
              )}
              {modal === 'regenerate' && (
                <RegenerateRecoveryCodes onComplete={closeModal} onCancel={closeModal} />
              )}
            </div>
          </div>
        </>
      )}
    </SettingsSection>
  );
}

// ============================================
// MAIN COMPONENT
// ============================================

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const { currency, setCurrency } = useCurrency();
  const { user, updatePreferences } = useAuth();

  // Form states
  const [profile, setProfile] = useState({
    name: MOCK_USER.name,
    email: MOCK_USER.email,
  });

  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    priceAlerts: false,
    weeklyDigest: true,
    marketNews: false,
  });

  const handleSaveProfile = () => {
    // TODO: Implement API call to save profile
  };

  return (
    <PageContainer>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Settings</h1>
        <p className="text-[var(--text-secondary)] mt-1">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="space-y-6 max-w-3xl">
        {/* Profile Section */}
        <SettingsSection
          icon={UserCircleIcon}
          title="Profile"
          description="Your personal information"
        >
          <div className="space-y-4">
            <FormField label="Full Name">
              <input
                type="text"
                value={profile.name}
                onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm',
                  'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                )}
              />
            </FormField>

            <FormField label="Email Address">
              <input
                type="email"
                value={profile.email}
                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm',
                  'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                )}
              />
            </FormField>

            <div className="pt-2">
              <button
                onClick={handleSaveProfile}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
              >
                Save Changes
              </button>
            </div>
          </div>
        </SettingsSection>

        {/* Portfolios Section */}
        <PortfolioManagement />

        {/* Security Section */}
        <SecuritySection />

        {/* Appearance Section */}
        <SettingsSection
          icon={SwatchIcon}
          title="Appearance"
          description="Customize how Finch looks"
        >
          <div className="space-y-6">
            <FormField label="Theme">
              <ThemeSelector value={theme} onChange={setTheme} />
            </FormField>
          </div>
        </SettingsSection>

        {/* Preferences Section */}
        <SettingsSection
          icon={CurrencyDollarIcon}
          title="Preferences"
          description="Display and regional settings"
        >
          <div className="space-y-4">
            <FormField label="Display Currency" hint="All values will be converted to this currency">
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm',
                  'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
                  'cursor-pointer'
                )}
              >
                {SUPPORTED_CURRENCIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </FormField>

            <div className="pt-2 border-t border-[var(--border-primary)]">
              <Toggle
                checked={user?.show_combined_view ?? true}
                onChange={async (checked) => {
                  try {
                    await updatePreferences({ show_combined_view: checked });
                  } catch {
                    // Preference update failed silently - UI will remain in sync
                  }
                }}
                label="Show 'All Portfolios' option"
              />
              <p className="text-xs text-[var(--text-tertiary)] mt-1">
                When enabled, you can view all portfolios combined in the portfolio selector
              </p>
            </div>
          </div>
        </SettingsSection>

        {/* Notifications Section */}
        <SettingsSection
          icon={BellIcon}
          title="Notifications"
          description="Choose what updates you receive"
        >
          <div className="space-y-4">
            <Toggle
              checked={notifications.emailAlerts}
              onChange={(checked) => setNotifications({ ...notifications, emailAlerts: checked })}
              label="Email alerts for significant portfolio changes"
            />
            <Toggle
              checked={notifications.priceAlerts}
              onChange={(checked) => setNotifications({ ...notifications, priceAlerts: checked })}
              label="Price alerts for watched assets"
            />
            <Toggle
              checked={notifications.weeklyDigest}
              onChange={(checked) => setNotifications({ ...notifications, weeklyDigest: checked })}
              label="Weekly portfolio digest"
            />
            <Toggle
              checked={notifications.marketNews}
              onChange={(checked) => setNotifications({ ...notifications, marketNews: checked })}
              label="Market news and insights"
            />
          </div>
        </SettingsSection>
      </div>
    </PageContainer>
  );
}
