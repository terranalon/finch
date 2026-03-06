import { useState } from 'react';
import { useDashboardData } from '../hooks/useDashboardData';
import {
  SummaryStrip,
  ChartCard,
  AccountStrip,
  TopHoldingsTable,
  AssetExplorerCard,
  MarketPulseCard,
  RecentActivityCard,
  MoversCard,
  AssetDetailSidebar,
} from '../components/dashboard';

export default function DashboardPage() {
  const { summary, snapshots, cashFlows, loading, error, currency } = useDashboardData();
  const [sidebarAsset, setSidebarAsset] = useState(null);

  const handleAssetClick = (asset) => setSidebarAsset(asset);
  const handleCloseSidebar = () => setSidebarAsset(null);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-[var(--text-secondary)]">
        Failed to load dashboard: {error}
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left Column */}
      <div className="flex-1 overflow-y-auto p-5 min-w-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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
        />

        <AssetExplorerCard onAssetClick={handleAssetClick} />
      </div>

      {/* Right Column */}
      <div className="w-[340px] min-w-[340px] flex-shrink-0 p-5 pl-0 flex flex-col gap-3.5 overflow-y-auto h-full [scrollbar-width:thin]">
        <MarketPulseCard />

        <div className="card flex-1 min-h-0 overflow-y-auto">
          <RecentActivityCard />
        </div>

        <div className="card">
          <MoversCard onAssetClick={handleAssetClick} />
        </div>
      </div>

      {/* Asset Detail Slide-Over */}
      <AssetDetailSidebar
        asset={sidebarAsset}
        isOpen={!!sidebarAsset}
        onClose={handleCloseSidebar}
      />
    </div>
  );
}
