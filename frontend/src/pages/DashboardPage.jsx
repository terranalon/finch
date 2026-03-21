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
  TradeDetailSidebar,
} from '../components/dashboard';

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

  const handleTradeClick = (trade) => setSidebarTrade(trade);
  const handleCloseTradePanel = () => setSidebarTrade(null);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-secondary)]">
        Failed to load dashboard: {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col min-[900px]:flex-row h-full min-[900px]:overflow-hidden">
      {/* Left Column */}
      <div className="min-[900px]:flex-1 min-[900px]:overflow-y-auto p-5 min-w-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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

      {/* Right Column */}
      <div className="px-5 pb-5 min-[900px]:py-5 min-[900px]:pr-5 min-[900px]:pl-0 min-[900px]:w-[300px] min-[900px]:shrink-0 flex flex-col gap-3.5 min-[900px]:overflow-y-auto min-[900px]:h-full [scrollbar-width:thin]">
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
      <TradeDetailSidebar
        trade={sidebarTrade}
        isOpen={!!sidebarTrade}
        onClose={handleCloseTradePanel}
        currency={currency}
      />
    </div>
  );
}
