import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api, cn } from '../lib';
import { PageContainer } from '../components/Layout';
import { SkeletonHero, SkeletonChart, SkeletonCard } from '../components/ui/Skeleton';
import AssetHero from '../components/asset-detail/AssetHero';
import PositionStrip from '../components/asset-detail/PositionStrip';
import AssetChart from '../components/asset-detail/AssetChart';

const TABS = ['Overview', 'Transactions'];

export default function AssetDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [asset, setAsset] = useState(null);
  const [position, setPosition] = useState(null);
  const [trades, setTrades] = useState([]);
  const [dividends, setDividends] = useState([]);
  const [priceHistory, setPriceHistory] = useState(null);
  const [chartPeriod, setChartPeriod] = useState('1y');
  const [activeTab, setActiveTab] = useState('Overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadAsset() {
      setLoading(true);
      setError(null);

      // Step 1: fetch asset detail (gates all subsequent calls)
      let assetData;
      try {
        const res = await api(`/assets/${id}/detail`);
        if (!res.ok) {
          if (res.status === 404) {
            setError('Asset not found');
          } else {
            setError('Failed to load asset');
          }
          setLoading(false);
          return;
        }
        assetData = await res.json();
        setAsset(assetData);
      } catch {
        setError('Failed to load asset. Please try again.');
        setLoading(false);
        return;
      }

      // Step 2: fan out to secondary endpoints in parallel
      const symbol = assetData.symbol;
      const [posRes, tradesRes, dividendsRes, pricesRes] = await Promise.allSettled([
        api(`/positions?limit=100&display_currency=USD`).then((r) => r.json()),
        api(`/transactions/trades?symbol=${symbol}&limit=500`).then((r) => r.json()),
        api(`/transactions/dividends?symbol=${symbol}&limit=500`).then((r) => r.json()),
        api(`/prices/historical/${symbol}?period=${chartPeriod}`).then((r) => r.json()),
      ]);

      if (posRes.status === 'fulfilled') {
        const allPositions = posRes.value.items || [];
        const match = allPositions.find((p) => p.asset_id === assetData.id) || null;
        setPosition(match);
      }
      if (tradesRes.status === 'fulfilled') {
        setTrades(tradesRes.value.items || []);
      }
      if (dividendsRes.status === 'fulfilled') {
        setDividends(dividendsRes.value.items || []);
      }
      if (pricesRes.status === 'fulfilled') {
        setPriceHistory(pricesRes.value);
      }

      setLoading(false);
    }

    loadAsset();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePeriodChange = useCallback((period) => {
    setChartPeriod(period);
  }, []);

  const handleToggleFavorite = useCallback(async () => {
    if (!asset) return;
    const res = await api(`/assets/${asset.id}/favorite`, { method: 'PUT' });
    if (res.ok) {
      setAsset((prev) => ({ ...prev, is_favorite: !prev.is_favorite }));
    }
  }, [asset]);

  const handleRefreshPrice = useCallback(async () => {
    if (!asset) return;
    const res = await api(`/assets/${asset.id}/price`, { method: 'PATCH' });
    if (res.ok) {
      const data = await res.json();
      setAsset((prev) => ({
        ...prev,
        last_fetched_price: data.last_fetched_price,
        last_fetched_at: data.last_fetched_at,
      }));
    }
  }, [asset]);

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
          <button
            onClick={() => navigate('/assets')}
            className="btn btn-primary"
          >
            Back to Assets
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Breadcrumb */}
      <nav className="mb-4 flex items-center gap-2 text-sm text-[var(--text-secondary)]">
        <Link to="/assets" className="hover:text-[var(--text-primary)]">Assets</Link>
        <span>/</span>
        <span className="text-[var(--text-primary)] font-medium">{asset.symbol}</span>
      </nav>

      <AssetHero asset={asset} onToggleFavorite={handleToggleFavorite} onRefreshPrice={handleRefreshPrice} />

      {position && <PositionStrip position={position} asset={asset} />}

      {/* Content tabs */}
      <div className="flex gap-6 border-b border-[var(--border-primary)] mb-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'pb-3 text-sm border-b-2 -mb-px transition-colors',
              activeTab === tab
                ? 'border-[var(--accent)] text-[var(--text-primary)] font-semibold'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      <AssetChart
        priceHistory={priceHistory}
        activePeriod={chartPeriod}
        onPeriodChange={handlePeriodChange}
        currency={asset.currency}
      />

      {/* Tab content */}
      {activeTab === 'Overview' && (
        <div>
          {/* Stats grid placeholder - Task 5 */}
          {/* About / dividend section placeholder - Tasks 6-7 */}
        </div>
      )}

      {activeTab === 'Transactions' && (
        <div>
          {/* Transactions table - Task 8 */}
        </div>
      )}
    </PageContainer>
  );
}
