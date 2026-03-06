import { useDashboardData } from '../hooks/useDashboardData';
import { Skeleton } from '../components/ui';

export default function DashboardPage() {
  const { summary, snapshots, cashFlows, loading, error, currency } = useDashboardData();

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
        {/* SummaryStrip */}
        <div className="mb-5 pb-[18px] border-b border-[var(--border-primary)]">
          {loading ? (
            <Skeleton className="h-16 w-full" />
          ) : (
            <p className="text-3xl font-bold font-mono tabular-nums">
              Summary Strip placeholder
            </p>
          )}
        </div>

        {/* ChartCard */}
        <div className="card mb-5">
          {loading ? <Skeleton className="h-[280px] w-full" /> : <p>Chart Card placeholder</p>}
        </div>

        {/* AccountStrip */}
        <div className="mb-5">Account Strip placeholder</div>

        {/* TopHoldingsTable */}
        <div className="card mb-5">Top Holdings placeholder</div>

        {/* AssetExplorerCard */}
        <div className="card">Asset Explorer placeholder</div>
      </div>

      {/* Right Column */}
      <div className="w-[340px] min-w-[340px] flex-shrink-0 p-5 pl-0 flex flex-col gap-3.5 overflow-y-auto h-full [scrollbar-width:thin]">
        <div className="card flex-1 min-h-0 overflow-y-auto">Market Pulse placeholder</div>
        <div className="card flex-1 min-h-0 overflow-y-auto">Recent Activity placeholder</div>
      </div>
    </div>
  );
}
