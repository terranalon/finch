/**
 * Insights Page Mock - Finch Redesign
 *
 * Purpose: Deep-dive analytics with interactive breakdowns and custom charts
 *
 * This is a static mock with hardcoded data for review.
 * After approval, it will be wired up to real API endpoints.
 */

import React, { useState } from 'react';
import { cn, formatCurrency, formatPercent } from '../lib';
import { useCurrency } from '../contexts';
import { PageContainer } from '../components/layout';

// ============================================
// MOCK DATA - Replace with real API data later
// ============================================

const MOCK_PERFORMANCE_DATA = {
  periods: [
    { label: '1W', value: 2.34, amount: 28500 },
    { label: '1M', value: 5.67, amount: 68000 },
    { label: '3M', value: 8.92, amount: 105000 },
    { label: 'YTD', value: 12.45, amount: 145000 },
    { label: '1Y', value: 18.23, amount: 210000 },
    { label: 'ALL', value: 45.67, amount: 420000 },
  ],
  byAssetClass: [
    { name: 'Stocks', value: 22.5, amount: 180000, allocation: 62 },
    { name: 'ETFs', value: 15.3, amount: 95000, allocation: 28 },
    { name: 'Crypto', value: 45.2, amount: 35000, allocation: 7 },
    { name: 'Cash', value: 0.5, amount: 2000, allocation: 3 },
  ],
  bySector: [
    { name: 'Technology', value: 28.4, amount: 125000, allocation: 35 },
    { name: 'Healthcare', value: 12.1, amount: 65000, allocation: 18 },
    { name: 'Financials', value: 8.7, amount: 55000, allocation: 15 },
    { name: 'Consumer', value: 15.2, amount: 48000, allocation: 13 },
    { name: 'Energy', value: -5.3, amount: 32000, allocation: 9 },
    { name: 'Other', value: 6.8, amount: 35000, allocation: 10 },
  ],
};

const MOCK_ALLOCATION_DATA = {
  byAssetClass: [
    { name: 'Stocks', value: 765000, percent: 62, color: 'bg-blue-500' },
    { name: 'ETFs', value: 345000, percent: 28, color: 'bg-emerald-500' },
    { name: 'Crypto', value: 86000, percent: 7, color: 'bg-amber-500' },
    { name: 'Cash', value: 38000, percent: 3, color: 'bg-slate-400' },
  ],
  bySector: [
    { name: 'Technology', value: 432000, percent: 35, color: 'bg-violet-500' },
    { name: 'Healthcare', value: 222000, percent: 18, color: 'bg-rose-500' },
    { name: 'Financials', value: 185000, percent: 15, color: 'bg-cyan-500' },
    { name: 'Consumer', value: 160000, percent: 13, color: 'bg-orange-500' },
    { name: 'Energy', value: 111000, percent: 9, color: 'bg-lime-500' },
    { name: 'Other', value: 124000, percent: 10, color: 'bg-slate-500' },
  ],
  byGeography: [
    { name: 'United States', value: 988000, percent: 80, color: 'bg-blue-500' },
    { name: 'Europe', value: 124000, percent: 10, color: 'bg-emerald-500' },
    { name: 'Asia Pacific', value: 86000, percent: 7, color: 'bg-amber-500' },
    { name: 'Other', value: 36000, percent: 3, color: 'bg-slate-400' },
  ],
  byAccount: [
    { name: 'IBKR Main', value: 890000, percent: 72, color: 'bg-blue-500' },
    { name: 'Fidelity IRA', value: 234567, percent: 19, color: 'bg-emerald-500' },
    { name: 'Coinbase', value: 110000, percent: 9, color: 'bg-amber-500' },
  ],
};

const MOCK_INCOME_DATA = {
  totalDividends: 4521,
  ytdDividends: 3200,
  monthlyAverage: 377,
  monthlyData: [
    { month: 'Jan', value: 320 },
    { month: 'Feb', value: 285 },
    { month: 'Mar', value: 450 },
    { month: 'Apr', value: 310 },
    { month: 'May', value: 295 },
    { month: 'Jun', value: 520 },
    { month: 'Jul', value: 340 },
    { month: 'Aug', value: 280 },
    { month: 'Sep', value: 480 },
    { month: 'Oct', value: 350 },
    { month: 'Nov', value: 310 },
    { month: 'Dec', value: 581 },
  ],
  topPayers: [
    { symbol: 'AAPL', name: 'Apple Inc.', amount: 1200, yield: 0.5 },
    { symbol: 'VTI', name: 'Vanguard Total Stock', amount: 890, yield: 1.4 },
    { symbol: 'MSFT', name: 'Microsoft Corp.', amount: 650, yield: 0.8 },
    { symbol: 'JNJ', name: 'Johnson & Johnson', amount: 520, yield: 2.9 },
    { symbol: 'PG', name: 'Procter & Gamble', amount: 480, yield: 2.4 },
  ],
};

const MOCK_ACCOUNTS = [
  { id: 1, name: 'IBKR Main' },
  { id: 2, name: 'Fidelity IRA' },
  { id: 3, name: 'Coinbase' },
];

const MOCK_ASSET_CLASSES = ['Stocks', 'ETFs', 'Crypto', 'Cash'];

// ============================================
// ICONS
// ============================================

function ChevronDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
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

function ArrowTrendingUpIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
    </svg>
  );
}

function ArrowTrendingDownIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6 9 12.75l4.286-4.286a11.948 11.948 0 0 1 4.306 6.43l.776 2.898m0 0 3.182-5.511m-3.182 5.51-5.511-3.181" />
    </svg>
  );
}

function BanknotesIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
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
// FILTER COMPONENTS
// ============================================

function DateRangeFilter({ value, onChange }) {
  const options = ['1M', '3M', 'YTD', '1Y', 'ALL'];

  return (
    <div className="flex items-center gap-1 p-1 bg-[var(--bg-tertiary)] rounded-lg">
      {options.map((option) => (
        <button
          key={option}
          onClick={() => onChange(option)}
          className={cn(
            'px-3 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer',
            value === option
              ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          )}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

function MultiSelectDropdown({ label, options, selected, onChange }) {
  const [isOpen, setIsOpen] = useState(false);

  const allSelected = selected.length === options.length;
  const displayLabel = allSelected
    ? label
    : selected.length === 0
    ? `No ${label}`
    : `${selected.length} ${label}`;

  const toggleOption = (option) => {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  const toggleAll = () => {
    if (allSelected) {
      onChange([]);
    } else {
      onChange([...options]);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer',
          'bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)]',
          !allSelected && selected.length > 0 && 'ring-2 ring-accent/30'
        )}
      >
        {displayLabel}
        <ChevronDownIcon className={cn('w-4 h-4 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-1 z-20 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-lg shadow-lg min-w-[180px] py-1">
            {/* Select All */}
            <button
              onClick={toggleAll}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-[var(--bg-tertiary)] cursor-pointer"
            >
              <span
                className={cn(
                  'w-4 h-4 rounded border flex items-center justify-center',
                  allSelected
                    ? 'bg-accent border-accent'
                    : 'border-[var(--border-secondary)]'
                )}
              >
                {allSelected && <CheckIcon className="w-3 h-3 text-white" />}
              </span>
              <span className="font-medium text-[var(--text-primary)]">Select All</span>
            </button>

            <div className="h-px bg-[var(--border-primary)] my-1" />

            {/* Options */}
            {options.map((option) => {
              const isSelected = selected.includes(option);
              const optionLabel = typeof option === 'object' ? option.name : option;

              return (
                <button
                  key={optionLabel}
                  onClick={() => toggleOption(option)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left hover:bg-[var(--bg-tertiary)] cursor-pointer"
                >
                  <span
                    className={cn(
                      'w-4 h-4 rounded border flex items-center justify-center',
                      isSelected
                        ? 'bg-accent border-accent'
                        : 'border-[var(--border-secondary)]'
                    )}
                  >
                    {isSelected && <CheckIcon className="w-3 h-3 text-white" />}
                  </span>
                  <span className="text-[var(--text-primary)]">{optionLabel}</span>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

// ============================================
// PERFORMANCE BREAKDOWN SECTION
// ============================================

function PerformanceBreakdown({ data, currency, dateRange }) {
  const [activeTab, setActiveTab] = useState('period');
  const tabs = [
    { id: 'period', label: 'By Period' },
    { id: 'assetClass', label: 'By Asset Class' },
    { id: 'sector', label: 'By Sector' },
  ];

  const getActiveData = () => {
    switch (activeTab) {
      case 'period':
        return data.periods;
      case 'assetClass':
        return data.byAssetClass;
      case 'sector':
        return data.bySector;
      default:
        return data.periods;
    }
  };

  const activeData = getActiveData();
  const maxValue = Math.max(...activeData.map((d) => Math.abs(d.value)));

  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">Performance Breakdown</h2>
        <div className="flex items-center gap-1 p-1 bg-[var(--bg-tertiary)] rounded-lg">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-3 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer',
                activeTab === tab.id
                  ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Performance Bars */}
      <div className="space-y-4">
        {activeData.map((item) => {
          const isPositive = item.value >= 0;
          const barWidth = (Math.abs(item.value) / maxValue) * 100;

          return (
            <div key={item.label || item.name} className="group">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-medium text-[var(--text-primary)]">
                  {item.label || item.name}
                </span>
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      'text-sm font-semibold font-mono tabular-nums',
                      isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
                    )}
                  >
                    {isPositive ? '+' : ''}
                    {item.value.toFixed(2)}%
                  </span>
                  <span className="text-sm text-[var(--text-secondary)] font-mono tabular-nums">
                    {formatCurrency(item.amount, currency)}
                  </span>
                </div>
              </div>
              <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-300',
                    isPositive ? 'bg-emerald-500' : 'bg-red-500'
                  )}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================
// ALLOCATION ANALYSIS SECTION
// ============================================

function AllocationAnalysis({ data, currency }) {
  const [activeTab, setActiveTab] = useState('assetClass');
  const tabs = [
    { id: 'assetClass', label: 'By Asset Class' },
    { id: 'sector', label: 'By Sector' },
    { id: 'geography', label: 'By Geography' },
    { id: 'account', label: 'By Account' },
  ];

  const getActiveData = () => {
    switch (activeTab) {
      case 'assetClass':
        return data.byAssetClass;
      case 'sector':
        return data.bySector;
      case 'geography':
        return data.byGeography;
      case 'account':
        return data.byAccount;
      default:
        return data.byAssetClass;
    }
  };

  const activeData = getActiveData();
  const total = activeData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">Allocation Analysis</h2>
        <div className="flex flex-wrap items-center gap-1 p-1 bg-[var(--bg-tertiary)] rounded-lg">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-3 py-1.5 rounded-md text-sm font-medium transition-colors cursor-pointer',
                activeTab === tab.id
                  ? 'bg-[var(--bg-primary)] text-[var(--text-primary)] shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stacked Bar */}
      <div className="h-8 flex rounded-lg overflow-hidden mb-6">
        {activeData.map((item, index) => (
          <div
            key={item.name}
            className={cn(item.color, 'transition-all duration-300 hover:opacity-80 cursor-pointer')}
            style={{ width: `${item.percent}%` }}
            title={`${item.name}: ${item.percent}%`}
          />
        ))}
      </div>

      {/* Legend & Details */}
      <div className="grid grid-cols-2 gap-4">
        {activeData.map((item) => (
          <div
            key={item.name}
            className="flex items-center gap-3 p-3 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <div className={cn('w-3 h-3 rounded-full', item.color)} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--text-primary)] truncate">{item.name}</p>
              <p className="text-xs text-[var(--text-secondary)]">{item.percent}%</p>
            </div>
            <p className="text-sm font-mono tabular-nums text-[var(--text-primary)]">
              {formatCurrency(item.value, currency)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// INCOME ANALYSIS SECTION
// ============================================

function IncomeAnalysis({ data, currency }) {
  const maxMonthlyValue = Math.max(...data.monthlyData.map((d) => d.value));

  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] p-6 shadow-sm dark:shadow-none">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-950/40">
          <BanknotesIcon className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Income Analysis</h2>
          <p className="text-sm text-[var(--text-secondary)]">Dividend income over time</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
          <p className="text-xs text-[var(--text-tertiary)] mb-1">Total (12M)</p>
          <p className="text-xl font-semibold font-mono tabular-nums text-[var(--text-primary)]">
            {formatCurrency(data.totalDividends, currency)}
          </p>
        </div>
        <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
          <p className="text-xs text-[var(--text-tertiary)] mb-1">YTD</p>
          <p className="text-xl font-semibold font-mono tabular-nums text-[var(--text-primary)]">
            {formatCurrency(data.ytdDividends, currency)}
          </p>
        </div>
        <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
          <p className="text-xs text-[var(--text-tertiary)] mb-1">Monthly Avg</p>
          <p className="text-xl font-semibold font-mono tabular-nums text-[var(--text-primary)]">
            {formatCurrency(data.monthlyAverage, currency)}
          </p>
        </div>
      </div>

      {/* Monthly Bar Chart */}
      <div className="mb-6">
        <h3 className="text-sm font-medium text-[var(--text-primary)] mb-4">Monthly Dividends</h3>
        <div className="flex items-end gap-1 h-32">
          {data.monthlyData.map((month) => {
            const height = (month.value / maxMonthlyValue) * 100;
            return (
              <div key={month.month} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-emerald-500 dark:bg-emerald-400 rounded-t transition-all hover:bg-emerald-600 dark:hover:bg-emerald-300 cursor-pointer"
                  style={{ height: `${height}%` }}
                  title={`${month.month}: ${formatCurrency(month.value, currency)}`}
                />
                <span className="text-xs text-[var(--text-tertiary)]">{month.month.slice(0, 1)}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Dividend Payers */}
      <div>
        <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3">Top Dividend Payers</h3>
        <div className="space-y-2">
          {data.topPayers.map((payer, index) => (
            <div
              key={payer.symbol}
              className="flex items-center gap-3 p-3 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
            >
              <span className="text-sm font-medium text-[var(--text-tertiary)] w-5">{index + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-[var(--text-primary)]">{payer.symbol}</span>
                  <span className="text-xs text-[var(--text-tertiary)]">{payer.yield.toFixed(1)}% yield</span>
                </div>
                <p className="text-xs text-[var(--text-secondary)] truncate">{payer.name}</p>
              </div>
              <p className="text-sm font-mono tabular-nums text-emerald-600 dark:text-emerald-400">
                +{formatCurrency(payer.amount, currency)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================
// MAIN COMPONENT
// ============================================

export default function Insights() {
  const { currency } = useCurrency();
  const [dateRange, setDateRange] = useState('1Y');
  const [selectedAccounts, setSelectedAccounts] = useState(MOCK_ACCOUNTS.map((a) => a.name));
  const [selectedAssetClasses, setSelectedAssetClasses] = useState([...MOCK_ASSET_CLASSES]);

  return (
    <PageContainer>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Insights</h1>
          <p className="text-[var(--text-secondary)] mt-1">
            Deep-dive analytics and performance breakdowns
          </p>
        </div>
      </div>

      {/* Global Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-8">
        <DateRangeFilter value={dateRange} onChange={setDateRange} />
        <MultiSelectDropdown
          label="Accounts"
          options={MOCK_ACCOUNTS.map((a) => a.name)}
          selected={selectedAccounts}
          onChange={setSelectedAccounts}
        />
        <MultiSelectDropdown
          label="Asset Classes"
          options={MOCK_ASSET_CLASSES}
          selected={selectedAssetClasses}
          onChange={setSelectedAssetClasses}
        />
      </div>

      {/* Content Grid */}
      <div className="space-y-6">
        {/* Performance Breakdown */}
        <PerformanceBreakdown
          data={MOCK_PERFORMANCE_DATA}
          currency={currency}
          dateRange={dateRange}
        />

        {/* Two Column Layout for Allocation and Income */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Allocation Analysis */}
          <AllocationAnalysis data={MOCK_ALLOCATION_DATA} currency={currency} />

          {/* Income Analysis */}
          <IncomeAnalysis data={MOCK_INCOME_DATA} currency={currency} />
        </div>
      </div>
    </PageContainer>
  );
}
