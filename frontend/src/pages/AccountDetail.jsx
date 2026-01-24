/**
 * Account Detail Page - Finch Redesign
 *
 * Purpose: Deep dive into a single account with holdings, transactions,
 * performance, import history, and settings.
 */

import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { cn, formatCurrency, api, deleteDataSource, transformTrade, transformDividend, transformForex, transformCash } from '../lib';
import { PageContainer } from '../components/layout';
import { ApiCredentialsModal } from '../components/ApiCredentialsModal';
import { TransactionCard } from '../components/transactions';

/**
 * Calculate Time-Weighted Return using Modified Dietz method
 * This excludes the effect of cash flows (deposits/withdrawals) from returns
 *
 * @param {Array} snapshots - Array of {date, value} objects, sorted by date ascending
 * @param {Array} cashFlows - Array of {date, amount} objects (positive = deposit, negative = withdrawal)
 * @returns {Array} Array of {date, value, performance} objects
 */
function calculateTWR(snapshots, cashFlows) {
  if (!snapshots || snapshots.length === 0) return [];

  const result = [];
  const startDate = new Date(snapshots[0].date);
  const startValue = snapshots[0].value;

  // Create a map of cash flows by date for quick lookup
  const cashFlowMap = new Map();
  if (cashFlows && cashFlows.length > 0) {
    cashFlows.forEach((cf) => {
      const dateKey = cf.date.split('T')[0]; // Normalize to YYYY-MM-DD
      const existing = cashFlowMap.get(dateKey) || 0;
      cashFlowMap.set(dateKey, existing + cf.amount);
    });
  }

  // For each snapshot, calculate cumulative TWR from start
  snapshots.forEach((snapshot, index) => {
    const currentDate = new Date(snapshot.date);
    const currentValue = snapshot.value;

    if (index === 0) {
      // First point is always 0% (baseline)
      result.push({ ...snapshot, performance: 0 });
      return;
    }

    // Calculate total days in period
    const totalDays = Math.max(1, (currentDate - startDate) / (1000 * 60 * 60 * 24));

    // Sum all cash flows and their weighted contributions
    let totalCashFlow = 0;
    let weightedCashFlow = 0;

    cashFlowMap.forEach((amount, dateStr) => {
      const cfDate = new Date(dateStr);
      if (cfDate > startDate && cfDate <= currentDate) {
        totalCashFlow += amount;
        // Weight = proportion of period remaining after cash flow
        const daysFromStart = (cfDate - startDate) / (1000 * 60 * 60 * 24);
        const weight = (totalDays - daysFromStart) / totalDays;
        weightedCashFlow += amount * weight;
      }
    });

    // Modified Dietz formula:
    // Return = (Ending Value - Beginning Value - Cash Flows) / (Beginning Value + Weighted Cash Flows)
    const denominator = startValue + weightedCashFlow;
    let performance = 0;

    if (denominator > 0) {
      performance = ((currentValue - startValue - totalCashFlow) / denominator) * 100;
    }

    result.push({ ...snapshot, performance });
  });

  return result;
}

// ============================================
// ICONS
// ============================================

function ArrowLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
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

function LinkIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
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

function DocumentArrowUpIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

function CheckCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function ExclamationCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
    </svg>
  );
}

function CloudArrowDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9.75v6.75m0 0-3-3m3 3 3-3m-8.25 6a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
    </svg>
  );
}

function ChevronLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
    </svg>
  );
}

function ChevronRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
    </svg>
  );
}

function ChevronDoubleLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m18.75 4.5-7.5 7.5 7.5 7.5m-6-15L5.25 12l7.5 7.5" />
    </svg>
  );
}

function ChevronDoubleRightIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m5.25 4.5 7.5 7.5-7.5 7.5m6-15 7.5 7.5-7.5 7.5" />
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

// ============================================
// UTILITY FUNCTIONS
// ============================================

const formatDateShort = (dateStr) => {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

// Scroll to top of page (used for pagination)
const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

function getStatusInfo(lastSync) {
  const date = new Date(lastSync);
  const now = new Date();
  const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

  if (diffDays <= 7) {
    return { status: 'connected', label: 'Connected', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500' };
  }
  if (diffDays <= 30) {
    return { status: 'stale', label: 'Needs sync', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-500' };
  }
  return { status: 'outdated', label: 'Outdated', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-500' };
}

function formatOverlapWarningDescription(warning) {
  if (!warning) return '';

  const sources = warning.affected_sources || [];
  const sourcesList = sources.length > 0
    ? sources.map(s => `- ${s.identifier} (${s.start_date} to ${s.end_date})`).join('\n')
    : 'None';

  return [
    warning.message,
    '',
    'Affected sources:',
    sourcesList,
    '',
    `Transactions affected: ${warning.affected_transaction_count || 0}`,
    '',
    'Continuing will transfer ownership of duplicate transactions to this new import.',
  ].join('\n');
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

  // API returns start_date/end_date for gaps
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
        <div className="absolute inset-0 bg-emerald-500 dark:bg-emerald-400 rounded-full" />
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
          <span>{coverage.sources} source{coverage.sources !== 1 ? 's' : ''}</span>
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
// STAT CARD COMPONENT
// ============================================

function StatCard({ label, value, subValue, trend, trendDirection }) {
  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-5 shadow-sm dark:shadow-none">
      <p className="text-sm text-[var(--text-secondary)] mb-1">{label}</p>
      <p className="text-2xl font-semibold font-mono tabular-nums text-[var(--text-primary)]">{value}</p>
      {(subValue || trend) && (
        <div className="flex items-center gap-2 mt-1">
          {trend && (
            <span className={cn(
              'text-sm font-medium',
              trendDirection === 'up' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
            )}>
              {trendDirection === 'up' ? '▲' : '▼'} {trend}
            </span>
          )}
          {subValue && (
            <span className="text-sm text-[var(--text-tertiary)]">{subValue}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================
// ALERT DIALOG COMPONENT
// ============================================

function AlertDialog({ isOpen, onClose, onConfirm, title, description, confirmLabel = 'Delete', loadingLabel, variant = 'danger', isLoading = false }) {
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
              <p className="text-sm text-[var(--text-secondary)] mt-1 whitespace-pre-line">{description}</p>
            </div>
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors cursor-pointer disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors cursor-pointer disabled:opacity-50',
                variant === 'danger'
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-amber-600 hover:bg-amber-700'
              )}
            >
              {isLoading ? (loadingLabel || 'Processing...') : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// ============================================
// HOLDINGS TABLE
// ============================================

function HoldingsTable({ holdings }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-[var(--border-primary)]">
            <th className="text-left text-sm font-medium text-[var(--text-secondary)] py-3 px-4">Asset</th>
            <th className="text-right text-sm font-medium text-[var(--text-secondary)] py-3 px-4">Quantity</th>
            <th className="text-right text-sm font-medium text-[var(--text-secondary)] py-3 px-4">Price</th>
            <th className="text-right text-sm font-medium text-[var(--text-secondary)] py-3 px-4">Cost Basis</th>
            <th className="text-right text-sm font-medium text-[var(--text-secondary)] py-3 px-4">Value</th>
            <th className="text-right text-sm font-medium text-[var(--text-secondary)] py-3 px-4">Gain/Loss</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((holding) => (
            <tr key={holding.symbol} className="border-b border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)] transition-colors">
              <td className="py-3 px-4">
                <div>
                  <p className="font-semibold text-[var(--text-primary)]">{holding.symbol}</p>
                  <p className="text-sm text-[var(--text-tertiary)]">{holding.name}</p>
                </div>
              </td>
              <td className="text-right py-3 px-4 font-mono tabular-nums text-[var(--text-primary)]">
                {holding.quantity}
              </td>
              <td className="text-right py-3 px-4 font-mono tabular-nums text-[var(--text-primary)]">
                {formatCurrency(holding.price, holding.currency)}
              </td>
              <td className="text-right py-3 px-4 font-mono tabular-nums text-[var(--text-secondary)]">
                {formatCurrency(holding.cost_basis, holding.currency)}
              </td>
              <td className="text-right py-3 px-4 font-mono tabular-nums font-semibold text-[var(--text-primary)]">
                {formatCurrency(holding.value, holding.currency)}
              </td>
              <td className="text-right py-3 px-4">
                <p className={cn(
                  'font-mono tabular-nums font-semibold',
                  holding.gain >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                )}>
                  {holding.gain >= 0 ? '+' : ''}{formatCurrency(holding.gain, holding.currency)}
                </p>
                <p className={cn(
                  'text-xs',
                  holding.gain >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                )}>
                  {holding.gain >= 0 ? '+' : ''}{holding.gain_pct.toFixed(2)}%
                </p>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================
// IMPORT HISTORY
// ============================================

// Import source item from coverage API
function ImportSourceItem({ source, onDelete, isDeleting }) {
  const isSuccess = source.status === 'completed';
  const filename = source.source_identifier || 'Unknown file';
  const totalRecords = source.stats?.total_records || 0;
  const transactionCount = source.transaction_count || 0;

  return (
    <div className="flex items-start justify-between py-3">
      <div className="flex items-start gap-3">
        <div className={cn(
          'p-2 rounded-lg',
          isSuccess ? 'bg-emerald-50 dark:bg-emerald-950/40' : 'bg-amber-50 dark:bg-amber-950/40'
        )}>
          {isSuccess ? (
            <CheckCircleIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <ExclamationCircleIcon className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">
            {filename}
          </p>
          <p className="text-xs text-[var(--text-tertiary)]">
            {source.start_date && source.end_date
              ? `${formatDateShort(source.start_date)} - ${formatDateShort(source.end_date)}`
              : 'Date range unknown'}
          </p>
          {transactionCount > 0 && (
            <p className="text-xs text-[var(--text-tertiary)]">
              {transactionCount.toLocaleString()} transaction{transactionCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-start gap-3">
        <div className="text-right">
          <p className="text-sm font-medium text-[var(--text-primary)]">
            {totalRecords.toLocaleString()} records
          </p>
          <p className="text-xs text-[var(--text-tertiary)]">
            {source.source_type === 'file_upload' ? 'File upload' : 'API sync'}
          </p>
        </div>
        <button
          onClick={() => onDelete?.(source)}
          disabled={isDeleting}
          className={cn(
            'p-2 rounded-lg transition-colors',
            'text-[var(--text-tertiary)] hover:text-red-600 dark:hover:text-red-400',
            'hover:bg-red-50 dark:hover:bg-red-950/40',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'cursor-pointer'
          )}
          title="Delete import"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// ============================================
// UPLOAD MODAL
// ============================================

function UploadModal({ isOpen, onClose, onUpload, isUploading, supportedFormats, institution }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const dropRef = React.useRef(null);
  const fileInputRef = React.useRef(null);

  const formatDisplay = supportedFormats?.length > 0
    ? supportedFormats.join(', ')
    : 'all file types';

  const validateFile = (file) => {
    if (!file) return false;
    if (!supportedFormats || supportedFormats.length === 0) return true;

    const fileName = file.name.toLowerCase();
    const fileExt = '.' + fileName.split('.').pop();
    return supportedFormats.some((ext) => fileExt === ext.toLowerCase());
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    setError(null);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (validateFile(file)) {
        setSelectedFile(file);
      } else {
        setError(`Invalid file format. ${institution} only supports: ${formatDisplay}`);
      }
    }
  };

  const handleFileSelect = (e) => {
    setError(null);
    const file = e.target.files?.[0];
    if (file) {
      if (validateFile(file)) {
        setSelectedFile(file);
      } else {
        setError(`Invalid file format. ${institution} only supports: ${formatDisplay}`);
        e.target.value = '';
      }
    }
  };

  const handleUpload = () => {
    if (selectedFile) {
      onUpload(selectedFile);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setError(null);
    setIsDragOver(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative bg-[var(--bg-primary)] rounded-xl border border-[var(--border-primary)] shadow-2xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--border-primary)]">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Upload File</h2>
          <button
            onClick={handleClose}
            className="p-1 rounded hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <svg className="w-5 h-5 text-[var(--text-secondary)]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Drop Zone */}
          <div
            ref={dropRef}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              'border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer',
              isDragOver
                ? 'border-accent bg-accent/5'
                : 'border-[var(--border-primary)] hover:border-accent/50 hover:bg-[var(--bg-tertiary)]'
            )}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={supportedFormats?.join(',') || '*'}
              onChange={handleFileSelect}
              className="hidden"
            />

            {selectedFile ? (
              <div>
                <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-emerald-100 dark:bg-emerald-950/40 flex items-center justify-center">
                  <CheckCircleIcon className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <p className="font-medium text-[var(--text-primary)]">{selectedFile.name}</p>
                <p className="text-sm text-[var(--text-tertiary)] mt-1">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                  }}
                  className="mt-3 text-sm text-accent hover:underline"
                >
                  Choose a different file
                </button>
              </div>
            ) : (
              <div>
                <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-accent/10 flex items-center justify-center">
                  <DocumentArrowUpIcon className="w-6 h-6 text-accent" />
                </div>
                <p className="font-medium text-[var(--text-primary)]">
                  Drag & drop your file here
                </p>
                <p className="text-sm text-[var(--text-tertiary)] mt-1">
                  or click to browse
                </p>
                <p className="text-xs text-[var(--text-tertiary)] mt-3">
                  Supported formats: {formatDisplay}
                </p>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900">
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}

          {/* Help Text */}
          <div className="mt-4 p-3 rounded-lg bg-[var(--bg-tertiary)]">
            <p className="text-xs text-[var(--text-secondary)]">
              <strong>Tip:</strong> Export your transactions from {institution} and upload the file here.
              We'll automatically import your holdings and transaction history.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-[var(--border-primary)]">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-lg text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || isUploading}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white transition-colors',
              (!selectedFile || isUploading) ? 'opacity-50 cursor-not-allowed' : 'hover:bg-accent/90 cursor-pointer'
            )}
          >
            {isUploading ? 'Uploading...' : 'Upload & Import'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================
// SETTINGS SECTION
// ============================================

function SettingsSection({ account, brokerConfig, onOpenApiModal, apiCredentialsRef }) {
  const isIbkr = account.broker_type === 'ibkr';
  const [formData, setFormData] = useState({
    name: account.name,
    institution: account.institution,
    account_type: account.account_type,
    currency: account.currency,
    notes: account.notes || '',
  });

  const [credentialsStatus, setCredentialsStatus] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSavingCredentials, setIsSavingCredentials] = useState(false);
  const [isEditingCredentials, setIsEditingCredentials] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [credentialsForm, setCredentialsForm] = useState(
    isIbkr
      ? { flex_token: '', flex_query_id: '' }
      : { api_key: '', api_secret: '' }
  );
  const [credentialsError, setCredentialsError] = useState(null);

  // Fetch credentials status
  useEffect(() => {
    const fetchCredentialsStatus = async () => {
      if (!brokerConfig?.has_api) return;

      try {
        const res = await api(`/brokers/${account.broker_type}/credentials/${account.id}`);
        if (res.ok) {
          const data = await res.json();
          setCredentialsStatus(data);
        }
      } catch (err) {
        console.error('Error fetching credentials status:', err);
      }
    };

    fetchCredentialsStatus();
  }, [account.id, account.broker_type, brokerConfig?.has_api]);

  const handleDeleteCredentials = async () => {
    if (!confirm('Are you sure you want to remove your API credentials? You will need to reconnect to sync data.')) {
      return;
    }

    setIsDeleting(true);
    try {
      const res = await api(`/brokers/${account.broker_type}/credentials/${account.id}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        setCredentialsStatus(null);
        setCredentialsForm(
          isIbkr
            ? { flex_token: '', flex_query_id: '' }
            : { api_key: '', api_secret: '' }
        );
        alert('API credentials removed successfully');
      } else {
        const error = await res.json();
        alert(`Failed to remove credentials: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      alert(`Failed to remove credentials: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSaveCredentials = async () => {
    // Only save fields that have new values
    const hasNewValues = isIbkr
      ? credentialsForm.flex_token || credentialsForm.flex_query_id
      : credentialsForm.api_key || credentialsForm.api_secret;

    if (!hasNewValues) {
      alert('Please enter at least one field to update');
      return;
    }

    setIsSavingCredentials(true);
    setCredentialsError(null);

    try {
      // Build payload with only non-empty fields
      const payload = {};
      if (isIbkr) {
        if (credentialsForm.flex_token) payload.flex_token = credentialsForm.flex_token;
        if (credentialsForm.flex_query_id) payload.flex_query_id = credentialsForm.flex_query_id;
      } else {
        if (credentialsForm.api_key) payload.api_key = credentialsForm.api_key;
        if (credentialsForm.api_secret) payload.api_secret = credentialsForm.api_secret;
      }

      const res = await api(`/brokers/${account.broker_type}/credentials/${account.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        // Clear the form and refetch status
        setCredentialsForm(
          isIbkr
            ? { flex_token: '', flex_query_id: '' }
            : { api_key: '', api_secret: '' }
        );
        // Refetch credentials status
        const statusRes = await api(`/brokers/${account.broker_type}/credentials/${account.id}`);
        if (statusRes.ok) {
          const data = await statusRes.json();
          setCredentialsStatus(data);
        }
        alert('Credentials updated successfully');
      } else {
        const error = await res.json();
        setCredentialsError(error.detail || 'Failed to update credentials');
      }
    } catch (err) {
      setCredentialsError(err.message);
    } finally {
      setIsSavingCredentials(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    setCredentialsError(null);

    try {
      const res = await api(`/brokers/${account.broker_type}/test-credentials/${account.id}`, {
        method: 'POST',
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Connection test failed');
      }

      setTestResult(data);
    } catch (err) {
      setCredentialsError(err.message);
    } finally {
      setIsTesting(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditingCredentials(false);
    setCredentialsForm(
      isIbkr
        ? { flex_token: '', flex_query_id: '' }
        : { api_key: '', api_secret: '' }
    );
    setCredentialsError(null);
    setTestResult(null);
  };

  return (
    <div className="space-y-6">
      {/* Account Details Section */}
      <div>
        <h4 className="text-sm font-medium text-[var(--text-primary)] mb-4">Account Details</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">Account Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg text-sm',
                'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                'text-[var(--text-primary)]',
                'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
              )}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">Institution</label>
            <input
              type="text"
              value={formData.institution}
              onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg text-sm',
                'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                'text-[var(--text-primary)]',
                'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
              )}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">Account Type</label>
            <select
              value={formData.account_type}
              onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg text-sm',
                'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                'text-[var(--text-primary)]',
                'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
                'cursor-pointer'
              )}
            >
              <option value="Brokerage">Brokerage</option>
              <option value="IRA">IRA</option>
              <option value="401k">401(k)</option>
              <option value="Crypto">Crypto</option>
              <option value="Savings">Savings</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">Currency</label>
            <select
              value={formData.currency}
              onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
              className={cn(
                'w-full px-3 py-2.5 rounded-lg text-sm',
                'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
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

        <div className="mt-4">
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">Notes</label>
          <textarea
            value={formData.notes}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            rows={3}
            className={cn(
              'w-full px-3 py-2.5 rounded-lg text-sm',
              'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
              'text-[var(--text-primary)]',
              'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
              'resize-none'
            )}
          />
        </div>

        <div className="flex justify-end mt-4">
          <button className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer">
            Save Changes
          </button>
        </div>
      </div>

      {/* API Credentials Section */}
      {brokerConfig?.has_api && (
        <div ref={apiCredentialsRef} className="pt-6 border-t border-[var(--border-primary)]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-sm font-medium text-[var(--text-primary)]">API Credentials</h4>
              {credentialsStatus?.has_credentials && (
                <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">
                  Connected · Last updated: {credentialsStatus.updated_at ? new Date(credentialsStatus.updated_at).toLocaleDateString() : 'Unknown'}
                </p>
              )}
            </div>
            {credentialsStatus?.has_credentials && !isEditingCredentials && (
              <div className="flex gap-2">
                <button
                  onClick={handleTestConnection}
                  disabled={isTesting}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium border border-[var(--border-primary)] text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer disabled:opacity-50"
                >
                  {isTesting ? 'Testing...' : 'Test Connection'}
                </button>
                <button
                  onClick={() => setIsEditingCredentials(true)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
                >
                  Edit
                </button>
              </div>
            )}
          </div>

          {credentialsStatus?.has_credentials ? (
            <div className="space-y-4">
              {/* Test Result */}
              {testResult && (
                <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
                  <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                    ✓ {testResult.message}
                  </p>
                  {testResult.assets_count !== undefined && (
                    <p className="text-xs text-emerald-600/80 dark:text-emerald-400/80 mt-0.5">
                      Found {testResult.assets_count} assets
                    </p>
                  )}
                </div>
              )}

              {/* Error */}
              {credentialsError && (
                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
                  <p className="text-sm text-red-600 dark:text-red-400">{credentialsError}</p>
                </div>
              )}

              {isEditingCredentials ? (
                <>
                  <p className="text-xs text-[var(--text-tertiary)]">
                    Enter new values to update your credentials. Leave a field empty to keep the current value.
                  </p>
                  {isIbkr ? (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          Flex Token
                        </label>
                        <input
                          type="password"
                          value={credentialsForm.flex_token}
                          onChange={(e) => setCredentialsForm({ ...credentialsForm, flex_token: e.target.value })}
                          placeholder="Enter new token..."
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm',
                            'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                            'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
                            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                          )}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          Flex Query ID
                        </label>
                        <input
                          type="text"
                          value={credentialsForm.flex_query_id}
                          onChange={(e) => setCredentialsForm({ ...credentialsForm, flex_query_id: e.target.value })}
                          placeholder="Enter new ID..."
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm',
                            'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                            'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
                            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                          )}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          API Key
                        </label>
                        <input
                          type="text"
                          value={credentialsForm.api_key}
                          onChange={(e) => setCredentialsForm({ ...credentialsForm, api_key: e.target.value })}
                          placeholder="Enter new key..."
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm',
                            'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                            'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
                            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                          )}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          API Secret
                        </label>
                        <input
                          type="password"
                          value={credentialsForm.api_secret}
                          onChange={(e) => setCredentialsForm({ ...credentialsForm, api_secret: e.target.value })}
                          placeholder="Enter new secret..."
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm',
                            'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                            'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
                            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent'
                          )}
                        />
                      </div>
                    </div>
                  )}

                  <div className="flex justify-between">
                    <button
                      onClick={handleDeleteCredentials}
                      disabled={isDeleting}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors cursor-pointer disabled:opacity-50"
                    >
                      {isDeleting ? 'Removing...' : 'Remove Credentials'}
                    </button>
                    <div className="flex gap-2">
                      <button
                        onClick={handleCancelEdit}
                        className="px-4 py-2 rounded-lg text-sm font-medium border border-[var(--border-primary)] text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveCredentials}
                        disabled={isSavingCredentials}
                        className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {isSavingCredentials ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  {/* Read-only masked fields */}
                  {isIbkr ? (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          Flex Token
                        </label>
                        <input
                          type="text"
                          readOnly
                          value="••••••••••••••••"
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm cursor-not-allowed',
                            'bg-[var(--bg-tertiary)] border border-[var(--border-primary)]',
                            'text-[var(--text-secondary)]'
                          )}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          Flex Query ID
                        </label>
                        <input
                          type="text"
                          readOnly
                          value="••••••••"
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm cursor-not-allowed',
                            'bg-[var(--bg-tertiary)] border border-[var(--border-primary)]',
                            'text-[var(--text-secondary)]'
                          )}
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          API Key
                        </label>
                        <input
                          type="text"
                          readOnly
                          value="••••••••••••••••"
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm cursor-not-allowed',
                            'bg-[var(--bg-tertiary)] border border-[var(--border-primary)]',
                            'text-[var(--text-secondary)]'
                          )}
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
                          API Secret
                        </label>
                        <input
                          type="text"
                          readOnly
                          value="••••••••••••••••"
                          className={cn(
                            'w-full px-3 py-2.5 rounded-lg text-sm cursor-not-allowed',
                            'bg-[var(--bg-tertiary)] border border-[var(--border-primary)]',
                            'text-[var(--text-secondary)]'
                          )}
                        />
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-lg bg-[var(--bg-primary)] border border-[var(--border-primary)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">No API credentials configured</p>
                  <p className="text-xs text-[var(--text-tertiary)] mt-0.5">Connect your API to enable automatic syncing</p>
                </div>
                <button
                  onClick={onOpenApiModal}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
                >
                  Connect API
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================
// LOADING SKELETON
// ============================================

function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      {/* Back Link Skeleton */}
      <div className="h-4 bg-[var(--bg-tertiary)] rounded w-32 mb-6"></div>

      {/* Header Skeleton */}
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-xl bg-[var(--bg-tertiary)]"></div>
          <div>
            <div className="h-7 bg-[var(--bg-tertiary)] rounded w-40 mb-2"></div>
            <div className="h-4 bg-[var(--bg-tertiary)] rounded w-56 mb-2"></div>
            <div className="h-4 bg-[var(--bg-tertiary)] rounded w-24"></div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="h-10 bg-[var(--bg-tertiary)] rounded-lg w-28"></div>
          <div className="h-10 bg-[var(--bg-tertiary)] rounded-lg w-28"></div>
        </div>
      </div>

      {/* Stats Grid Skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-5">
            <div className="h-4 bg-[var(--bg-tertiary)] rounded w-20 mb-2"></div>
            <div className="h-8 bg-[var(--bg-tertiary)] rounded w-32 mb-2"></div>
            <div className="h-4 bg-[var(--bg-tertiary)] rounded w-24"></div>
          </div>
        ))}
      </div>

      {/* Tabs Skeleton */}
      <div className="border-b border-[var(--border-primary)] mb-6">
        <div className="flex gap-1">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 bg-[var(--bg-tertiary)] rounded w-24"></div>
          ))}
        </div>
      </div>

      {/* Content Skeleton */}
      <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6">
        <div className="h-6 bg-[var(--bg-tertiary)] rounded w-40 mb-4"></div>
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-[var(--bg-tertiary)] rounded"></div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================
// MAIN COMPONENT
// ============================================

export default function AccountDetail() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('overview');
  const apiCredentialsRef = useRef(null);
  const [shouldScrollToCredentials, setShouldScrollToCredentials] = useState(false);

  // Data state
  const [account, setAccount] = useState(null);
  const [holdings, setHoldings] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [brokerConfig, setBrokerConfig] = useState(null); // {has_api, supported_formats, name}
  const [coverage, setCoverage] = useState(null); // Real coverage data from API
  const [importHistory, setImportHistory] = useState([]); // Import sources from coverage API
  const [historicalData, setHistoricalData] = useState([]); // Account value history for chart
  const [accountCashFlows, setAccountCashFlows] = useState([]); // Cash flows for TWR calculation
  const [chartTimeRange, setChartTimeRange] = useState('3M'); // Chart time range: 1W, 1M, 3M, YTD, 1Y, ALL
  const [chartHoveredData, setChartHoveredData] = useState(null); // Hovered data point for chart
  const [chartMode, setChartMode] = useState('value'); // 'value' or 'performance'
  const [fullHistoryLoaded, setFullHistoryLoaded] = useState(false); // Track if full history is loaded
  const [loadingFullHistory, setLoadingFullHistory] = useState(false); // Loading state for full history
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Pagination state for transactions
  const [txCurrentPage, setTxCurrentPage] = useState(1);
  const [txPageSize, setTxPageSize] = useState(10);

  // Pagination state for holdings
  const [holdingsCurrentPage, setHoldingsCurrentPage] = useState(1);
  const [holdingsPageSize, setHoldingsPageSize] = useState(10);

  // File upload state
  const [isUploading, setIsUploading] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // API credentials modal state
  const [isApiModalOpen, setIsApiModalOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [hasApiCredentials, setHasApiCredentials] = useState(false);

  // Delete source state
  const [deleteDialogSource, setDeleteDialogSource] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Overlap warning state
  const [overlapWarning, setOverlapWarning] = useState(null);
  const [pendingUploadFile, setPendingUploadFile] = useState(null);

  // Handle tab query parameter and scrolling to API credentials
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    const scrollTo = searchParams.get('scrollTo');

    if (tabParam === 'settings') {
      setActiveTab('settings');
      // Clear the query params after reading
      setSearchParams({}, { replace: true });
      // Schedule scroll to API credentials
      if (scrollTo === 'api' || !scrollTo) {
        setShouldScrollToCredentials(true);
      }
    }
  }, [searchParams, setSearchParams]);

  // Scroll to API credentials when tab is switched and data is loaded
  useEffect(() => {
    if (shouldScrollToCredentials && activeTab === 'settings' && !loading) {
      // Small delay to ensure the settings section is rendered
      const timer = setTimeout(() => {
        apiCredentialsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setShouldScrollToCredentials(false);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [shouldScrollToCredentials, activeTab, loading]);

  // Handler for navigating to settings and scrolling to API credentials
  const handleGoToSettingsAndScroll = () => {
    setActiveTab('settings');
    setShouldScrollToCredentials(true);
  };

  // Check for API credentials when account loads
  useEffect(() => {
    const checkCredentials = async () => {
      if (!account?.id || !brokerConfig?.has_api) {
        setHasApiCredentials(false);
        return;
      }
      try {
        const res = await api(`/brokers/${account.broker_type}/credentials/${account.id}`);
        if (res.ok) {
          const data = await res.json();
          setHasApiCredentials(data?.has_credentials ?? false);
        } else {
          setHasApiCredentials(false);
        }
      } catch {
        setHasApiCredentials(false);
      }
    };
    checkCredentials();
  }, [account?.id, account?.broker_type, brokerConfig?.has_api]);

  // Handle file upload from modal - first analyze, then upload with optional overlap confirmation
  const handleFileUpload = async (file, confirmOverlap = false) => {
    if (!file) return;

    setIsUploading(true);
    try {
      // If not confirming overlap, first analyze the file
      if (!confirmOverlap) {
        const analyzeFormData = new FormData();
        analyzeFormData.append('file', file);
        analyzeFormData.append('broker_type', account.broker_type);

        const analyzeRes = await api(`/broker-data/upload/${id}/analyze`, {
          method: 'POST',
          body: analyzeFormData,
        });

        if (analyzeRes.ok) {
          const analysis = await analyzeRes.json();

          // If there's an overlap warning and it requires confirmation
          if (analysis.overlap_warning && analysis.requires_confirmation) {
            setOverlapWarning(analysis.overlap_warning);
            setPendingUploadFile(file);
            setIsUploading(false);
            return; // Wait for user to confirm
          }
        }
      }

      // Proceed with upload (with or without overlap confirmation)
      const formData = new FormData();
      formData.append('file', file);
      formData.append('broker_type', account.broker_type);
      if (confirmOverlap) {
        formData.append('confirm_overlap', 'true');
      }

      const res = await api(`/broker-data/upload/${id}`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const result = await res.json();
        alert(
          `Successfully imported ${result.stats?.total_records || 0} records from ${file.name}`
        );
        setIsUploadModalOpen(false);
        setOverlapWarning(null);
        setPendingUploadFile(null);
        window.location.reload();
      } else {
        const errorData = await res.json();
        // Handle both string and object error details
        const detail = errorData.detail;
        const errorMessage =
          typeof detail === 'string'
            ? detail
            : detail?.message || detail?.error || JSON.stringify(detail);
        alert(`Import failed: ${errorMessage}`);
      }
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle overlap confirmation
  const handleOverlapConfirm = async () => {
    if (!pendingUploadFile) return;
    await handleFileUpload(pendingUploadFile, true);
  };

  // Handle overlap cancellation
  const handleOverlapCancel = () => {
    setOverlapWarning(null);
    setPendingUploadFile(null);
  };

  // Handle delete data source
  const handleDeleteSource = async () => {
    if (!deleteDialogSource) return;

    setIsDeleting(true);
    try {
      await deleteDataSource(deleteDialogSource.id);
      // Close dialog and refresh page to reload all data
      setDeleteDialogSource(null);
      window.location.reload();
    } catch (err) {
      alert(`Failed to delete import: ${err.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  // Handle API sync (import data using stored credentials)
  const handleSync = async () => {
    if (!account) return;

    setIsSyncing(true);
    try {
      const res = await api(`/brokers/${account.broker_type}/import/${id}`, {
        method: 'POST',
      });

      if (res.ok) {
        const result = await res.json();
        alert(`Sync completed: ${result.stats?.transactions_imported || 0} transactions imported`);
        window.location.reload();
      } else {
        const error = await res.json();
        // If no credentials, prompt to connect API
        if (error.detail?.includes('credentials') || error.detail?.includes('No credentials')) {
          alert('No API credentials found. Please connect your API first.');
          setIsApiModalOpen(true);
        } else {
          alert(`Sync failed: ${error.detail || 'Unknown error'}`);
        }
      }
    } catch (err) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  // Fetch full history when user requests longer time ranges (1Y, ALL)
  useEffect(() => {
    const fetchFullHistory = async () => {
      if (fullHistoryLoaded || loadingFullHistory || !account) return;
      if (chartTimeRange !== '1Y' && chartTimeRange !== 'ALL') return;

      setLoadingFullHistory(true);
      try {
        const res = await api(`/snapshots/account/${id}?limit=2000&display_currency=${account.currency}`);
        if (res.ok) {
          const snapshotsData = await res.json();
          const chartData = snapshotsData
            .filter((s) => s.date && !isNaN(new Date(s.date).getTime()))
            .map((s) => ({
              date: s.date,
              value: s.value || s.total_value || 0,
              costBasis: s.cost_basis || 0,
            }))
            .sort((a, b) => new Date(a.date) - new Date(b.date));
          setHistoricalData(chartData);
          setFullHistoryLoaded(true);
        }
      } catch (err) {
        console.error('Error fetching full history:', err);
      } finally {
        setLoadingFullHistory(false);
      }
    };

    fetchFullHistory();
  }, [chartTimeRange, account, fullHistoryLoaded, loadingFullHistory, id]);

  // Fetch data on mount and when account ID changes
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      setTxCurrentPage(1); // Reset transactions pagination
      setHoldingsCurrentPage(1); // Reset holdings pagination
      setFullHistoryLoaded(false); // Reset full history flag for new account

      try {
        // First fetch account to get its currency
        const accountRes = await api(`/accounts/${id}`);
        if (!accountRes.ok) {
          if (accountRes.status === 404) {
            setAccount(null);
            setLoading(false);
            return;
          }
          throw new Error(`Failed to fetch account: ${accountRes.status}`);
        }
        const accountData = await accountRes.json();
        const accountCurrency = accountData.currency || 'USD';

        // Now fetch everything else with account's currency for display
        const [positionsRes, tradesRes, dividendsRes, forexRes, cashRes, coverageRes, brokerRes, snapshotsRes] = await Promise.all([
          api(`/positions?display_currency=${accountCurrency}`),
          api(`/transactions/trades?account_id=${id}&limit=500&display_currency=${accountCurrency}`),
          api(`/transactions/dividends?account_id=${id}&limit=500`),
          api(`/transactions/forex?account_id=${id}&limit=500`),
          api(`/transactions/cash?account_id=${id}&limit=500&display_currency=${accountCurrency}`),
          api(`/broker-data/coverage/${id}`),
          api(`/broker-data/supported-brokers`),
          api(`/snapshots/account/${id}?limit=100&display_currency=${accountCurrency}`),
        ]);

        const positionsData = await positionsRes.json();
        const tradesData = await tradesRes.json();
        const dividendsData = await dividendsRes.json();
        const forexData = await forexRes.json();
        const cashData = await cashRes.json();

        // Process coverage data
        let coverageData = null;
        let importSources = [];
        if (coverageRes.ok) {
          const coverageJson = await coverageRes.json();
          const brokerType = accountData.broker_type;
          const brokerCoverage = coverageJson.brokers?.[brokerType];
          if (brokerCoverage && brokerCoverage.has_data) {
            coverageData = {
              start_date: brokerCoverage.coverage?.start_date,
              end_date: brokerCoverage.coverage?.end_date,
              transactions: brokerCoverage.totals?.transactions || 0,
              sources: brokerCoverage.totals?.sources || 0,
              gaps: brokerCoverage.gaps || [],
            };
            importSources = brokerCoverage.sources || [];
          }
        }
        setCoverage(coverageData);
        setImportHistory(importSources);

        // Process broker config
        if (brokerRes.ok) {
          const brokerList = await brokerRes.json();
          const config = brokerList.find(b => b.type === accountData.broker_type);
          setBrokerConfig(config || null);
        }

        // Process historical snapshots for chart
        if (snapshotsRes.ok) {
          const snapshotsData = await snapshotsRes.json();
          // Transform to chart format, filter out invalid dates, sorted by date ascending
          // API returns 'date' field (not 'snapshot_date') and 'value' (not 'total_value')
          const chartData = snapshotsData
            .filter((s) => s.date && !isNaN(new Date(s.date).getTime()))
            .map((s) => ({
              date: s.date,
              value: s.value || s.total_value || 0,
              costBasis: s.cost_basis || 0,
            }))
            .sort((a, b) => new Date(a.date) - new Date(b.date));
          setHistoricalData(chartData);
        }

        // Extract holdings for this account from positions data
        const accountIdInt = parseInt(id);
        const accountHoldings = [];
        let totalValue = 0;
        let totalCostBasis = 0;

        positionsData.forEach((position) => {
          const accountInfo = position.accounts?.find((a) => a.account_id === accountIdInt);
          if (accountInfo) {
            // Use native currency values for per-holding display and account totals
            // This ensures Meitav (ILS account) shows values in ILS, not USD
            const valueNative = accountInfo.market_value_native ?? accountInfo.market_value ?? 0;
            const costBasisNative = accountInfo.cost_basis_native ?? accountInfo.cost_basis ?? 0;
            const isCash = position.asset_class === 'Cash';

            // For cash, cost basis = current value (1 ILS costs 1 ILS)
            // The backend returns all deposits as cost_basis for cash, which is incorrect
            const effectiveCostBasis = isCash ? valueNative : costBasisNative;
            const gainNative = valueNative - effectiveCostBasis;
            const gainPct = effectiveCostBasis > 0 ? (gainNative / effectiveCostBasis) * 100 : 0;

            accountHoldings.push({
              symbol: position.symbol,
              name: position.name,
              quantity: accountInfo.quantity,
              currency: position.currency || 'USD', // Native currency
              price: position.current_price || 0, // Native price
              value: valueNative, // Native currency value for display
              cost_basis: effectiveCostBasis, // Native currency cost basis
              gain: gainNative, // Native currency gain
              gain_pct: gainPct,
              asset_class: position.asset_class,
            });

            // Sum native values for account totals
            totalValue += valueNative;
            totalCostBasis += effectiveCostBasis;
          }
        });

        // Sort holdings by value descending
        accountHoldings.sort((a, b) => b.value - a.value);

        // Calculate account totals
        const totalReturn = totalValue - totalCostBasis;
        const totalReturnPct = totalCostBasis > 0 ? (totalReturn / totalCostBasis) * 100 : 0;

        // Extract cash flows for TWR calculation (positive = deposit, negative = withdrawal)
        const cashFlowsForTWR = cashData.map((tx) => ({
          date: tx.date,
          amount: tx.type === 'Deposit' ? parseFloat(tx.amount) : -parseFloat(tx.amount),
        }));
        setAccountCashFlows(cashFlowsForTWR);

        // Merge and sort transactions
        const allTransactions = [
          ...tradesData.map(transformTrade),
          ...dividendsData.map(transformDividend),
          ...forexData.map(transformForex),
          ...cashData.map(transformCash),
        ].sort((a, b) => new Date(b.date) - new Date(a.date));

        // Enrich account with calculated data
        const enrichedAccount = {
          ...accountData,
          value: totalValue,
          cost_basis: totalCostBasis,
          total_return: totalReturn,
          total_return_pct: totalReturnPct,
          day_change: 0, // Would need separate calculation
          day_change_pct: 0,
          last_sync: accountData.updated_at,
          holdings: accountHoldings,
          recent_transactions: allTransactions.slice(0, 10),
        };

        setAccount(enrichedAccount);
        setHoldings(accountHoldings);
        setTransactions(allTransactions);
      } catch (err) {
        console.error('Error fetching account data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]); // Note: Using account's currency, not global currency context

  // Loading state
  if (loading) {
    return (
      <PageContainer>
        <LoadingSkeleton />
      </PageContainer>
    );
  }

  // Error state
  if (error) {
    return (
      <PageContainer>
        <div className="text-center py-16">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Error loading account</h2>
          <p className="text-[var(--text-secondary)] mt-2">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  // Not found state
  if (!account) {
    return (
      <PageContainer>
        <div className="text-center py-16">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Account not found</h2>
          <p className="text-[var(--text-secondary)] mt-2">The account you're looking for doesn't exist.</p>
          <Link
            to="/accounts"
            className="inline-flex items-center gap-2 mt-4 text-accent hover:underline"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Back to Accounts
          </Link>
        </div>
      </PageContainer>
    );
  }

  const statusInfo = getStatusInfo(account.last_sync);
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'holdings', label: 'Holdings' },
    { id: 'transactions', label: 'Transactions' },
    { id: 'imports', label: 'Import History' },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <PageContainer>
      {/* Back Link */}
      <Link
        to="/accounts"
        className="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors mb-6"
      >
        <ArrowLeftIcon className="w-4 h-4" />
        Back to Accounts
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="p-4 rounded-xl bg-accent/10">
            <BuildingLibraryIcon className="w-8 h-8 text-accent" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">{account.name}</h1>
            <p className="text-[var(--text-secondary)]">
              {account.institution} · {account.account_type}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn('w-2 h-2 rounded-full', statusInfo.bg)} />
              <span className={cn('text-sm', statusInfo.color)}>{statusInfo.label}</span>
            </div>
          </div>
        </div>

        {/* Import Buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsUploadModalOpen(true)}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium',
              'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
              'text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer'
            )}
          >
            <DocumentArrowUpIcon className="w-4 h-4" />
            Upload File
          </button>
          {brokerConfig?.has_api && (
            <button
              onClick={() => setIsApiModalOpen(true)}
              className={cn(
                'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer',
                hasApiCredentials
                  ? 'bg-emerald-100 dark:bg-emerald-900/30 border border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-900/50'
                  : 'bg-accent text-white hover:bg-accent/90'
              )}
            >
              {hasApiCredentials ? (
                <CheckIcon className="w-4 h-4" />
              ) : (
                <LinkIcon className="w-4 h-4" />
              )}
              {hasApiCredentials ? 'API Connected' : 'Connect API'}
            </button>
          )}
        </div>
      </div>

      {/* Stats Grid - values shown in account's currency */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Total Value"
          value={formatCurrency(account.value, account.currency)}
          trend={`${account.day_change_pct >= 0 ? '+' : ''}${account.day_change_pct.toFixed(2)}%`}
          trendDirection={account.day_change >= 0 ? 'up' : 'down'}
          subValue="today"
        />
        <StatCard
          label="Total Return"
          value={`${account.total_return >= 0 ? '+' : ''}${formatCurrency(account.total_return, account.currency)}`}
          trend={`${account.total_return_pct >= 0 ? '+' : ''}${account.total_return_pct.toFixed(2)}%`}
          trendDirection={account.total_return >= 0 ? 'up' : 'down'}
        />
        <StatCard
          label="Cost Basis"
          value={formatCurrency(account.cost_basis, account.currency)}
        />
        <StatCard
          label="Day Change"
          value={`${account.day_change >= 0 ? '+' : ''}${formatCurrency(account.day_change, account.currency)}`}
          trend={`${account.day_change_pct >= 0 ? '+' : ''}${account.day_change_pct.toFixed(2)}%`}
          trendDirection={account.day_change >= 0 ? 'up' : 'down'}
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-[var(--border-primary)] mb-6">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-3 text-sm font-medium transition-colors cursor-pointer border-b-2 -mb-px',
                activeTab === tab.id
                  ? 'border-accent text-accent'
                  : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'overview' && (() => {
          const isPerformanceMode = chartMode === 'performance';

          // Filter chart data based on selected time range (using slice like Overview page)
          let daysToShow;
          switch (chartTimeRange) {
            case '1W': daysToShow = 7; break;
            case '1M': daysToShow = 30; break;
            case '3M': daysToShow = 90; break;
            case 'YTD':
              // Calculate days from start of year
              const now = new Date();
              const startOfYear = new Date(now.getFullYear(), 0, 1);
              daysToShow = Math.ceil((now - startOfYear) / (1000 * 60 * 60 * 24));
              break;
            case '1Y': daysToShow = 365; break;
            case 'ALL': daysToShow = Infinity; break;
            default: daysToShow = 90;
          }
          const filteredChartData = daysToShow === Infinity
            ? historicalData
            : historicalData.slice(-daysToShow);

          // Calculate performance data using TWR (excludes deposits/withdrawals)
          const performanceData = filteredChartData.length > 0
            ? calculateTWR(filteredChartData, accountCashFlows)
            : [];

          // Calculate Y-axis domain with padding based on filtered data
          const chartValues = isPerformanceMode
            ? performanceData.map((d) => d.performance)
            : filteredChartData.map((d) => d.value);
          const chartMinValue = chartValues.length > 0 ? Math.min(...chartValues) : 0;
          const chartMaxValue = chartValues.length > 0 ? Math.max(...chartValues) : 0;
          const chartPadding = (chartMaxValue - chartMinValue) * 0.1 || Math.abs(chartMaxValue) * 0.05 || 1;
          const chartYMin = isPerformanceMode ? chartMinValue - chartPadding : Math.max(0, chartMinValue - chartPadding);
          const chartYMax = chartMaxValue + chartPadding;

          // Get display value - hovered or latest
          const baseChartValue = filteredChartData.length > 0 ? filteredChartData[0].value : 0;
          const latestChartData = filteredChartData.length > 0 ? filteredChartData[filteredChartData.length - 1] : null;
          const latestPerformance = performanceData.length > 0 ? performanceData[performanceData.length - 1].performance : 0;
          const displayChartValue = chartHoveredData?.value ?? latestChartData?.value ?? 0;
          const displayPerformance = chartHoveredData?.performance ?? latestPerformance;
          const displayChartDate = chartHoveredData?.date ?? latestChartData?.date ?? null;

          // Calculate simple value change (includes deposits/withdrawals) for display
          const valueChange = displayChartValue - baseChartValue;
          const valueChangePct = baseChartValue > 0 ? ((displayChartValue - baseChartValue) / baseChartValue) * 100 : 0;

          // Create performance data with separate positive/negative keys for coloring
          const performanceChartData = (() => {
            if (!performanceData || performanceData.length < 2) return [];

            const result = [];

            for (let i = 0; i < performanceData.length; i++) {
              const point = performanceData[i];
              const prevPoint = i > 0 ? performanceData[i - 1] : null;

              // Check for zero crossing and insert interpolated point
              if (prevPoint) {
                const crossingFromNegative = prevPoint.performance < 0 && point.performance >= 0;
                const crossingFromPositive = prevPoint.performance >= 0 && point.performance < 0;

                if (crossingFromNegative || crossingFromPositive) {
                  // Interpolate the zero-crossing point
                  const ratio = Math.abs(prevPoint.performance) / (Math.abs(prevPoint.performance) + Math.abs(point.performance));
                  const date1 = new Date(prevPoint.date).getTime();
                  const date2 = new Date(point.date).getTime();
                  const crossDate = new Date(date1 + ratio * (date2 - date1)).toISOString().split('T')[0];
                  result.push({
                    date: crossDate,
                    performance: 0,
                    positive: 0,
                    negative: 0,
                  });
                }
              }

              // Add point with appropriate positive/negative values
              result.push({
                ...point,
                positive: point.performance >= 0 ? point.performance : null,
                negative: point.performance < 0 ? point.performance : null,
              });
            }

            return result;
          })();

          // Chart mouse handlers
          const handleChartMouseMove = (state) => {
            if (state && state.activePayload && state.activePayload.length > 0) {
              setChartHoveredData(state.activePayload[0].payload);
            }
          };
          const handleChartMouseLeave = () => {
            setChartHoveredData(null);
          };

          return (
          <div className="space-y-8">
            {/* Historical Value Chart */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
              <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
                <div className="flex items-center gap-3">
                  {/* Value/Performance Toggle */}
                  <div className="flex bg-[var(--bg-tertiary)] rounded-md p-0.5">
                    <button
                      onClick={() => setChartMode('value')}
                      className={cn(
                        'px-3 py-1 text-sm rounded transition-colors cursor-pointer',
                        !isPerformanceMode
                          ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                      )}
                    >
                      Value
                    </button>
                    <button
                      onClick={() => setChartMode('performance')}
                      className={cn(
                        'px-3 py-1 text-sm rounded transition-colors cursor-pointer',
                        isPerformanceMode
                          ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                      )}
                    >
                      Performance
                    </button>
                  </div>
                </div>
                {/* Time Range */}
                <div className="flex gap-1">
                  {['1W', '1M', '3M', 'YTD', '1Y', 'ALL'].map((range) => (
                    <button
                      key={range}
                      onClick={() => setChartTimeRange(range)}
                      className={cn(
                        'px-2.5 py-1 text-xs rounded-md transition-colors cursor-pointer',
                        chartTimeRange === range
                          ? 'bg-accent text-white'
                          : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                      )}
                    >
                      {range}
                    </button>
                  ))}
                </div>
              </div>

              {filteredChartData.length > 0 ? (
                <>
                  {/* Value display at top - updates on hover */}
                  <div className="mb-4">
                    <div className="flex items-baseline gap-3">
                      {isPerformanceMode ? (
                        <span className={cn(
                          'text-3xl font-bold tabular-nums font-mono',
                          displayPerformance >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                        )}>
                          {displayPerformance >= 0 ? '+' : ''}{displayPerformance.toFixed(2)}%
                        </span>
                      ) : (
                        <div className="flex flex-col">
                          <span className="text-3xl font-bold text-[var(--text-primary)] tabular-nums font-mono">
                            {formatCurrency(displayChartValue, account.currency)}
                          </span>
                          <span className={cn(
                            'text-sm font-medium tabular-nums',
                            valueChange >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                          )}>
                            {valueChange >= 0 ? '+' : ''}{formatCurrency(valueChange, account.currency, { compact: true })} ({valueChangePct >= 0 ? '+' : ''}{valueChangePct.toFixed(2)}%)
                          </span>
                        </div>
                      )}
                      {displayChartDate && (
                        <span className="text-sm text-[var(--text-tertiary)]">
                          {new Date(displayChartDate).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          })}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      {isPerformanceMode ? (
                        /* Performance Chart with green/red coloring */
                        <LineChart
                          data={performanceChartData}
                          onMouseMove={handleChartMouseMove}
                          onMouseLeave={handleChartMouseLeave}
                        >
                          <XAxis
                            dataKey="date"
                            tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                            axisLine={{ stroke: 'var(--border-primary)' }}
                            tickLine={false}
                            minTickGap={40}
                          />
                          <YAxis
                            tickFormatter={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`}
                            tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            width={70}
                            domain={[chartYMin, chartYMax]}
                          />
                          <Tooltip content={() => null} cursor={{ stroke: 'var(--border-secondary)', strokeWidth: 1 }} />
                          <ReferenceLine y={0} stroke="var(--border-secondary)" strokeDasharray="3 3" />
                          {/* Positive performance (green) */}
                          <Line
                            type="monotone"
                            dataKey="positive"
                            name="Positive"
                            stroke="#10B981"
                            strokeWidth={2}
                            dot={false}
                            connectNulls={false}
                            activeDot={{ r: 4, stroke: '#10B981', strokeWidth: 2, fill: 'white' }}
                            isAnimationActive={false}
                          />
                          {/* Negative performance (red) */}
                          <Line
                            type="monotone"
                            dataKey="negative"
                            name="Negative"
                            stroke="#EF4444"
                            strokeWidth={2}
                            dot={false}
                            connectNulls={false}
                            activeDot={{ r: 4, stroke: '#EF4444', strokeWidth: 2, fill: 'white' }}
                            isAnimationActive={false}
                          />
                        </LineChart>
                      ) : (
                        /* Value Chart */
                        <AreaChart
                          data={filteredChartData}
                          onMouseMove={handleChartMouseMove}
                          onMouseLeave={handleChartMouseLeave}
                        >
                          <defs>
                            <linearGradient id="accountValueGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#2563EB" stopOpacity={0.3} />
                              <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <XAxis
                            dataKey="date"
                            tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                            axisLine={{ stroke: 'var(--border-primary)' }}
                            tickLine={false}
                            minTickGap={40}
                          />
                          <YAxis
                            tickFormatter={(v) => formatCurrency(v, account.currency, { compact: true })}
                            tick={{ fill: 'var(--text-tertiary)', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                            width={70}
                            domain={[chartYMin, chartYMax]}
                          />
                          <Tooltip content={() => null} cursor={{ stroke: 'var(--border-secondary)', strokeWidth: 1 }} />
                          <Area
                            type="monotone"
                            dataKey="value"
                            stroke="#2563EB"
                            strokeWidth={2}
                            fill="url(#accountValueGradient)"
                            activeDot={{ r: 4, stroke: '#2563EB', strokeWidth: 2, fill: 'white' }}
                          />
                        </AreaChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                </>
              ) : loadingFullHistory ? (
                <div className="h-56 flex items-center justify-center">
                  <p className="text-[var(--text-tertiary)]">Loading historical data...</p>
                </div>
              ) : (
                <div className="h-56 flex items-center justify-center">
                  <p className="text-[var(--text-tertiary)]">No historical data available for this period</p>
                </div>
              )}
            </div>

            {/* Data Coverage */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
              <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Data Coverage</h3>
              <DataCoverageBar coverage={coverage} />
            </div>

            {/* Holdings Preview */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">Top Holdings</h3>
                {holdings.length > 0 && (
                  <button
                    onClick={() => setActiveTab('holdings')}
                    className="text-sm text-accent hover:underline cursor-pointer"
                  >
                    View all ({holdings.length}) →
                  </button>
                )}
              </div>
              {holdings.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-[var(--text-secondary)]">No holdings found for this account.</p>
                </div>
              ) : (
                <HoldingsTable holdings={holdings.slice(0, 5)} />
              )}
            </div>

            {/* Recent Transactions Preview */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">Recent Transactions</h3>
                {transactions.length > 0 && (
                  <button
                    onClick={() => setActiveTab('transactions')}
                    className="text-sm text-accent hover:underline cursor-pointer"
                  >
                    View all ({transactions.length}) →
                  </button>
                )}
              </div>
              {transactions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-[var(--text-secondary)]">No transactions found for this account.</p>
                </div>
              ) : (
                <div className="divide-y divide-[var(--border-primary)]">
                  {transactions.slice(0, 5).map((tx) => (
                    <TransactionCard key={tx.id} tx={tx} variant="compact" currency={account?.currency} />
                  ))}
                </div>
              )}
            </div>
          </div>
          );
        })()}

        {activeTab === 'holdings' && (
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
            {/* Header with title and page size selector */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                Holdings ({holdings.length})
              </h3>
              {holdings.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-[var(--text-secondary)]">Show:</span>
                  <select
                    value={holdingsPageSize}
                    onChange={(e) => {
                      setHoldingsPageSize(Number(e.target.value));
                      setHoldingsCurrentPage(1);
                    }}
                    className={cn(
                      'px-2 py-1 rounded text-sm',
                      'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                      'text-[var(--text-primary)] cursor-pointer',
                      'focus:outline-none focus:ring-2 focus:ring-accent/50'
                    )}
                  >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              )}
            </div>

            {holdings.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-[var(--text-secondary)]">No holdings found for this account.</p>
              </div>
            ) : (
              <>
                <HoldingsTable
                  holdings={holdings.slice(
                    (holdingsCurrentPage - 1) * holdingsPageSize,
                    holdingsCurrentPage * holdingsPageSize
                  )}
                />

                {/* Pagination controls */}
                {holdings.length > holdingsPageSize && (() => {
                  const totalPages = Math.ceil(holdings.length / holdingsPageSize);
                  return (
                    <div className="mt-4 pt-4 border-t border-[var(--border-primary)] flex items-center justify-between">
                      <p className="text-sm text-[var(--text-tertiary)]">
                        Showing {(holdingsCurrentPage - 1) * holdingsPageSize + 1}-{Math.min(holdingsCurrentPage * holdingsPageSize, holdings.length)} of {holdings.length}
                      </p>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { setHoldingsCurrentPage(1); scrollToTop(); }}
                          disabled={holdingsCurrentPage === 1}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            holdingsCurrentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="First page"
                        >
                          <ChevronDoubleLeftIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => { setHoldingsCurrentPage((p) => Math.max(1, p - 1)); scrollToTop(); }}
                          disabled={holdingsCurrentPage === 1}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            holdingsCurrentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="Previous page"
                        >
                          <ChevronLeftIcon className="w-4 h-4" />
                        </button>
                        <span className="text-sm text-[var(--text-secondary)] px-2">
                          {holdingsCurrentPage} / {totalPages}
                        </span>
                        <button
                          onClick={() => { setHoldingsCurrentPage((p) => Math.min(totalPages, p + 1)); scrollToTop(); }}
                          disabled={holdingsCurrentPage >= totalPages}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            holdingsCurrentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="Next page"
                        >
                          <ChevronRightIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => { setHoldingsCurrentPage(totalPages); scrollToTop(); }}
                          disabled={holdingsCurrentPage >= totalPages}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            holdingsCurrentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="Last page"
                        >
                          <ChevronDoubleRightIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  );
                })()}
              </>
            )}
          </div>
        )}

        {activeTab === 'transactions' && (
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
            {/* Header with title and page size selector */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                Transactions ({transactions.length})
              </h3>
              {transactions.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-[var(--text-secondary)]">Show:</span>
                  <select
                    value={txPageSize}
                    onChange={(e) => {
                      setTxPageSize(Number(e.target.value));
                      setTxCurrentPage(1);
                    }}
                    className={cn(
                      'px-2 py-1 rounded text-sm',
                      'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                      'text-[var(--text-primary)] cursor-pointer',
                      'focus:outline-none focus:ring-2 focus:ring-accent/50'
                    )}
                  >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              )}
            </div>

            {transactions.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-[var(--text-secondary)]">No transactions found for this account.</p>
              </div>
            ) : (
              <>
                <div className="divide-y divide-[var(--border-primary)]">
                  {transactions
                    .slice((txCurrentPage - 1) * txPageSize, txCurrentPage * txPageSize)
                    .map((tx) => (
                      <TransactionCard key={tx.id} tx={tx} variant="compact" currency={account?.currency} />
                    ))}
                </div>

                {/* Pagination controls */}
                {transactions.length > txPageSize && (() => {
                  const totalPages = Math.ceil(transactions.length / txPageSize);
                  return (
                    <div className="mt-4 pt-4 border-t border-[var(--border-primary)] flex items-center justify-between">
                      <p className="text-sm text-[var(--text-tertiary)]">
                        Showing {(txCurrentPage - 1) * txPageSize + 1}-{Math.min(txCurrentPage * txPageSize, transactions.length)} of {transactions.length}
                      </p>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { setTxCurrentPage(1); scrollToTop(); }}
                          disabled={txCurrentPage === 1}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            txCurrentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="First page"
                        >
                          <ChevronDoubleLeftIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => { setTxCurrentPage((p) => Math.max(1, p - 1)); scrollToTop(); }}
                          disabled={txCurrentPage === 1}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            txCurrentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="Previous page"
                        >
                          <ChevronLeftIcon className="w-4 h-4" />
                        </button>
                        <span className="text-sm text-[var(--text-secondary)] px-2">
                          {txCurrentPage} / {totalPages}
                        </span>
                        <button
                          onClick={() => { setTxCurrentPage((p) => Math.min(totalPages, p + 1)); scrollToTop(); }}
                          disabled={txCurrentPage >= totalPages}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            txCurrentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="Next page"
                        >
                          <ChevronRightIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => { setTxCurrentPage(totalPages); scrollToTop(); }}
                          disabled={txCurrentPage >= totalPages}
                          className={cn(
                            'p-1.5 rounded',
                            'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                            'hover:bg-[var(--border-primary)] transition-colors',
                            txCurrentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          )}
                          title="Last page"
                        >
                          <ChevronDoubleRightIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  );
                })()}
              </>
            )}
            <div className="mt-4 pt-4 border-t border-[var(--border-primary)]">
              <Link
                to="/activity"
                className="text-sm text-accent hover:underline"
              >
                View all transactions in Activity →
              </Link>
            </div>
          </div>
        )}

        {activeTab === 'imports' && (
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">Import History</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsUploadModalOpen(true)}
                  className={cn(
                    'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
                    'bg-[var(--bg-tertiary)] text-[var(--text-primary)]',
                    'hover:bg-[var(--border-primary)] transition-colors cursor-pointer'
                  )}
                >
                  <DocumentArrowUpIcon className="w-4 h-4" />
                  Upload
                </button>
                {brokerConfig?.has_api && (
                  <button
                    onClick={handleSync}
                    disabled={isSyncing}
                    className={cn(
                      'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm',
                      'bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer',
                      'disabled:opacity-50'
                    )}
                  >
                    <CloudArrowDownIcon className="w-4 h-4" />
                    {isSyncing ? 'Syncing...' : 'Sync Now'}
                  </button>
                )}
              </div>
            </div>
            {importHistory.length > 0 ? (
              <div className="divide-y divide-[var(--border-primary)]">
                {importHistory.map((source, index) => (
                  <ImportSourceItem
                    key={source.id || index}
                    source={source}
                    onDelete={setDeleteDialogSource}
                    isDeleting={isDeleting && deleteDialogSource?.id === source.id}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-[var(--text-secondary)]">No import history available.</p>
                <p className="text-sm text-[var(--text-tertiary)] mt-2">
                  Upload a file{brokerConfig?.has_api ? ' or connect an API' : ''} to start importing transactions.
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-6">Account Settings</h3>
            <SettingsSection
              account={account}
              brokerConfig={brokerConfig}
              onOpenApiModal={() => setIsApiModalOpen(true)}
              apiCredentialsRef={apiCredentialsRef}
            />
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUpload={handleFileUpload}
        isUploading={isUploading}
        supportedFormats={brokerConfig?.supported_formats}
        institution={account.institution}
      />

      {/* API Credentials Modal */}
      <ApiCredentialsModal
        isOpen={isApiModalOpen}
        onClose={() => setIsApiModalOpen(false)}
        account={account}
        hasCredentials={hasApiCredentials}
        onGoToSettings={handleGoToSettingsAndScroll}
        onCredentialsSaved={() => {
          setHasApiCredentials(true);
          window.location.reload();
        }}
      />

      {/* Overlap Warning Dialog */}
      <AlertDialog
        isOpen={!!overlapWarning}
        onClose={handleOverlapCancel}
        onConfirm={handleOverlapConfirm}
        title="Overlapping Date Range Detected"
        description={formatOverlapWarningDescription(overlapWarning)}
        confirmLabel="Continue Import"
        loadingLabel="Importing..."
        variant="warning"
        isLoading={isUploading}
      />

      {/* Delete Import Confirmation Dialog */}
      <AlertDialog
        isOpen={!!deleteDialogSource}
        onClose={() => setDeleteDialogSource(null)}
        onConfirm={handleDeleteSource}
        title="Delete Import Source"
        description={deleteDialogSource ? `Are you sure you want to delete this import?\n\n${deleteDialogSource.source_identifier || 'Unknown file'}\n\nThis will permanently delete ${(deleteDialogSource.transaction_count || 0).toLocaleString()} transaction${deleteDialogSource.transaction_count !== 1 ? 's' : ''} and all related data imported from this file. This action cannot be undone.` : ''}
        confirmLabel="Delete Import"
        loadingLabel="Deleting..."
        variant="danger"
        isLoading={isDeleting}
      />
    </PageContainer>
  );
}
