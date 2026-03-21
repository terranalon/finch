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
import { cn, api } from '../lib';
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
  const hasHandledSymbolParam = useRef(false);

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

  // Fetch data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
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

  // Reset filters on currency change
  useEffect(() => { setFiltersInitialized(false); }, [currency]);

  // Reset page on filter change
  useEffect(() => { setCurrentPage(1); }, [searchQuery, selectedAccounts, selectedClasses, selectedSectors]);

  // URL ?symbol= pre-selection
  const pendingSymbolRef = useRef(null);
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
    let result = positions.filter((p) => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!p.symbol.toLowerCase().includes(q) && !p.name?.toLowerCase().includes(q)) return false;
      }
      if (selectedAccounts.length > 0 && selectedAccounts.length < accounts.length) {
        if (!p.accounts.some((a) => selectedAccounts.includes(a.account_id))) return false;
      } else if (selectedAccounts.length === 0) return false;
      if (selectedClasses.length > 0 && selectedClasses.length < assetClasses.length) {
        if (!selectedClasses.includes(p.asset_class)) return false;
      } else if (selectedClasses.length === 0) return false;
      if (selectedSectors.length > 0 && selectedSectors.length < sectors.length) {
        if (!selectedSectors.includes(p.category)) return false;
      } else if (selectedSectors.length === 0) return false;
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
    const result = filteredPositions.reduce(
      (acc, p) => ({
        costBasis: acc.costBasis + (p.total_cost_basis_native || 0),
        marketValue: acc.marketValue + (p.total_market_value_native || 0),
        pnl: acc.pnl + (p.total_pnl_native || 0),
      }),
      { costBasis: 0, marketValue: 0, pnl: 0 }
    );
    result.pnlPct = result.costBasis > 0 ? (result.pnl / result.costBasis) * 100 : 0;
    return result;
  }, [filteredPositions]);

  const handleSort = useCallback((field) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortDirection('desc');
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
                  {['', '', '', 'Symbol', 'Name', 'Price', 'Qty', 'Avg Cost', 'Cost Basis', 'Value', 'P&L', 'Accts'].map((h, i) => (
                    <th key={i} className={cn('table-header', i >= 5 && 'text-right', i === 11 && 'text-center')}>{h}</th>
                  ))}
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
