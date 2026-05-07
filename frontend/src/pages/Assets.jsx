import { useState, useMemo, useEffect } from 'react';
import { useAssetsData } from '../hooks/useAssetsData';
import { PageContainer } from '../components/layout';
import { Skeleton } from '../components/ui';
import { AssetClassTabs, AssetsFilterRow, AssetsTable, PERIOD_KEYS } from '../components/assets';
import { AssetDetailSidebar } from '../components/dashboard';

function getSortValue(asset, sortKey, periodKeys, positionMap) {
  switch (sortKey) {
    case 'symbol': return asset.symbol?.toLowerCase() || '';
    case 'price': return asset.last_fetched_price ?? -Infinity;
    case 'changePct': return asset[periodKeys.pct] ?? -Infinity;
    case 'marketCap': return positionMap.get(asset.id)?.market_cap ?? -Infinity;
    case 'volume': return -Infinity;
    default: return 0;
  }
}

export default function Assets() {
  const { assets, positionMap, loading, error, currency, toggleFavorite, syncFavorite } = useAssetsData();

  const [activeTab, setActiveTab] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPeriod, setSelectedPeriod] = useState('1d');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [sortConfig, setSortConfig] = useState({ key: 'symbol', direction: 'asc' });
  const [sidebarAsset, setSidebarAsset] = useState(null);

  useEffect(() => {
    setSearchQuery('');
    setShowFavoritesOnly(false);
  }, [activeTab]);

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const handleRowClick = (asset) => {
    setSidebarAsset({
      id: asset.id,
      symbol: asset.symbol,
      name: asset.name,
      asset_class: asset.asset_class,
      current_price: asset.last_fetched_price,
      day_change_pct: asset.change_1d_pct,
      currency: asset.currency,
    });
  };

  const { filteredAssets, totalCount, favoritesCount } = useMemo(() => {
    const periodKeys = PERIOD_KEYS[selectedPeriod] || PERIOD_KEYS['1d'];
    const query = searchQuery.toLowerCase();

    // Single pass to compute tab count, favorites count, and filtered list
    const filtered = [];
    let tabCount = 0;
    let favCount = 0;
    for (const a of assets) {
      const inTab = activeTab === 'All' || a.asset_class === activeTab;
      if (inTab) tabCount++;
      if (a.is_favorite) favCount++;

      if (!inTab) continue;
      if (showFavoritesOnly && !a.is_favorite) continue;
      if (query) {
        const matchSymbol = a.symbol?.toLowerCase().includes(query);
        const matchName = a.name?.toLowerCase().includes(query);
        if (!matchSymbol && !matchName) continue;
      }
      filtered.push(a);
    }

    const sorted = [...filtered].sort((a, b) => {
      const va = getSortValue(a, sortConfig.key, periodKeys, positionMap);
      const vb = getSortValue(b, sortConfig.key, periodKeys, positionMap);
      if (typeof va === 'string') {
        return sortConfig.direction === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      }
      return sortConfig.direction === 'asc' ? va - vb : vb - va;
    });

    return { filteredAssets: sorted, totalCount: tabCount, favoritesCount: favCount };
  }, [assets, activeTab, searchQuery, selectedPeriod, showFavoritesOnly, sortConfig, positionMap]);

  if (loading) {
    return (
      <PageContainer className="mx-0 max-w-none">
        <div className="mb-5">
          <Skeleton className="h-7 w-24 mb-1" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-10 w-full mb-4 rounded-[10px]" />
        <div className="flex items-center gap-2.5 mb-4">
          <Skeleton className="h-9 w-[240px]" />
          <div className="flex-1" />
          <Skeleton className="h-9 w-32" />
          <Skeleton className="h-9 w-28" />
        </div>
        <AssetsTable
          assets={[]}
          positionMap={new Map()}
          period="1d"
          currency={currency}
          sortConfig={sortConfig}
          onSort={() => {}}
          onRowClick={() => {}}
          onToggleFavorite={() => {}}
          loading={true}
          totalCount={0}
          favoritesCount={0}
        />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer className="mx-0 max-w-none">
        <h1 className="text-[22px] font-bold tracking-[-0.3px] text-[var(--text-primary)] mb-5">Assets</h1>
        <div className="text-center py-12">
          <p className="text-[var(--negative)] mb-2">Error loading assets</p>
          <p className="text-[var(--text-secondary)] text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90 transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer className="mx-0 max-w-none">
      <div className="mb-5">
        <h1 className="text-[22px] font-bold tracking-[-0.3px] text-[var(--text-primary)]">Assets</h1>
        <p className="text-[13px] text-[var(--text-tertiary)] mt-0.5">
          {filteredAssets.length} asset{filteredAssets.length !== 1 ? 's' : ''}
        </p>
      </div>

      <AssetClassTabs
        assets={assets}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <AssetsFilterRow
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedPeriod={selectedPeriod}
        onPeriodChange={setSelectedPeriod}
        showFavoritesOnly={showFavoritesOnly}
        onFavoritesToggle={() => setShowFavoritesOnly((v) => !v)}
      />

      <AssetsTable
        assets={filteredAssets}
        positionMap={positionMap}
        period={selectedPeriod}
        currency={currency}
        sortConfig={sortConfig}
        onSort={handleSort}
        onRowClick={handleRowClick}
        onToggleFavorite={toggleFavorite}
        loading={false}
        totalCount={totalCount}
        favoritesCount={favoritesCount}
      />

      <AssetDetailSidebar
        asset={sidebarAsset}
        isOpen={!!sidebarAsset}
        onClose={() => setSidebarAsset(null)}
        onFavoriteToggle={syncFavorite}
      />
    </PageContainer>
  );
}
