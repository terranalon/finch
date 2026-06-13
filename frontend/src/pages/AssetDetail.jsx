import { useParams, useNavigate, Link } from 'react-router-dom';
import { PageContainer } from '../components/Layout';
import { SkeletonHero, SkeletonChart, SkeletonCard } from '../components/ui/Skeleton';
import { useAssetDetailData } from '../hooks/useAssetDetailData';
import {
  AssetHero,
  PositionStrip,
  AssetChart,
  AssetStatsGrid,
  AssetAbout,
  AssetDividend,
  RecentActivity,
} from '../components/asset-detail';

export default function AssetDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const {
    asset,
    position,
    recentActivity,
    activityCount,
    priceHistory,
    chartPeriod,
    loading,
    error,
    currency,
    setChartPeriod,
    toggleFavorite,
    refreshPrice,
  } = useAssetDetailData(id);

  if (loading) {
    return (
      <PageContainer>
        <SkeletonHero />
        <SkeletonChart className="mt-6" />
        <SkeletonCard className="mt-6" />
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">{error}</h2>
          <p className="text-sm text-[var(--text-secondary)] mb-6">
            The asset you requested could not be loaded.
          </p>
          <button onClick={() => navigate('/assets')} className="btn btn-primary">
            Back to Assets
          </button>
        </div>
      </PageContainer>
    );
  }

  const showDividend = asset.daily_metrics?.dividend_yield != null && asset.asset_class !== 'Crypto';

  return (
    <PageContainer>
      <nav className="mb-4 flex items-center gap-2 text-sm text-[var(--text-secondary)]">
        <Link to="/assets" className="hover:text-[var(--text-primary)]">Assets</Link>
        <span>/</span>
        <span className="text-[var(--text-primary)] font-medium">{asset.symbol}</span>
      </nav>

      <AssetHero asset={asset} onToggleFavorite={toggleFavorite} onRefreshPrice={refreshPrice} />

      {position && <PositionStrip position={position} asset={asset} />}

      <div className="mt-6 flex flex-col lg:flex-row gap-6 items-start">
        {/* Left column: market data */}
        <div className="flex-1 min-w-0 flex flex-col gap-6 w-full">
          <AssetChart
            priceHistory={priceHistory}
            activePeriod={chartPeriod}
            onPeriodChange={setChartPeriod}
            currency={asset.currency}
          />
          <AssetStatsGrid asset={asset} />
        </div>

        {/* Right column: activity + about + dividend */}
        <aside className="w-full lg:w-[420px] lg:flex-shrink-0 flex flex-col gap-6">
          <RecentActivity activity={recentActivity} activityCount={activityCount} currency={currency} />
          <AssetAbout asset={asset} />
          {showDividend && <AssetDividend asset={asset} position={position} />}
        </aside>
      </div>
    </PageContainer>
  );
}
