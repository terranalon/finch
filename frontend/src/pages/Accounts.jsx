/**
 * Accounts Page - Finch Redesign
 *
 * Purpose: Account management with integrated import flow
 *
 * Wired to real API endpoints:
 * - GET /api/accounts
 * - GET /api/dashboard/summary (for account values)
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn, formatCurrency, api } from '../lib';
import { useCurrency, usePortfolio } from '../contexts';
import { PageContainer } from '../components/layout';
import { Skeleton } from '../components/ui';
import { ApiCredentialsModal } from '../components/ApiCredentialsModal';

// ============================================
// ICONS
// ============================================

function PlusIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function ChevronDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
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

function CloudArrowUpIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
    </svg>
  );
}

function LinkIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
    </svg>
  );
}

function DocumentArrowUpIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
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

function ExclamationTriangleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
    </svg>
  );
}

function PencilIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" />
    </svg>
  );
}

function ArrowRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
    </svg>
  );
}

function BuildingLibraryIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z" />
    </svg>
  );
}

function ChartBarIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
    </svg>
  );
}

function CheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
    </svg>
  );
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

const formatLastSync = (dateStr) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours === 0) {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      return `${diffMins} minutes ago`;
    }
    return `${diffHours} hours ago`;
  } else if (diffDays === 1) {
    return 'Yesterday';
  } else if (diffDays < 30) {
    return `${diffDays} days ago`;
  } else {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }
};

const formatDateShort = (dateStr) => {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
};

const getStatusInfo = (lastSync) => {
  const date = new Date(lastSync);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

  if (diffDays <= 7) {
    return { status: 'connected', label: 'Connected', color: 'text-emerald-600 dark:text-emerald-400' };
  } else if (diffDays <= 30) {
    return { status: 'stale', label: 'Needs sync', color: 'text-amber-600 dark:text-amber-400' };
  } else {
    return { status: 'outdated', label: 'Outdated', color: 'text-red-600 dark:text-red-400' };
  }
};

// ============================================
// ALERT DIALOG COMPONENT
// ============================================

function AlertDialog({ isOpen, onClose, onConfirm, title, description, confirmLabel = 'Delete', variant = 'danger' }) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />

      {/* Dialog */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[var(--bg-primary)] rounded-xl shadow-xl max-w-md w-full p-6">
          <div className="flex items-start gap-4">
            <div className={cn(
              'p-2 rounded-full',
              variant === 'danger' ? 'bg-red-100 dark:bg-red-950/40' : 'bg-amber-100 dark:bg-amber-950/40'
            )}>
              <ExclamationTriangleIcon className={cn(
                'w-6 h-6',
                variant === 'danger' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'
              )} />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h3>
              <p className="text-sm text-[var(--text-secondary)] mt-1">{description}</p>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors cursor-pointer',
                variant === 'danger'
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-amber-600 hover:bg-amber-700'
              )}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// ============================================
// ADD ACCOUNT MODAL
// ============================================

function AddAccountModal({ isOpen, onClose, onAccountCreated, brokers, portfolioId }) {
  const [formData, setFormData] = useState({
    name: '',
    broker_type: '',
    account_type: 'Investment',
    currency: 'USD',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      // Get the broker name from the selected broker type
      const selectedBroker = brokers.find((b) => b.type === formData.broker_type);

      const res = await api('/accounts', {
        method: 'POST',
        body: JSON.stringify({
          name: formData.name,
          broker_type: formData.broker_type,
          institution: selectedBroker?.name || formData.broker_type,
          account_type: formData.account_type,
          currency: formData.currency,
          portfolio_id: portfolioId,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create account');
      }

      // Reset form and close modal
      setFormData({
        name: '',
        broker_type: '',
        account_type: 'Investment',
        currency: 'USD',
      });
      onClose();
      onAccountCreated?.();
    } catch (err) {
      console.error('Error creating account:', err);
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[var(--bg-primary)] rounded-xl shadow-xl max-w-md w-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-[var(--border-primary)]">
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">Add Account</h2>
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
                Account Name
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Main Portfolio"
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm',
                  'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                )}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                Broker
              </label>
              <select
                required
                value={formData.broker_type}
                onChange={(e) => setFormData({ ...formData, broker_type: e.target.value })}
                className={cn(
                  'w-full px-3 py-2.5 rounded-lg text-sm',
                  'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                  'text-[var(--text-primary)]',
                  'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
                  'cursor-pointer'
                )}
              >
                <option value="">Select broker...</option>
                {brokers.map((broker) => (
                  <option key={broker.type} value={broker.type}>
                    {broker.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Account Type
                </label>
                <select
                  value={formData.account_type}
                  onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
                  className={cn(
                    'w-full px-3 py-2.5 rounded-lg text-sm',
                    'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                    'text-[var(--text-primary)]',
                    'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
                    'cursor-pointer'
                  )}
                >
                  <option value="Investment">Investment</option>
                  <option value="IRA">IRA</option>
                  <option value="401k">401(k)</option>
                  <option value="Crypto">Crypto</option>
                  <option value="Savings">Savings</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                  Currency
                </label>
                <select
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  className={cn(
                    'w-full px-3 py-2.5 rounded-lg text-sm',
                    'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
                    'text-[var(--text-primary)]',
                    'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
                    'cursor-pointer'
                  )}
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="ILS">ILS</option>
                </select>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors cursor-pointer disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? 'Creating...' : 'Create Account'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

// ============================================
// DATA COVERAGE BAR
// ============================================

function DataCoverageBar({ coverage }) {
  if (!coverage || !coverage.start_date || !coverage.end_date) {
    return (
      <div className="text-sm text-[var(--text-tertiary)]">
        No data coverage information available
      </div>
    );
  }

  const startDate = new Date(coverage.start_date);
  const endDate = new Date(coverage.end_date);
  const totalDays = Math.max(1, (endDate - startDate) / (1000 * 60 * 60 * 24));

  // Calculate gap positions (API returns start_date/end_date, not start/end)
  const gaps = coverage.gaps || [];
  const gapSegments = gaps.map((gap) => {
    const gapStart = new Date(gap.start_date);
    const gapEnd = new Date(gap.end_date);
    const startPercent = ((gapStart - startDate) / (1000 * 60 * 60 * 24) / totalDays) * 100;
    const widthPercent = Math.max(1, ((gapEnd - gapStart) / (1000 * 60 * 60 * 24) / totalDays) * 100);
    return { startPercent, widthPercent, days: gap.days };
  });

  return (
    <div>
      <div className="flex justify-between text-xs text-[var(--text-tertiary)] mb-2">
        <span>{formatDateShort(coverage.start_date)}</span>
        <span>{formatDateShort(coverage.end_date)}</span>
      </div>
      <div className="relative h-2 bg-emerald-100 dark:bg-emerald-950/40 rounded-full overflow-hidden">
        {/* Filled bar */}
        <div className="absolute inset-0 bg-emerald-500 dark:bg-emerald-400 rounded-full" />
        {/* Gap overlays */}
        {gapSegments.map((gap, i) => (
          <div
            key={i}
            className="absolute top-0 bottom-0 bg-amber-400 dark:bg-amber-500"
            style={{ left: `${gap.startPercent}%`, width: `${gap.widthPercent}%` }}
            title={`${gap.days} day gap`}
          />
        ))}
      </div>
      <div className="flex items-center gap-4 mt-2 text-xs text-[var(--text-secondary)]">
        <span>{(coverage.transactions || 0).toLocaleString()} transactions</span>
        {coverage.sources > 0 && (
          <span>{coverage.sources} source{coverage.sources > 1 ? 's' : ''}</span>
        )}
        {gaps.length > 0 && (
          <span className="text-amber-600 dark:text-amber-400">
            {gaps.length} gap{gaps.length > 1 ? 's' : ''} detected
          </span>
        )}
      </div>
    </div>
  );
}

// ============================================
// ACCOUNT CARD COMPONENT
// ============================================

function AccountCard({ account, currency, brokerConfig, onDelete, onRename, onRefresh }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(account.name);
  const [showApiModal, setShowApiModal] = useState(false);
  const [hasApiCredentials, setHasApiCredentials] = useState(false);
  const navigate = useNavigate();
  const statusInfo = getStatusInfo(account.last_sync);
  const inputRef = React.useRef(null);
  const fileInputRef = React.useRef(null);

  // Get broker config (API support and file formats)
  const supportsApi = brokerConfig?.has_api ?? false;
  const supportedFormats = brokerConfig?.supported_formats || [];
  const formatDisplay = supportedFormats.map(f => f.replace('.', '').toUpperCase()).join(', ') || 'Files';
  const acceptFormats = supportedFormats.join(',') || '*';

  // Check if API credentials exist
  useEffect(() => {
    if (supportsApi && account.id) {
      api(`/brokers/${account.broker_type}/credentials/${account.id}`)
        .then((res) => {
          if (res.ok) {
            return res.json();
          }
          return null;
        })
        .then((data) => {
          setHasApiCredentials(data?.has_credentials ?? false);
        })
        .catch(() => setHasApiCredentials(false));
    }
  }, [supportsApi, account.id, account.broker_type]);

  const handleEditClick = (e) => {
    e.stopPropagation();
    setEditName(account.name);
    setIsEditing(true);
    // Focus input after render
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const handleSaveEdit = (e) => {
    e.stopPropagation();
    if (editName.trim() && editName.trim() !== account.name) {
      onRename(account.id, editName.trim());
    }
    setIsEditing(false);
  };

  const handleCancelEdit = (e) => {
    e.stopPropagation();
    setEditName(account.name);
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSaveEdit(e);
    } else if (e.key === 'Escape') {
      handleCancelEdit(e);
    }
  };

  const handleViewDetails = (e) => {
    e.stopPropagation();
    navigate(`/accounts/${account.id}`);
  };

  const handleUploadFile = (e) => {
    e.stopPropagation();
    // Trigger file input click
    fileInputRef.current?.click();
  };

  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file extension
    const fileName = file.name.toLowerCase();
    const fileExt = '.' + fileName.split('.').pop();
    const isValidFormat = supportedFormats.length === 0 || supportedFormats.some(ext => fileExt === ext.toLowerCase());

    if (!isValidFormat) {
      alert(`Invalid file format. ${account.institution} only supports: ${formatDisplay}`);
      e.target.value = ''; // Reset file input
      return;
    }

    // Upload the file to the API
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('broker_type', account.broker_type);

      const res = await api(`/broker-data/upload/${account.id}`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const result = await res.json();
        alert(`Successfully imported ${result.stats?.total_records || 0} records from ${file.name}`);
        // Refresh the page to show updated coverage
        window.location.reload();
      } else {
        const error = await res.json();
        // Handle both string and object error details
        const detail = error.detail;
        const errorMessage =
          typeof detail === 'string'
            ? detail
            : detail?.message || detail?.error || JSON.stringify(detail);
        alert(`Import failed: ${errorMessage}`);
      }
    } catch (err) {
      console.error('Upload error:', err);
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
      e.target.value = ''; // Reset file input
    }
  };

  const handleConnectApi = (e) => {
    e.stopPropagation();
    setShowApiModal(true);
  };

  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] overflow-hidden shadow-sm dark:shadow-none">
      {/* Card Header - Always visible */}
      <div
        onClick={() => !isEditing && setIsExpanded(!isExpanded)}
        className="flex items-center justify-between p-5 cursor-pointer hover:bg-[var(--bg-tertiary)] transition-colors"
      >
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-accent/10">
            <ChartBarIcon className="w-6 h-6 text-accent" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              {isEditing ? (
                <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <input
                    ref={inputRef}
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onBlur={handleSaveEdit}
                    className={cn(
                      'px-2 py-0.5 rounded text-sm font-semibold',
                      'bg-[var(--bg-primary)] border border-accent',
                      'text-[var(--text-primary)]',
                      'focus:outline-none focus:ring-2 focus:ring-accent/50'
                    )}
                  />
                  <button
                    onClick={handleSaveEdit}
                    className="p-1 rounded hover:bg-emerald-100 dark:hover:bg-emerald-950/40 transition-colors cursor-pointer"
                    title="Save"
                  >
                    <CheckIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-950/40 transition-colors cursor-pointer"
                    title="Cancel"
                  >
                    <XMarkIcon className="w-4 h-4 text-red-600 dark:text-red-400" />
                  </button>
                </div>
              ) : (
                <>
                  <h3 className="font-semibold text-[var(--text-primary)]">{account.name}</h3>
                  <button
                    onClick={handleEditClick}
                    className="p-1 rounded hover:bg-[var(--bg-primary)] transition-colors cursor-pointer"
                    title="Rename account"
                  >
                    <PencilIcon className="w-3.5 h-3.5 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]" />
                  </button>
                </>
              )}
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              {account.institution} · {account.account_type}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn('w-2 h-2 rounded-full', {
                'bg-emerald-500': statusInfo.status === 'connected',
                'bg-amber-500': statusInfo.status === 'stale',
                'bg-red-500': statusInfo.status === 'outdated',
              })} />
              <span className={cn('text-xs', statusInfo.color)}>
                {statusInfo.label}
              </span>
              <span className="text-xs text-[var(--text-tertiary)]">
                · Last sync: {formatLastSync(account.last_sync)}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <p className="text-xl font-semibold font-mono tabular-nums text-[var(--text-primary)]">
            {formatCurrency(account.value, currency)}
          </p>
          <ChevronDownIcon className={cn(
            'w-5 h-5 text-[var(--text-tertiary)] transition-transform',
            isExpanded && 'rotate-180'
          )} />
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-[var(--border-primary)]">
          {/* View Details Link */}
          <button
            onClick={handleViewDetails}
            className="w-full flex items-center justify-between p-4 border-b border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer group"
          >
            <span className="text-sm font-medium text-accent group-hover:text-accent/80">
              View Account Details
            </span>
            <ArrowRightIcon className="w-4 h-4 text-accent group-hover:text-accent/80" />
          </button>

          {/* Data Coverage Section */}
          <div className="p-5 border-b border-[var(--border-primary)]">
            <h4 className="text-sm font-medium text-[var(--text-primary)] mb-3">Data Coverage</h4>
            <DataCoverageBar coverage={account.coverage} />
          </div>

          {/* Import Options Section */}
          <div className="p-5 border-b border-[var(--border-primary)]">
            <h4 className="text-sm font-medium text-[var(--text-primary)] mb-3">Import Data</h4>
            <div className={cn('grid gap-3', supportsApi ? 'grid-cols-2' : 'grid-cols-1')}>
              {supportsApi && (
                <button
                  onClick={handleConnectApi}
                  className={cn(
                    'flex items-center justify-center gap-2 p-4 rounded-lg border-2',
                    hasApiCredentials
                      ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/30'
                      : 'border-dashed border-[var(--border-secondary)] hover:border-accent hover:bg-accent/5',
                    'transition-colors cursor-pointer group'
                  )}
                >
                  {hasApiCredentials ? (
                    <CheckIcon className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  ) : (
                    <LinkIcon className="w-5 h-5 text-[var(--text-tertiary)] group-hover:text-accent" />
                  )}
                  <div className="text-left">
                    <p className={cn(
                      'text-sm font-medium',
                      hasApiCredentials
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-[var(--text-primary)] group-hover:text-accent'
                    )}>
                      {hasApiCredentials ? 'API Connected' : 'Connect API'}
                    </p>
                    <p className="text-xs text-[var(--text-tertiary)]">
                      {hasApiCredentials ? 'Click to update' : 'Automatic sync'}
                    </p>
                  </div>
                </button>
              )}

              <button
                onClick={handleUploadFile}
                disabled={isUploading}
                className={cn(
                  'flex items-center justify-center gap-2 p-4 rounded-lg border-2 border-dashed',
                  'border-[var(--border-secondary)] hover:border-accent hover:bg-accent/5',
                  'transition-colors group',
                  isUploading ? 'opacity-50 cursor-wait' : 'cursor-pointer'
                )}
              >
                {isUploading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                    <div className="text-left">
                      <p className="text-sm font-medium text-[var(--text-primary)]">Importing...</p>
                      <p className="text-xs text-[var(--text-tertiary)]">Please wait</p>
                    </div>
                  </>
                ) : (
                  <>
                    <DocumentArrowUpIcon className="w-5 h-5 text-[var(--text-tertiary)] group-hover:text-accent" />
                    <div className="text-left">
                      <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-accent">Upload File</p>
                      <p className="text-xs text-[var(--text-tertiary)]">{formatDisplay || 'Supported formats'}</p>
                    </div>
                  </>
                )}
              </button>
              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept={acceptFormats}
                onChange={handleFileChange}
                className="hidden"
              />
            </div>
          </div>

          {/* Danger Zone */}
          <div className="p-5 bg-red-50/50 dark:bg-red-950/20">
            <h4 className="text-sm font-medium text-red-600 dark:text-red-400 mb-3">Danger Zone</h4>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(account);
              }}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium',
                'border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400',
                'hover:bg-red-100 dark:hover:bg-red-950/40 transition-colors cursor-pointer'
              )}
            >
              <TrashIcon className="w-4 h-4" />
              Delete Account
            </button>
            <p className="text-xs text-[var(--text-tertiary)] mt-2">
              This will permanently delete this account and all associated data.
            </p>
          </div>
        </div>
      )}

      {/* API Credentials Modal */}
      <ApiCredentialsModal
        isOpen={showApiModal}
        onClose={() => setShowApiModal(false)}
        account={account}
        hasCredentials={hasApiCredentials}
        onGoToSettings={() => navigate(`/accounts/${account.id}?tab=settings`)}
        onCredentialsSaved={() => {
          setHasApiCredentials(true);
          onRefresh?.();
        }}
      />
    </div>
  );
}

// ============================================
// EMPTY STATE
// ============================================

function EmptyState({ onAddAccount }) {
  return (
    <div className="text-center py-16">
      <div className="inline-flex p-4 rounded-full bg-[var(--bg-secondary)] mb-4">
        <BuildingLibraryIcon className="w-12 h-12 text-[var(--text-tertiary)]" />
      </div>
      <h3 className="text-lg font-semibold text-[var(--text-primary)]">No accounts yet</h3>
      <p className="text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">
        Add your first investment account to start tracking your portfolio.
      </p>
      <button
        onClick={onAddAccount}
        className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
      >
        <PlusIcon className="w-4 h-4" />
        Add Account
      </button>
    </div>
  );
}

// ============================================
// MAIN COMPONENT
// ============================================

export default function Accounts() {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  // Use portfolio's currency when viewing a specific portfolio, otherwise use global currency
  const currency = portfolioCurrency || globalCurrency;
  const [accounts, setAccounts] = useState([]);
  const [brokerConfig, setBrokerConfig] = useState({}); // Maps broker_type to config
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState({ isOpen: false, account: null });
  const [refreshKey, setRefreshKey] = useState(0);

  // Fetch accounts and values
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      // Build query params - add portfolio_id if a specific portfolio is selected
      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';

      try {
        // Fetch accounts, dashboard summary, and broker config in parallel
        const [accountsRes, dashboardRes, brokerRes] = await Promise.all([
          api(`/accounts?is_active=true${portfolioParam}`),
          api(`/dashboard/summary?display_currency=${currency}${portfolioParam}`),
          api(`/broker-data/supported-brokers`),
        ]);

        if (!accountsRes.ok) {
          throw new Error(`Failed to fetch accounts: ${accountsRes.statusText}`);
        }
        if (!dashboardRes.ok) {
          throw new Error(`Failed to fetch dashboard: ${dashboardRes.statusText}`);
        }

        const [accountsData, dashboardData, brokerData] = await Promise.all([
          accountsRes.json(),
          dashboardRes.json(),
          brokerRes.ok ? brokerRes.json() : [],
        ]);

        // Build broker config map (broker_type -> config)
        const brokerConfigMap = {};
        brokerData.forEach((broker) => {
          brokerConfigMap[broker.type] = {
            name: broker.name,
            supported_formats: broker.supported_formats,
            has_api: broker.has_api,
          };
        });
        setBrokerConfig(brokerConfigMap);

        // Create a map of account values from dashboard data
        const accountValuesMap = {};
        if (dashboardData.accounts) {
          dashboardData.accounts.forEach((acc) => {
            accountValuesMap[acc.id] = acc.value;
          });
        }

        // Fetch coverage data for each account from the broker-data API
        const coveragePromises = accountsData.map(async (account) => {
          try {
            const res = await api(`/broker-data/coverage/${account.id}`);
            if (res.ok) {
              const data = await res.json();
              // The response is keyed by broker type (e.g., 'ibkr', 'meitav')
              const brokerType = account.broker_type;
              const brokerCoverage = data.brokers?.[brokerType];
              if (brokerCoverage && brokerCoverage.has_data) {
                return {
                  id: account.id,
                  coverage: {
                    start_date: brokerCoverage.coverage?.start_date,
                    end_date: brokerCoverage.coverage?.end_date,
                    transactions: brokerCoverage.totals?.transactions || 0,
                    sources: brokerCoverage.totals?.sources || 0,
                    gaps: brokerCoverage.gaps || [],
                  },
                };
              }
            }
          } catch (err) {
            console.error(`Error fetching coverage for account ${account.id}:`, err);
          }
          // Default coverage if API fails
          return {
            id: account.id,
            coverage: {
              start_date: account.created_at?.split('T')[0],
              end_date: new Date().toISOString().split('T')[0],
              transactions: 0,
              sources: 0,
              gaps: [],
            },
          };
        });

        const coverageResults = await Promise.all(coveragePromises);
        const coverageMap = {};
        coverageResults.forEach((c) => {
          coverageMap[c.id] = c.coverage;
        });

        // Merge account data with values and actual coverage data
        const enrichedAccounts = accountsData.map((account) => ({
          ...account,
          value: accountValuesMap[account.id] || 0,
          last_sync: account.updated_at || account.created_at,
          coverage: coverageMap[account.id],
        }));

        setAccounts(enrichedAccounts);
      } catch (err) {
        console.error('Error fetching accounts data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [currency, selectedPortfolioId, refreshKey]);

  const handleDeleteAccount = (account) => {
    setDeleteDialog({ isOpen: true, account });
  };

  const confirmDelete = async () => {
    try {
      const res = await api(`/accounts/${deleteDialog.account.id}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        throw new Error('Failed to delete account');
      }
      // Remove from local state
      setAccounts((prev) => prev.filter((a) => a.id !== deleteDialog.account.id));
    } catch (err) {
      console.error('Error deleting account:', err);
      alert('Failed to delete account');
    }
    setDeleteDialog({ isOpen: false, account: null });
  };

  const confirmRename = async (accountId, newName) => {
    try {
      const res = await api(`/accounts/${accountId}`, {
        method: 'PUT',
        body: JSON.stringify({ name: newName }),
      });
      if (!res.ok) {
        throw new Error('Failed to rename account');
      }
      // Update local state
      setAccounts((prev) =>
        prev.map((a) => (a.id === accountId ? { ...a, name: newName } : a))
      );
    } catch (err) {
      console.error('Error renaming account:', err);
      alert('Failed to rename account');
    }
  };

  const totalValue = accounts.reduce((sum, acc) => sum + (acc.value || 0), 0);

  // Loading state
  if (loading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Accounts</h1>
            <Skeleton className="h-5 w-48 mt-2" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" />
          ))}
        </div>
      </PageContainer>
    );
  }

  // Error state
  if (error) {
    return (
      <PageContainer>
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Accounts</h1>
        </div>
        <div className="text-center py-12">
          <p className="text-negative mb-2">Error loading accounts</p>
          <p className="text-[var(--text-secondary)] text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/90 transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Accounts</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            {accounts.length} accounts · {formatCurrency(totalValue, currency)} total
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
        >
          <PlusIcon className="w-4 h-4" />
          Add Account
        </button>
      </div>

      {/* Account List */}
      {accounts.length === 0 ? (
        <EmptyState onAddAccount={() => setShowAddModal(true)} />
      ) : (
        <div className="space-y-4">
          {accounts.map((account) => (
            <AccountCard
              key={account.id}
              account={account}
              currency={currency}
              brokerConfig={brokerConfig[account.broker_type]}
              onDelete={handleDeleteAccount}
              onRename={confirmRename}
              onRefresh={() => setRefreshKey((k) => k + 1)}
            />
          ))}
        </div>
      )}

      {/* Add Account Modal */}
      <AddAccountModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAccountCreated={() => setRefreshKey((k) => k + 1)}
        brokers={Object.entries(brokerConfig).map(([type, config]) => ({
          type,
          name: config.name,
          supports_api: config.has_api,
        }))}
        portfolioId={selectedPortfolioId}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        isOpen={deleteDialog.isOpen}
        onClose={() => setDeleteDialog({ isOpen: false, account: null })}
        onConfirm={confirmDelete}
        title="Delete Account"
        description={`Are you sure you want to delete "${deleteDialog.account?.name}"? This action cannot be undone and all associated transaction data will be permanently removed.`}
        confirmLabel="Delete Account"
        variant="danger"
      />
    </PageContainer>
  );
}
