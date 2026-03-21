/**
 * Holdings Page
 *
 * Detailed view of all positions with per-account drill-down.
 *
 * API endpoints:
 * - GET /api/positions?display_currency={currency}&portfolio_id={pid}
 * - GET /api/accounts?is_active=true&portfolio_id={pid}
 */

import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib';
import { useCurrency, usePortfolio } from '../contexts';
import { PageContainer } from '../components/layout';
import { Card, Skeleton, SkeletonTableRow } from '../components/ui';
import { AssetDetailSidebar } from '../components/dashboard';
import { toAssetClickPayload } from '../components/dashboard/shared';
import { HoldingsFilterBar, HoldingsTable, PaginationFooter } from '../components/holdings';

export default function Holdings() {
  const { currency } = useCurrency();
  const { selectedPortfolioId } = usePortfolio();
  const [searchParams, setSearchParams] = useSearchParams();

  // Data state
  const [positions, setPositions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // URL ?symbol= deep-link refs
  const hasHandledSymbolParam = useRef(false);
  const pendingSymbolRef = useRef(null);

  // Filter options derived from data
  const assetClasses = useMemo(() => {
    return [...new Set(positions.map((p) => p.asset_class).filter(Boolean))].sort();
  }, [positions]);

  const sectors = useMemo(() => {
    return [...new Set(positions.map((p) => p.category).filter(Boolean))].sort();
  }, [positions]);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAccounts, setSelectedAccounts] = useState([]);
  const [selectedClasses, setSelectedClasses] = useState([]);
  const [selectedSectors, setSelectedSectors] = useState([]);
  const [filtersInitialized, setFiltersInitialized] = useState(false);

  // Sort state
  const [sortField, setSortField] = useState('total_market_value_native');
  const [sortDirection, setSortDirection] = useState('desc');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  // Expanded rows
  const [expandedRows, setExpandedRows] = useState(new Set());

  // Asset sidebar
  const [sidebarAsset, setSidebarAsset] = useState(null);

  // Fetch data (also resets filter state so filters re-initialize from fresh data)
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      setFiltersInitialized(false);
      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';
      try {
        const [posRes, accRes] = await Promise.all([
          api(`/positions?display_currency=${currency}${portfolioParam}`),
          api(`/accounts?is_active=true${portfolioParam}`),
        ]);
        if (!posRes.ok) throw new Error(`Failed to fetch positions: ${posRes.statusText}`);
        if (!accRes.ok) throw new Error(`Failed to fetch accounts: ${accRes.statusText}`);
        const [posData, accData] = await Promise.all([posRes.json(), accRes.json()]);
        setPositions(posData.items);
        setAccounts(accData.items);
      } catch (err) {
        console.error('Error fetching holdings data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [currency, selectedPortfolioId]);

  // Initialize filters when data loads
  useEffect(() => {
    if (!loading && positions.length > 0 && accounts.length > 0 && !filtersInitialized) {
      setSelectedAccounts(accounts.map((a) => a.id));
      setSelectedClasses([...assetClasses]);
      setSelectedSectors([...sectors]);
      setFiltersInitialized(true);
    }
  }, [loading, positions, accounts, assetClasses, sectors, filtersInitialized]);

  // Reset page on filter change
  useEffect(() => { setCurrentPage(1); }, [searchQuery, selectedAccounts, selectedClasses, selectedSectors]);

  // URL ?symbol= pre-selection: open sidebar and scroll to row
  useEffect(() => {
    const symbol = searchParams.get('symbol');
    if (symbol && positions.length > 0 && !hasHandledSymbolParam.current) {
      hasHandledSymbolParam.current = true;
      pendingSymbolRef.current = symbol;
      const pos = positions.find((p) => p.symbol === symbol);
      if (pos) {
        setSidebarAsset(toAssetClickPayload(pos));
        setSearchParams({}, { replace: true });
      }
    }
  }, [positions, searchParams, setSearchParams]);

  // Favorite toggle with optimistic update + API call
  const toggleFavorite = useCallback((assetId) => {
    setPositions((prev) =>
      prev.map((p) => (p.asset_id === assetId ? { ...p, is_favorite: !p.is_favorite } : p))
    );
    api(`/assets/${assetId}/favorite`, { method: 'PUT' }).catch(() => {
      // Revert on failure
      setPositions((prev) =>
        prev.map((p) => (p.asset_id === assetId ? { ...p, is_favorite: !p.is_favorite } : p))
      );
    });
  }, []);

  // Sync favorite changes from sidebar back to table
  const handleSidebarFavoriteToggle = useCallback((assetId, newValue) => {
    setPositions((prev) =>
      prev.map((p) => (p.asset_id === assetId ? { ...p, is_favorite: newValue } : p))
    );
  }, []);

  // Clear all filters
  const clearAllFilters = useCallback(() => {
    setSearchQuery('');
    setSelectedAccounts(accounts.map((a) => a.id));
    setSelectedClasses([...assetClasses]);
    setSelectedSectors([...sectors]);
  }, [accounts, assetClasses, sectors]);

  // Filter + sort
  const filteredPositions = useMemo(() => {
    // When all items are selected, skip the filter check (nothing is excluded).
    // When none are selected, exclude everything.
    const isAccountFiltered = selectedAccounts.length > 0 && selectedAccounts.length < accounts.length;
    const isClassFiltered = selectedClasses.length > 0 && selectedClasses.length < assetClasses.length;
    const isSectorFiltered = selectedSectors.length > 0 && selectedSectors.length < sectors.length;
    const hasEmptyFilter = selectedAccounts.length === 0 || selectedClasses.length === 0 || selectedSectors.length === 0;

    let result = hasEmptyFilter ? [] : positions.filter((p) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!p.symbol.toLowerCase().includes(q) && !p.name?.toLowerCase().includes(q)) return false;
      }
      if (isAccountFiltered && !p.accounts.some((a) => selectedAccounts.includes(a.account_id))) return false;
      if (isClassFiltered && !selectedClasses.includes(p.asset_class)) return false;
      if (isSectorFiltered && !selectedSectors.includes(p.category)) return false;
      return true;
    });

    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'string') {
        return sortDirection === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });

    return result;
  }, [positions, searchQuery, selectedAccounts, selectedClasses, selectedSectors, sortField, sortDirection, accounts.length, assetClasses.length, sectors.length]);

  // Navigate to page containing symbol from URL param
  useEffect(() => {
    if (pendingSymbolRef.current && filteredPositions.length > 0) {
      const symbol = pendingSymbolRef.current;
      const index = filteredPositions.findIndex((p) => p.symbol === symbol);
      if (index !== -1) {
        const targetPage = Math.floor(index / pageSize) + 1;
        if (targetPage !== currentPage) {
          setCurrentPage(targetPage);
        } else {
          setTimeout(() => {
            const row = document.getElementById(`holdings-row-${filteredPositions[index].asset_id}`);
            if (row) row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            pendingSymbolRef.current = null;
          }, 100);
        }
      } else {
        pendingSymbolRef.current = null;
      }
    }
  }, [filteredPositions, currentPage, pageSize]);

  // Totals from ALL filtered positions (not just current page)
  const totals = useMemo(() => {
    const { costBasis, marketValue, pnl } = filteredPositions.reduce(
      (acc, p) => ({
        costBasis: acc.costBasis + (p.total_cost_basis_native || 0),
        marketValue: acc.marketValue + (p.total_market_value_native || 0),
        pnl: acc.pnl + (p.total_pnl_native || 0),
      }),
      { costBasis: 0, marketValue: 0, pnl: 0 }
    );
    const pnlPct = costBasis > 0 ? (pnl / costBasis) * 100 : 0;
    return { costBasis, marketValue, pnl, pnlPct };
  }, [filteredPositions]);

  const handleSort = useCallback((field) => {
    setSortField((prev) => {
      if (prev === field) setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
      else setSortDirection('desc');
      return field;
    });
  }, []);

  const toggleExpand = useCallback((assetId) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(assetId)) next.delete(assetId);
      else next.add(assetId);
      return next;
    });
  }, []);

  const handleRowClick = useCallback((position) => {
    setSidebarAsset(toAssetClickPayload(position));
  }, []);

  // Current page slice
  const pagedPositions = filteredPositions.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Loading skeleton
  if (loading) {
    return (
      <PageContainer width="wide">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-8 w-32" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-9 w-64" />
            <Skeleton className="h-9 w-9" />
          </div>
        </div>
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="table-header" />
                  <th className="table-header" />
                  <th className="table-header" />
                  <th className="table-header">Symbol</th>
                  <th className="table-header">Name</th>
                  <th className="table-header text-right">Price</th>
                  <th className="table-header text-right">Qty</th>
                  <th className="table-header text-right">Avg Cost</th>
                  <th className="table-header text-right">Cost Basis</th>
                  <th className="table-header text-right">Value</th>
                  <th className="table-header text-right">P&L</th>
                  <th className="table-header text-center">Accts</th>
                </tr>
              </thead>
              <tbody>
                {[1, 2, 3, 4, 5].map((i) => (
                  <SkeletonTableRow key={i} columns={12} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </PageContainer>
    );
  }

  // Error state
  if (error) {
    return (
      <PageContainer width="wide">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)] mb-4">Holdings</h1>
        <Card>
          <div className="py-12 text-center">
            <p className="text-negative mb-2">Error loading holdings</p>
            <p className="text-[var(--text-secondary)] text-sm">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-hover transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer width="wide">
      {/* Title bar with search + filter */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Holdings</h1>
        <HoldingsFilterBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          accounts={accounts}
          selectedAccounts={selectedAccounts}
          onAccountsChange={setSelectedAccounts}
          assetClasses={assetClasses}
          selectedClasses={selectedClasses}
          onClassesChange={setSelectedClasses}
          sectors={sectors}
          selectedSectors={selectedSectors}
          onSectorsChange={setSelectedSectors}
          onClearAll={clearAllFilters}
        />
      </div>

      <Card>
        <HoldingsTable
          positions={pagedPositions}
          expandedRows={expandedRows}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={handleSort}
          onToggleExpand={toggleExpand}
          onRowClick={handleRowClick}
          onToggleFavorite={toggleFavorite}
          totals={totals}
          currency={currency}
          emptyMessage={positions.length === 0 ? 'No holdings found' : 'No holdings match your filters'}
          onClearFilters={positions.length > 0 ? clearAllFilters : undefined}
        />

        {filteredPositions.length > 0 && (
          <PaginationFooter
            currentPage={currentPage}
            totalItems={filteredPositions.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={(size) => { setPageSize(size); setCurrentPage(1); }}
          />
        )}
      </Card>

      <AssetDetailSidebar
        asset={sidebarAsset}
        isOpen={!!sidebarAsset}
        onClose={() => setSidebarAsset(null)}
        onFavoriteToggle={handleSidebarFavoriteToggle}
      />
    </PageContainer>
  );
}
