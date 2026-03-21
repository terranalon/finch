import { useState, useCallback } from 'react';
import { useDashboardData } from '../hooks/useDashboardData';
import {
  SummaryStrip,
  ChartCard,
  AccountStrip,
  TopHoldingsTable,
  AssetExplorerCard,
  MarketPulseCard,
  RecentActivityCard,
  AllocationDonutCard,
  AssetDetailSidebar,
} from '../components/dashboard';
import { TransactionDetailSidebar } from '../components/transactions';
import { transformTrade } from '../lib';

export default function DashboardPage() {
  const { summary, snapshots, cashFlows, loading, error, currency } = useDashboardData();
  const [sidebarAsset, setSidebarAsset] = useState(null);
  const [sidebarTrade, setSidebarTrade] = useState(null);

  // Shared favorite state: maps assetId -> overridden is_favorite value
  const [favoriteOverrides, setFavoriteOverrides] = useState({});

  const handleFavoriteToggle = useCallback((assetId, newValue) => {
    setFavoriteOverrides((prev) => ({ ...prev, [assetId]: newValue }));
  }, []);

  const handleAssetClick = (asset) => setSidebarAsset(asset);
  const handleCloseSidebar = () => setSidebarAsset(null);

  const handleTradeClick = (trade) => setSidebarTrade(transformTrade(trade));
  const handleCloseTradePanel = () => setSidebarTrade(null);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-secondary)]">
        Failed to load dashboard: {error}
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left Column – 75% */}
      <div className="w-3/4 overflow-y-auto p-5 min-w-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <SummaryStrip
          summary={summary}
          snapshots={snapshots}
          loading={loading}
          currency={currency}
        />

        <ChartCard
          snapshots={snapshots}
          cashFlows={cashFlows}
          summary={summary}
          currency={currency}
          loading={loading}
        />

        <AccountStrip
          accounts={summary?.accounts}
          loading={loading}
          currency={currency}
        />

        <TopHoldingsTable
          holdings={summary?.top_holdings}
          totalValue={summary?.total_value || 0}
          loading={loading}
          currency={currency}
          onAssetClick={handleAssetClick}
          favoriteOverrides={favoriteOverrides}
          onFavoriteToggle={handleFavoriteToggle}
        />

        <AssetExplorerCard
          onAssetClick={handleAssetClick}
          favoriteOverrides={favoriteOverrides}
          onFavoriteToggle={handleFavoriteToggle}
        />
      </div>

      {/* Right Column – 25% */}
      <div className="w-1/4 min-w-[280px] p-5 pl-0 flex flex-col gap-3.5 overflow-y-auto h-full [scrollbar-width:thin]">
        <MarketPulseCard />

        <RecentActivityCard onTradeClick={handleTradeClick} />

        <AllocationDonutCard
          allocation={summary?.asset_allocation}
          totalValue={summary?.total_value}
          currency={currency}
          loading={loading}
        />
      </div>

      {/* Asset Detail Slide-Over */}
      <AssetDetailSidebar
        asset={sidebarAsset}
        isOpen={!!sidebarAsset}
        onClose={handleCloseSidebar}
      />

      {/* Trade Detail Slide-Over */}
      <TransactionDetailSidebar
        transaction={sidebarTrade}
        currency={currency}
        onClose={handleCloseTradePanel}
      />
    </div>
  );
}
