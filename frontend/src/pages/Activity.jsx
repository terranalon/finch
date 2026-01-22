/**
 * Activity Page - Finch Redesign
 *
 * Purpose: Complete transaction history as card-based timeline
 *
 * Wired to real API endpoints:
 * - GET /api/transactions/trades
 * - GET /api/transactions/dividends
 * - GET /api/transactions/forex
 * - GET /api/transactions/cash
 * - GET /api/accounts?is_active=true
 */

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { cn, formatCurrency, formatNumber, api } from '../lib';
import { useCurrency, usePortfolio } from '../contexts';
import { PageContainer } from '../components/layout';
import { MultiSelectFilter, Skeleton } from '../components/ui';

const TRANSACTION_TYPES = ['Trade', 'Dividend', 'Forex', 'Cash'];

// ============================================
// ICONS
// ============================================

function SearchIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
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

function ChevronDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
    </svg>
  );
}

function ArrowUpIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
    </svg>
  );
}

function ArrowDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5 12 21m0 0-7.5-7.5M12 21V3" />
    </svg>
  );
}

function PlusCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function MinusCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12H9m12 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}

function ReceiptPercentIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m9 14.25 6-6m4.5-3.493V21.75l-3.75-1.5-3.75 1.5-3.75-1.5-3.75 1.5V4.757c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0 1 11.186 0c1.1.128 1.907 1.077 1.907 2.185ZM9.75 9h.008v.008H9.75V9Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm4.125 4.5h.008v.008h-.008V13.5Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
    </svg>
  );
}

function BanknotesIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
    </svg>
  );
}

function ArrowsRightLeftIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  );
}

function CalendarIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
    </svg>
  );
}

// ============================================
// DATE RANGE PRESETS
// ============================================

const DATE_RANGES = [
  { id: 'all', label: 'All Time', days: null },
  { id: '7d', label: 'Last 7 Days', days: 7 },
  { id: '30d', label: 'Last 30 Days', days: 30 },
  { id: '90d', label: 'Last 90 Days', days: 90 },
  { id: 'ytd', label: 'Year to Date', days: 'ytd' },
];

// ============================================
// UTILITY FUNCTIONS
// ============================================

const getCurrencySymbol = (code) => {
  const symbols = { USD: '$', EUR: '€', GBP: '£', ILS: '₪', JPY: '¥', CHF: 'CHF ' };
  return symbols[code] || code + ' ';
};

// Format rate: trim trailing zeros but keep up to 4 decimal places
const formatRate = (rate) => {
  const formatted = rate.toFixed(4);
  return parseFloat(formatted).toString();
};

// Format date for display
const formatDateHeader = (dateStr) => {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
};

const formatShortDate = (dateStr) => {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

// ============================================
// TRANSACTION CARD COMPONENTS
// ============================================

/**
 * Trade Card - Buy/Sell transactions
 * Green for Buy (acquiring assets), Red for Sell (disposing assets)
 */
function TradeCard({ tx, onClick }) {
  const isBuy = tx.side === 'BUY';

  return (
    <div
      onClick={onClick}
      className="flex items-start justify-between p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer shadow-sm dark:shadow-none"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={cn(
          'p-2 rounded-lg',
          isBuy
            ? 'bg-emerald-50 dark:bg-emerald-950/40'
            : 'bg-red-50 dark:bg-red-950/40'
        )}>
          {isBuy ? (
            <ArrowDownIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <ArrowUpIcon className="w-4 h-4 text-red-600 dark:text-red-400" />
          )}
        </div>

        {/* Details */}
        <div>
          <div className="flex items-center gap-2">
            <span className={cn(
              'text-xs font-semibold px-2 py-0.5 rounded',
              isBuy
                ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400'
                : 'bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400'
            )}>
              {tx.side}
            </span>
            <span className="font-semibold text-[var(--text-primary)]">{tx.symbol}</span>
          </div>
          {/* Quantity × price display */}
          <p className="text-sm text-[var(--text-secondary)] mt-1 font-mono tabular-nums">
            {tx.quantity} × {formatCurrency(tx.price, tx.currency)}
          </p>
          {tx.fee > 0 && (
            <p className="text-xs text-[var(--text-tertiary)] mt-1">
              Fee: {formatCurrency(tx.fee, tx.currency)}
            </p>
          )}
          <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{tx.account_name}</p>
        </div>
      </div>

      {/* Amount */}
      <div className="text-right">
        <p className={cn(
          'font-mono tabular-nums font-semibold',
          isBuy
            ? 'text-emerald-600 dark:text-emerald-400'
            : 'text-red-600 dark:text-red-400'
        )}>
          {isBuy ? '-' : '+'}{formatCurrency(Math.abs(tx.total), tx.currency)}
        </p>
      </div>
    </div>
  );
}

/**
 * Dividend Card - Dividend payments
 * Uses teal color to distinguish from trades
 */
function DividendCard({ tx, currency, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex items-start justify-between p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer shadow-sm dark:shadow-none"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="p-2 rounded-lg bg-teal-50 dark:bg-teal-950/40">
          <BanknotesIcon className="w-4 h-4 text-teal-600 dark:text-teal-400" />
        </div>

        {/* Details */}
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-teal-50 dark:bg-teal-950/40 text-teal-600 dark:text-teal-400">
              DIVIDEND
            </span>
            <span className="font-semibold text-[var(--text-primary)]">{tx.symbol}</span>
          </div>
          <p className="text-sm text-[var(--text-secondary)] mt-1">{tx.description}</p>
          <p className="text-xs text-[var(--text-tertiary)] mt-1">{tx.account_name}</p>
        </div>
      </div>

      {/* Amount */}
      <div className="text-right">
        <p className="font-mono tabular-nums font-semibold text-teal-600 dark:text-teal-400">
          +{formatCurrency(Math.abs(tx.amount), currency)}
        </p>
      </div>
    </div>
  );
}

/**
 * Forex Card - Currency exchange transactions
 * Purple color, destination amount prominent
 */
function ForexCard({ tx, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex items-start justify-between p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer shadow-sm dark:shadow-none"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="p-2 rounded-lg bg-violet-50 dark:bg-violet-950/40">
          <ArrowsRightLeftIcon className="w-4 h-4 text-violet-600 dark:text-violet-400" />
        </div>

        {/* Details */}
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-violet-50 dark:bg-violet-950/40 text-violet-600 dark:text-violet-400">
              FX
            </span>
            <span className="font-semibold text-[var(--text-primary)]">
              {tx.from_currency} → {tx.to_currency}
            </span>
          </div>
          <p className="text-xs text-[var(--text-tertiary)] mt-1">
            Rate: {formatRate(tx.exchange_rate)}
            {tx.fee > 0 && (
              <span> · Fee: {getCurrencySymbol(tx.from_currency)}{tx.fee}</span>
            )}
          </p>
          <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{tx.account_name}</p>
        </div>
      </div>

      {/* Conversion - Destination amount prominent */}
      <div className="text-right">
        <p className="font-mono tabular-nums font-semibold text-violet-600 dark:text-violet-400">
          {getCurrencySymbol(tx.to_currency)}{tx.to_amount.toLocaleString()}
        </p>
        <p className="text-xs text-[var(--text-tertiary)] font-mono mt-0.5">
          from {getCurrencySymbol(tx.from_currency)}{tx.from_amount.toLocaleString()}
        </p>
      </div>
    </div>
  );
}

/**
 * Cash Card - Deposits and withdrawals
 * Blue for deposits, Amber for withdrawals
 */
function CashCard({ tx, currency, onClick }) {
  const isDeposit = tx.activity_type === 'DEPOSIT';
  const isFee = tx.activity_type === 'FEE';
  const isInterest = tx.activity_type === 'INTEREST';

  // Get style configuration based on transaction type
  const getStyleConfig = () => {
    if (isDeposit) {
      return {
        bgColor: 'bg-blue-50 dark:bg-blue-950/40',
        textColor: 'text-blue-600 dark:text-blue-400',
        icon: <PlusCircleIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />,
        sign: '+',
      };
    } else if (isInterest) {
      return {
        bgColor: 'bg-green-50 dark:bg-green-950/40',
        textColor: 'text-green-600 dark:text-green-400',
        icon: <BanknotesIcon className="w-4 h-4 text-green-600 dark:text-green-400" />,
        sign: '+',
      };
    } else if (isFee) {
      return {
        bgColor: 'bg-red-50 dark:bg-red-950/40',
        textColor: 'text-red-600 dark:text-red-400',
        icon: <ReceiptPercentIcon className="w-4 h-4 text-red-600 dark:text-red-400" />,
        sign: '-',
      };
    } else {
      return {
        bgColor: 'bg-amber-50 dark:bg-amber-950/40',
        textColor: 'text-amber-600 dark:text-amber-400',
        icon: <MinusCircleIcon className="w-4 h-4 text-amber-600 dark:text-amber-400" />,
        sign: '-',
      };
    }
  };

  const style = getStyleConfig();
  const displayType = tx.cash_type || tx.activity_type;

  return (
    <div
      onClick={onClick}
      className="flex items-start justify-between p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer shadow-sm dark:shadow-none"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={cn('p-2 rounded-lg', style.bgColor)}>
          {style.icon}
        </div>

        {/* Details */}
        <div>
          <div className="flex items-center gap-2">
            <span className={cn('text-xs font-semibold px-2 py-0.5 rounded', style.bgColor, style.textColor)}>
              {displayType}
            </span>
          </div>
          <p className="text-sm text-[var(--text-secondary)] mt-1">{tx.description}</p>
          <p className="text-xs text-[var(--text-tertiary)] mt-1">{tx.account_name}</p>
        </div>
      </div>

      {/* Amount */}
      <div className="text-right">
        <p className={cn('font-mono tabular-nums font-semibold', style.textColor)}>
          {style.sign}{formatCurrency(Math.abs(tx.amount), currency)}
        </p>
      </div>
    </div>
  );
}

/**
 * Renders the appropriate card type based on transaction type
 */
function TransactionCard({ tx, currency, onClick }) {
  switch (tx.type) {
    case 'trade':
      return <TradeCard tx={tx} onClick={onClick} />;
    case 'dividend':
      return <DividendCard tx={tx} currency={currency} onClick={onClick} />;
    case 'forex':
      return <ForexCard tx={tx} onClick={onClick} />;
    case 'cash':
      return <CashCard tx={tx} currency={currency} onClick={onClick} />;
    default:
      return null;
  }
}

// ============================================
// SLIDE-OUT DETAIL PANEL
// ============================================

function TransactionDetailPanel({ transaction: tx, currency, onClose }) {
  if (!tx) return null;

  const renderTradeDetails = () => {
    const isBuy = tx.side === 'BUY';
    // Backend already includes fees in tx.total, so use it directly
    const total = tx.total;
    // Compute true subtotal (qty * price) by subtracting the fee from total
    const subtotal = total - (tx.fee || 0);

    return (
      <>
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className={cn(
            'p-3 rounded-xl',
            isBuy ? 'bg-emerald-50 dark:bg-emerald-950/40' : 'bg-red-50 dark:bg-red-950/40'
          )}>
            {isBuy ? (
              <ArrowDownIcon className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <ArrowUpIcon className="w-6 h-6 text-red-600 dark:text-red-400" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{tx.symbol}</h2>
            <p className="text-sm text-[var(--text-secondary)]">{tx.name}</p>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-sm text-[var(--text-secondary)]">Total {isBuy ? 'Cost' : 'Proceeds'}</span>
            <span className={cn(
              'text-2xl font-semibold font-mono tabular-nums',
              isBuy ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
            )}>
              {isBuy ? '-' : '+'}{formatCurrency(Math.abs(total), tx.currency)}
            </span>
          </div>
        </div>

        {/* Details Grid */}
        <div className="space-y-4">
          <DetailRow label="Transaction Type" value={isBuy ? 'Buy' : 'Sell'} />
          <DetailRow label="Quantity" value={`${tx.quantity} shares`} />
          <DetailRow label="Price per Share" value={formatCurrency(tx.price, tx.currency)} />
          <DetailRow label="Subtotal" value={formatCurrency(subtotal, tx.currency)} />
          {tx.fee > 0 && (
            <DetailRow label="Commission/Fee" value={formatCurrency(tx.fee, tx.currency)} />
          )}
          <div className="h-px bg-[var(--border-primary)] my-2" />
          <DetailRow label="Date" value={formatShortDate(tx.date)} />
          <DetailRow label="Account" value={tx.account_name} />
          {tx.notes && (
            <>
              <div className="h-px bg-[var(--border-primary)] my-2" />
              <div>
                <p className="text-xs text-[var(--text-tertiary)] mb-1">Notes</p>
                <p className="text-sm text-[var(--text-secondary)]">{tx.notes}</p>
              </div>
            </>
          )}
        </div>
      </>
    );
  };

  const renderDividendDetails = () => (
    <>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 rounded-xl bg-teal-50 dark:bg-teal-950/40">
          <BanknotesIcon className="w-6 h-6 text-teal-600 dark:text-teal-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">{tx.symbol}</h2>
          <p className="text-sm text-[var(--text-secondary)]">{tx.name}</p>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-[var(--bg-tertiary)] rounded-lg p-4 mb-6">
        <div className="flex justify-between items-center">
          <span className="text-sm text-[var(--text-secondary)]">Dividend Received</span>
          <span className="text-2xl font-semibold font-mono tabular-nums text-teal-600 dark:text-teal-400">
            +{formatCurrency(Math.abs(tx.amount), currency)}
          </span>
        </div>
      </div>

      {/* Details Grid */}
      <div className="space-y-4">
        <DetailRow label="Description" value={tx.description} />
        {tx.shares_held && (
          <DetailRow label="Shares Held" value={`${tx.shares_held} shares`} />
        )}
        {tx.dividend_per_share && (
          <DetailRow label="Per Share" value={formatCurrency(tx.dividend_per_share, currency)} />
        )}
        <div className="h-px bg-[var(--border-primary)] my-2" />
        <DetailRow label="Payment Date" value={formatShortDate(tx.date)} />
        {tx.ex_date && (
          <DetailRow label="Ex-Dividend Date" value={formatShortDate(tx.ex_date)} />
        )}
        <DetailRow label="Account" value={tx.account_name} />
      </div>
    </>
  );

  const renderForexDetails = () => (
    <>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 rounded-xl bg-violet-50 dark:bg-violet-950/40">
          <ArrowsRightLeftIcon className="w-6 h-6 text-violet-600 dark:text-violet-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">
            {tx.from_currency} → {tx.to_currency}
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">Currency Exchange</p>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-[var(--bg-tertiary)] rounded-lg p-4 mb-6">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm text-[var(--text-secondary)]">You Received</span>
          <span className="text-2xl font-semibold font-mono tabular-nums text-violet-600 dark:text-violet-400">
            {getCurrencySymbol(tx.to_currency)}{tx.to_amount.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-[var(--text-tertiary)]">You Converted</span>
          <span className="font-mono tabular-nums text-[var(--text-secondary)]">
            {getCurrencySymbol(tx.from_currency)}{tx.from_amount.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Details Grid */}
      <div className="space-y-4">
        <DetailRow label="Exchange Rate" value={`1 ${tx.from_currency} = ${formatRate(tx.exchange_rate)} ${tx.to_currency}`} />
        {tx.fee > 0 && (
          <DetailRow label="Fee" value={`${getCurrencySymbol(tx.from_currency)}${tx.fee}`} />
        )}
        <div className="h-px bg-[var(--border-primary)] my-2" />
        <DetailRow label="Date" value={formatShortDate(tx.date)} />
        <DetailRow label="Account" value={tx.account_name} />
      </div>
    </>
  );

  const renderCashDetails = () => {
    const isDeposit = tx.activity_type === 'DEPOSIT';
    const isFee = tx.activity_type === 'FEE';
    const isInterest = tx.activity_type === 'INTEREST';
    const displayType = tx.cash_type || (isDeposit ? 'Deposit' : 'Withdrawal');

    // Determine colors and icons based on transaction type
    const getStyleConfig = () => {
      if (isDeposit) {
        return {
          bgColor: 'bg-blue-50 dark:bg-blue-950/40',
          textColor: 'text-blue-600 dark:text-blue-400',
          icon: <PlusCircleIcon className="w-6 h-6 text-blue-600 dark:text-blue-400" />,
          sign: '+',
        };
      } else if (isInterest) {
        return {
          bgColor: 'bg-green-50 dark:bg-green-950/40',
          textColor: 'text-green-600 dark:text-green-400',
          icon: <BanknotesIcon className="w-6 h-6 text-green-600 dark:text-green-400" />,
          sign: '+',
        };
      } else if (isFee) {
        return {
          bgColor: 'bg-red-50 dark:bg-red-950/40',
          textColor: 'text-red-600 dark:text-red-400',
          icon: <ReceiptPercentIcon className="w-6 h-6 text-red-600 dark:text-red-400" />,
          sign: '-',
        };
      } else {
        return {
          bgColor: 'bg-amber-50 dark:bg-amber-950/40',
          textColor: 'text-amber-600 dark:text-amber-400',
          icon: <MinusCircleIcon className="w-6 h-6 text-amber-600 dark:text-amber-400" />,
          sign: '-',
        };
      }
    };

    const style = getStyleConfig();

    return (
      <>
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className={cn('p-3 rounded-xl', style.bgColor)}>
            {style.icon}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              {displayType}
            </h2>
            <p className="text-sm text-[var(--text-secondary)]">{tx.description}</p>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-[var(--bg-tertiary)] rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-sm text-[var(--text-secondary)]">Amount</span>
            <span className={cn('text-2xl font-semibold font-mono tabular-nums', style.textColor)}>
              {style.sign}{formatCurrency(Math.abs(tx.amount), currency)}
            </span>
          </div>
        </div>

        {/* Details Grid */}
        <div className="space-y-4">
          <DetailRow label="Type" value={displayType} />
          {tx.fee > 0 && (
            <DetailRow label="Commission/Fee" value={formatCurrency(tx.fee, currency)} />
          )}
          {tx.reference && (
            <DetailRow label="Reference" value={tx.reference} />
          )}
          <div className="h-px bg-[var(--border-primary)] my-2" />
          <DetailRow label="Date" value={formatShortDate(tx.date)} />
          <DetailRow label="Account" value={tx.account_name} />
        </div>
      </>
    );
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-[var(--bg-primary)] z-50 shadow-xl overflow-y-auto">
        {/* Close button */}
        <div className="sticky top-0 bg-[var(--bg-primary)] p-4 border-b border-[var(--border-primary)] flex justify-between items-center">
          <span className="text-sm text-[var(--text-tertiary)]">Transaction Details</span>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <XMarkIcon className="w-5 h-5 text-[var(--text-secondary)]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {tx.type === 'trade' && renderTradeDetails()}
          {tx.type === 'dividend' && renderDividendDetails()}
          {tx.type === 'forex' && renderForexDetails()}
          {tx.type === 'cash' && renderCashDetails()}
        </div>
      </div>
    </>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-sm text-[var(--text-tertiary)]">{label}</span>
      <span className="text-sm text-[var(--text-primary)] font-medium">{value}</span>
    </div>
  );
}

// ============================================
// DATE RANGE FILTER COMPONENT
// ============================================

function DateRangeFilter({ value, onChange, presets }) {
  const [isOpen, setIsOpen] = useState(false);
  const [showCustom, setShowCustom] = useState(value.type === 'custom');
  const [customStart, setCustomStart] = useState(value.startDate || '');
  const [customEnd, setCustomEnd] = useState(value.endDate || '');
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handlePresetSelect = (preset) => {
    onChange({ type: 'preset', preset: preset.id, label: preset.label });
    setShowCustom(false);
    setIsOpen(false);
  };

  const handleCustomApply = () => {
    if (customStart && customEnd) {
      onChange({
        type: 'custom',
        startDate: customStart,
        endDate: customEnd,
        label: `${customStart} - ${customEnd}`,
      });
      setIsOpen(false);
    }
  };

  const displayLabel = value.label || 'All Time';
  const isCustomActive = value.type === 'custom';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-4 py-2.5 rounded-lg cursor-pointer',
          'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
          'text-[var(--text-primary)] text-sm',
          'hover:bg-[var(--bg-tertiary)] transition-colors',
          isCustomActive && 'border-accent'
        )}
      >
        <CalendarIcon className="w-4 h-4 text-[var(--text-tertiary)]" />
        <span>{displayLabel}</span>
        <ChevronDownIcon className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 min-w-[280px] bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg z-50 py-1">
          {/* Preset Options */}
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePresetSelect(preset)}
              className={cn(
                'flex items-center gap-2 w-full px-3 py-2 text-sm text-left transition-colors cursor-pointer',
                value.type === 'preset' && value.preset === preset.id
                  ? 'bg-accent/10 text-accent'
                  : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
              )}
            >
              {preset.label}
            </button>
          ))}

          <div className="h-px bg-[var(--border-primary)] my-1" />

          {/* Custom Range Toggle */}
          <button
            onClick={() => setShowCustom(!showCustom)}
            className={cn(
              'flex items-center justify-between w-full px-3 py-2 text-sm text-left transition-colors cursor-pointer',
              showCustom || isCustomActive
                ? 'bg-accent/10 text-accent'
                : 'hover:bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
            )}
          >
            <span>Custom Range</span>
            <ChevronDownIcon className={cn('w-4 h-4 transition-transform', showCustom && 'rotate-180')} />
          </button>

          {/* Custom Date Inputs */}
          {showCustom && (
            <div className="px-3 py-3 space-y-3">
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="text-xs text-[var(--text-tertiary)] mb-1 block">From</label>
                  <input
                    type="date"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                    className={cn(
                      'w-full px-2 py-1.5 rounded text-sm',
                      'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                      'text-[var(--text-primary)]',
                      'focus:outline-none focus:ring-1 focus:ring-accent'
                    )}
                  />
                </div>
                <div className="flex-1">
                  <label className="text-xs text-[var(--text-tertiary)] mb-1 block">To</label>
                  <input
                    type="date"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                    className={cn(
                      'w-full px-2 py-1.5 rounded text-sm',
                      'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                      'text-[var(--text-primary)]',
                      'focus:outline-none focus:ring-1 focus:ring-accent'
                    )}
                  />
                </div>
              </div>
              <button
                onClick={handleCustomApply}
                disabled={!customStart || !customEnd}
                className={cn(
                  'w-full py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer',
                  customStart && customEnd
                    ? 'bg-accent text-white hover:bg-accent/90'
                    : 'bg-[var(--bg-tertiary)] text-[var(--text-tertiary)] cursor-not-allowed'
                )}
              >
                Apply
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================
// FILTER BAR COMPONENT
// ============================================

function FilterBar({
  searchQuery,
  setSearchQuery,
  selectedTypes,
  setSelectedTypes,
  selectedAccounts,
  setSelectedAccounts,
  dateRange,
  setDateRange,
  accounts,
  types,
  datePresets,
}) {
  return (
    <div className="flex flex-col lg:flex-row gap-4 mb-6">
      {/* Search */}
      <div className="relative flex-1 max-w-md">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-tertiary)]" />
        <input
          type="text"
          placeholder="Search by symbol..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={cn(
            'w-full pl-10 pr-4 py-2.5 rounded-lg',
            'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
            'text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]',
            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
            'transition-colors'
          )}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <MultiSelectFilter
          label="Types"
          options={types}
          selected={selectedTypes}
          onChange={setSelectedTypes}
          getOptionLabel={(t) => t}
          getOptionValue={(t) => t}
        />

        <MultiSelectFilter
          label="Accounts"
          options={accounts}
          selected={selectedAccounts}
          onChange={setSelectedAccounts}
          getOptionLabel={(a) => a.name}
          getOptionValue={(a) => a.id}
        />

        <DateRangeFilter
          value={dateRange}
          onChange={setDateRange}
          presets={datePresets}
        />
      </div>
    </div>
  );
}

// ============================================
// MAIN COMPONENT
// ============================================

/**
 * Transform API trade response to unified format
 */
function transformTrade(trade) {
  return {
    id: `trade-${trade.id}`,
    type: 'trade',
    date: trade.date,
    symbol: trade.symbol,
    name: trade.asset_name,
    side: trade.action === 'Buy' ? 'BUY' : 'SELL',
    quantity: parseFloat(trade.quantity),
    price: parseFloat(trade.price_per_unit),
    total: parseFloat(trade.total),
    fee: parseFloat(trade.fees || 0),
    currency: trade.currency || 'USD',
    account_name: trade.account_name,
    notes: trade.notes,
  };
}

/**
 * Transform API dividend response to unified format
 */
function transformDividend(div) {
  return {
    id: `dividend-${div.id}`,
    type: 'dividend',
    date: div.date,
    symbol: div.symbol,
    name: div.asset_name,
    amount: parseFloat(div.amount),
    currency: div.currency || 'USD',
    description: div.type === 'Dividend' ? 'Dividend payment' : div.type,
    account_name: div.account_name,
    notes: div.notes,
  };
}

/**
 * Transform API forex response to unified format
 */
function transformForex(fx) {
  return {
    id: `forex-${fx.id}`,
    type: 'forex',
    date: fx.date,
    from_currency: fx.from_currency,
    to_currency: fx.to_currency,
    from_amount: parseFloat(fx.from_amount),
    to_amount: parseFloat(fx.to_amount),
    exchange_rate: parseFloat(fx.exchange_rate),
    fee: 0,
    account_name: fx.account_name,
    notes: fx.notes,
  };
}

/**
 * Transform API cash response to unified format
 */
function transformCash(cash) {
  // Map transaction type to activity type for display
  const activityTypeMap = {
    'Deposit': 'DEPOSIT',
    'Withdrawal': 'WITHDRAWAL',
    'Fee': 'FEE',
    'Transfer': 'TRANSFER',
    'Custody Fee': 'FEE',
    'Interest': 'INTEREST',
  };
  const activityType = activityTypeMap[cash.type] || cash.type.toUpperCase();

  return {
    id: `cash-${cash.id}`,
    type: 'cash',
    date: cash.date,
    activity_type: activityType,
    cash_type: cash.type,  // Keep original type for display
    amount: parseFloat(cash.amount),
    fee: parseFloat(cash.fees || 0),
    currency: cash.currency || 'USD',
    description: cash.type + (cash.notes ? ` - ${cash.notes}` : ''),
    account_name: cash.account_name,
    reference: null,
  };
}

export default function Activity() {
  const { currency } = useCurrency();
  const { selectedPortfolioId } = usePortfolio();

  // Data fetching state
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter states - initialized after data loads
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState([...TRANSACTION_TYPES]);
  const [selectedAccounts, setSelectedAccounts] = useState([]);
  const [dateRange, setDateRange] = useState({ type: 'preset', preset: 'all', label: 'All Time' });
  const [filtersInitialized, setFiltersInitialized] = useState(false);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Selected transaction for detail panel
  const [selectedTransaction, setSelectedTransaction] = useState(null);

  // Fetch transactions and accounts
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      // Build query params - add portfolio_id if a specific portfolio is selected
      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';

      try {
        // Fetch accounts first
        const accountsRes = await api(`/accounts?is_active=true${portfolioParam}`);
        if (!accountsRes.ok) {
          throw new Error(`Failed to fetch accounts: ${accountsRes.statusText}`);
        }
        const accountsData = await accountsRes.json();
        setAccounts(accountsData);

        // Fetch all transaction types in parallel
        const [tradesRes, dividendsRes, forexRes, cashRes] = await Promise.all([
          api(`/transactions/trades?limit=500${portfolioParam}`),
          api(`/transactions/dividends?limit=500${portfolioParam}`),
          api(`/transactions/forex?limit=500${portfolioParam}`),
          api(`/transactions/cash?limit=500${portfolioParam}`),
        ]);

        // Check for errors
        if (!tradesRes.ok) throw new Error(`Failed to fetch trades: ${tradesRes.statusText}`);
        if (!dividendsRes.ok) throw new Error(`Failed to fetch dividends: ${dividendsRes.statusText}`);
        if (!forexRes.ok) throw new Error(`Failed to fetch forex: ${forexRes.statusText}`);
        if (!cashRes.ok) throw new Error(`Failed to fetch cash: ${cashRes.statusText}`);

        // Parse responses
        const [tradesData, dividendsData, forexData, cashData] = await Promise.all([
          tradesRes.json(),
          dividendsRes.json(),
          forexRes.json(),
          cashRes.json(),
        ]);

        // Transform and merge all transactions
        const allTransactions = [
          ...tradesData.map(transformTrade),
          ...dividendsData.map(transformDividend),
          ...forexData.map(transformForex),
          ...cashData.map(transformCash),
        ];

        // Sort by date descending
        allTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));

        setTransactions(allTransactions);

        // Initialize account filter with all accounts selected
        if (!filtersInitialized) {
          setSelectedAccounts(accountsData.map((a) => a.id));
          setFiltersInitialized(true);
        }
      } catch (err) {
        console.error('Error fetching activity data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedPortfolioId]);

  // Filter and group transactions
  const { groupedTransactions, totalCount, filteredCount, totalPages } = useMemo(() => {
    // Filter transactions
    let filtered = transactions.filter((tx) => {
      // Type filter
      const typeMap = { trade: 'Trade', dividend: 'Dividend', forex: 'Forex', cash: 'Cash' };
      const typeMatch = selectedTypes.length === TRANSACTION_TYPES.length ||
        selectedTypes.includes(typeMap[tx.type]);

      // Account filter - match by account_name since we don't have account_id in transformed data
      const accountNames = accounts
        .filter((a) => selectedAccounts.includes(a.id))
        .map((a) => a.name);
      const accountMatch = selectedAccounts.length === accounts.length ||
        accountNames.includes(tx.account_name);

      // Search filter (symbol only for trades and dividends)
      const searchMatch = !searchQuery ||
        (tx.symbol && tx.symbol.toLowerCase().includes(searchQuery.toLowerCase()));

      // Date range filter
      let dateMatch = true;
      if (dateRange.type === 'custom' && dateRange.startDate && dateRange.endDate) {
        const txDate = new Date(tx.date);
        const startDate = new Date(dateRange.startDate);
        const endDate = new Date(dateRange.endDate);
        dateMatch = txDate >= startDate && txDate <= endDate;
      } else if (dateRange.type === 'preset' && dateRange.preset !== 'all') {
        const txDate = new Date(tx.date);
        const now = new Date();
        const preset = DATE_RANGES.find((r) => r.id === dateRange.preset);
        if (preset && preset.days) {
          if (preset.days === 'ytd') {
            const yearStart = new Date(now.getFullYear(), 0, 1);
            dateMatch = txDate >= yearStart;
          } else {
            const cutoff = new Date(now);
            cutoff.setDate(cutoff.getDate() - preset.days);
            dateMatch = txDate >= cutoff;
          }
        }
      }

      return typeMatch && accountMatch && searchMatch && dateMatch;
    });

    // Calculate pagination
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    const paginatedTransactions = filtered.slice(startIndex, endIndex);

    // Group by date
    const grouped = {};
    paginatedTransactions.forEach((tx) => {
      if (!grouped[tx.date]) {
        grouped[tx.date] = [];
      }
      grouped[tx.date].push(tx);
    });

    return {
      groupedTransactions: grouped,
      totalCount: transactions.length,
      filteredCount: filtered.length,
      totalPages: Math.ceil(filtered.length / pageSize),
    };
  }, [transactions, searchQuery, selectedTypes, selectedAccounts, dateRange, currentPage, pageSize, accounts]);

  // Reset pagination when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedTypes, selectedAccounts, dateRange]);

  // Loading state
  if (loading) {
    return (
      <PageContainer>
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Activity</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Complete transaction history across all accounts
          </p>
        </div>

        {/* Filters skeleton */}
        <div className="flex flex-col lg:flex-row gap-4 mb-6">
          <Skeleton className="h-11 w-full max-w-md" />
          <div className="flex flex-wrap gap-3">
            <Skeleton className="h-10 w-28" />
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-36" />
          </div>
        </div>

        {/* Timeline skeleton */}
        <div className="space-y-8">
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="flex items-center gap-3 mb-4">
                <Skeleton className="w-2 h-2 rounded-full" />
                <Skeleton className="h-4 w-48" />
              </div>
              <div className="space-y-3 ml-4 pl-4 border-l-2 border-[var(--border-primary)]">
                {[1, 2].map((j) => (
                  <Skeleton key={j} className="h-24 w-full rounded-lg" />
                ))}
              </div>
            </div>
          ))}
        </div>
      </PageContainer>
    );
  }

  // Error state
  if (error) {
    return (
      <PageContainer>
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Activity</h1>
        </div>
        <div className="text-center py-12">
          <p className="text-negative mb-2">Error loading activity</p>
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
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Activity</h1>
        <p className="text-[var(--text-secondary)] mt-1">
          Complete transaction history across all accounts
        </p>
      </div>

      {/* Filters */}
      <FilterBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        selectedTypes={selectedTypes}
        setSelectedTypes={setSelectedTypes}
        selectedAccounts={selectedAccounts}
        setSelectedAccounts={setSelectedAccounts}
        dateRange={dateRange}
        setDateRange={setDateRange}
        accounts={accounts}
        types={TRANSACTION_TYPES}
        datePresets={DATE_RANGES}
      />

      {/* Transaction Timeline */}
      <div className="space-y-8">
        {Object.keys(groupedTransactions).length === 0 ? (
          <div className="text-center py-12">
            <CalendarIcon className="w-12 h-12 mx-auto text-[var(--text-tertiary)] mb-4" />
            <h3 className="text-lg font-medium text-[var(--text-primary)]">No transactions found</h3>
            <p className="text-[var(--text-secondary)] mt-1">
              Try adjusting your filters to see more results.
            </p>
          </div>
        ) : (
          Object.entries(groupedTransactions)
            .sort(([dateA], [dateB]) => new Date(dateB) - new Date(dateA))
            .map(([date, transactions]) => (
              <div key={date}>
                {/* Date Header */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-2 h-2 rounded-full bg-accent" />
                  <h2 className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wide">
                    {formatDateHeader(date)}
                  </h2>
                  <div className="flex-1 h-px bg-[var(--border-primary)]" />
                </div>

                {/* Transaction Cards */}
                <div className="space-y-3 ml-4 pl-4 border-l-2 border-[var(--border-primary)]">
                  {transactions.map((tx) => (
                    <TransactionCard
                      key={tx.id}
                      tx={tx}
                      currency={currency}
                      onClick={() => setSelectedTransaction(tx)}
                    />
                  ))}
                </div>
              </div>
            ))
        )}
      </div>

      {/* Footer with pagination */}
      <div className="mt-8 flex items-center justify-between py-4 border-t border-[var(--border-primary)]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-[var(--text-secondary)]">Show:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className={cn(
                'px-2 py-1 rounded text-sm',
                'bg-[var(--bg-primary)] border border-[var(--border-primary)]',
                'text-[var(--text-primary)] cursor-pointer',
                'focus:outline-none focus:ring-2 focus:ring-accent/50'
              )}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <p className="text-sm text-[var(--text-tertiary)]">
            Showing {Math.min((currentPage - 1) * pageSize + 1, filteredCount)}-{Math.min(currentPage * pageSize, filteredCount)} of {filteredCount}
            {filteredCount !== totalCount && (
              <span> ({totalCount} total)</span>
            )}
          </p>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => { setCurrentPage(1); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              disabled={currentPage === 1}
              className={cn(
                'p-1.5 rounded',
                'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                'hover:bg-[var(--border-primary)] transition-colors',
                currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
              )}
              title="First page"
            >
              <ChevronDoubleLeftIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => { setCurrentPage((p) => Math.max(1, p - 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              disabled={currentPage === 1}
              className={cn(
                'p-1.5 rounded',
                'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                'hover:bg-[var(--border-primary)] transition-colors',
                currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
              )}
              title="Previous page"
            >
              <ChevronLeftIcon className="w-4 h-4" />
            </button>
            <span className="text-sm text-[var(--text-secondary)] px-2">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => { setCurrentPage((p) => Math.min(totalPages, p + 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              disabled={currentPage >= totalPages}
              className={cn(
                'p-1.5 rounded',
                'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                'hover:bg-[var(--border-primary)] transition-colors',
                currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
              )}
              title="Next page"
            >
              <ChevronRightIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => { setCurrentPage(totalPages); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              disabled={currentPage >= totalPages}
              className={cn(
                'p-1.5 rounded',
                'bg-[var(--bg-secondary)] text-[var(--text-primary)]',
                'hover:bg-[var(--border-primary)] transition-colors',
                currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
              )}
              title="Last page"
            >
              <ChevronDoubleRightIcon className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Transaction Detail Panel */}
      {selectedTransaction && (
        <TransactionDetailPanel
          transaction={selectedTransaction}
          currency={currency}
          onClose={() => setSelectedTransaction(null)}
        />
      )}
    </PageContainer>
  );
}
