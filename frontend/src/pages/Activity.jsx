import { useState, useMemo, useEffect } from 'react';
import { useActivityData } from '../hooks/useActivityData';
import { PageContainer, PageHeader } from '../components/layout';
import { Skeleton } from '../components/ui';
import {
  ActivityTimeline,
  TransactionDetailPanel,
  DateRangeFilter,
  FilterPopover,
  PaginationFooter,
} from '../components/activity';
import { SearchIcon } from '../components/activity/icons';

const TRANSACTION_TYPES = ['Trade', 'Dividend', 'Forex', 'Cash'];

const TYPE_MAP = { trade: 'Trade', dividend: 'Dividend', forex: 'Forex', cash: 'Cash' };

const PRESET_DAYS = { '7d': 7, '30d': 30, '90d': 90 };

function getDateCutoff(dateRange) {
  if (dateRange.type === 'custom' && dateRange.startDate && dateRange.endDate) {
    return { start: new Date(dateRange.startDate), end: new Date(dateRange.endDate) };
  }
  if (dateRange.type !== 'preset' || dateRange.preset === 'all') return null;

  const now = new Date();
  if (dateRange.preset === 'ytd') {
    return { start: new Date(now.getFullYear(), 0, 1), end: null };
  }
  const days = PRESET_DAYS[dateRange.preset];
  if (!days) return null;
  const cutoff = new Date(now);
  cutoff.setDate(cutoff.getDate() - days);
  return { start: cutoff, end: null };
}

function isWithinDateRange(txDate, cutoff) {
  if (!cutoff) return true;
  if (txDate < cutoff.start) return false;
  if (cutoff.end && txDate > cutoff.end) return false;
  return true;
}

export default function Activity() {
  const { transactions, accounts, loading, error, currency } = useActivityData();

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [excludedTypes, setExcludedTypes] = useState(new Set());
  const [excludedAccounts, setExcludedAccounts] = useState(new Set());
  const [dateRange, setDateRange] = useState({ type: 'preset', preset: 'all', label: 'All Time' });

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Detail panel
  const [selectedTransaction, setSelectedTransaction] = useState(null);

  // Filter + paginate + group
  const { groupedTransactions, filteredCount, totalCount, totalPages } = useMemo(() => {
    const accountIdByName = new Map(accounts.map((a) => [a.name, a.id]));
    const dateCutoff = getDateCutoff(dateRange);
    const query = searchQuery.toLowerCase();

    const filtered = transactions.filter((tx) => {
      if (excludedTypes.has(TYPE_MAP[tx.type])) return false;

      const accountId = accountIdByName.get(tx.account_name);
      if (accountId && excludedAccounts.has(accountId)) return false;

      if (query) {
        const matchesSymbol = tx.symbol?.toLowerCase().includes(query);
        const matchesName = tx.name?.toLowerCase().includes(query);
        if (!matchesSymbol && !matchesName) return false;
      }

      if (!isWithinDateRange(new Date(tx.date), dateCutoff)) return false;

      return true;
    });

    const startIndex = (currentPage - 1) * pageSize;
    const paginated = filtered.slice(startIndex, startIndex + pageSize);

    const grouped = {};
    for (const tx of paginated) {
      if (!grouped[tx.date]) grouped[tx.date] = [];
      grouped[tx.date].push(tx);
    }

    return {
      groupedTransactions: grouped,
      filteredCount: filtered.length,
      totalCount: transactions.length,
      totalPages: Math.ceil(filtered.length / pageSize),
    };
  }, [transactions, searchQuery, excludedTypes, excludedAccounts, dateRange, currentPage, pageSize, accounts]);

  // Reset page on filter change
  useEffect(() => { setCurrentPage(1); }, [searchQuery, excludedTypes, excludedAccounts, dateRange]);

  if (loading) {
    return (
      <PageContainer className="mx-0 max-w-none">
        <PageHeader title="Activity" />
        <div className="flex flex-col lg:flex-row gap-4 mb-6">
          <Skeleton className="h-9 w-64" />
          <div className="flex gap-3 ml-auto">
            <Skeleton className="h-9 w-28" />
            <Skeleton className="h-9 w-9" />
          </div>
        </div>
        <div className="space-y-8">
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="flex items-center gap-3 mb-4">
                <Skeleton className="w-2 h-2 rounded-full" />
                <Skeleton className="h-3 w-48" />
              </div>
              <div className="ml-4 pl-4 border-l-2 border-[var(--border-primary)] flex flex-col gap-[10px]">
                {[1, 2].map((j) => <Skeleton key={j} className="h-[72px] w-full rounded-lg" />)}
              </div>
            </div>
          ))}
        </div>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer className="mx-0 max-w-none">
        <PageHeader title="Activity" />
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
    <PageContainer className="mx-0 max-w-none">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-[22px] font-bold tracking-[-0.3px] text-[var(--text-primary)]">Activity</h1>
        <div className="flex items-center gap-[10px]">
          <div className="relative w-[260px]">
            <SearchIcon className="absolute left-[10px] top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-faint)] pointer-events-none" />
            <input
              type="text"
              placeholder="Search by symbol or name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full py-2 pl-[34px] pr-3 bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-faint)] focus:outline-none focus:border-accent transition-colors"
            />
          </div>
          <DateRangeFilter value={dateRange} onChange={setDateRange} />
          <FilterPopover
            types={TRANSACTION_TYPES}
            excludedTypes={excludedTypes}
            onTypesChange={setExcludedTypes}
            accounts={accounts}
            excludedAccounts={excludedAccounts}
            onAccountsChange={setExcludedAccounts}
          />
        </div>
      </div>

      <ActivityTimeline
        groupedTransactions={groupedTransactions}
        currency={currency}
        onTransactionClick={setSelectedTransaction}
      />

      <PaginationFooter
        currentPage={currentPage}
        totalPages={totalPages}
        pageSize={pageSize}
        filteredCount={filteredCount}
        totalCount={totalCount}
        onPageChange={setCurrentPage}
        onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(1); }}
      />

      <TransactionDetailPanel
        transaction={selectedTransaction}
        currency={currency}
        onClose={() => setSelectedTransaction(null)}
      />
    </PageContainer>
  );
}
