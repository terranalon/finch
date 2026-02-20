import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api, cn, formatCurrency, formatDate, formatNumber } from '../lib';
import { PageContainer } from '../components/Layout';
import { SkeletonHero, SkeletonChart, SkeletonCard } from '../components/ui/Skeleton';
import { Card } from '../components/ui/Card';
import { NoTransactionsEmpty } from '../components/ui/EmptyState';
import { TransactionBadge } from '../components/ui/Badge';
import AssetHero from '../components/asset-detail/AssetHero';
import PositionStrip from '../components/asset-detail/PositionStrip';
import AssetChart from '../components/asset-detail/AssetChart';
import AssetStatsGrid from '../components/asset-detail/AssetStatsGrid';
import AssetAbout from '../components/asset-detail/AssetAbout';
import AssetDividend from '../components/asset-detail/AssetDividend';

const TABS = ['Overview', 'Transactions'];

function OverviewTab({ asset, position }) {
  const hasDividend = asset.daily_metrics?.dividend_yield != null && asset.asset_class !== 'Crypto';
  return (
    <div>
      <AssetStatsGrid asset={asset} />
      <div className={`grid gap-6 items-start ${hasDividend ? 'lg:grid-cols-2' : ''}`}>
        <AssetAbout asset={asset} />
        {hasDividend && <AssetDividend asset={asset} position={position} />}
      </div>
    </div>
  );
}

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

      let assetData;
      try {
        const res = await api(`/assets/${id}/detail`);
        if (!res.ok) {
          setError(res.status === 404 ? 'Asset not found' : 'Failed to load asset');
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

  const handlePeriodChange = useCallback(async (period) => {
    setChartPeriod(period);
    if (!asset) return;
    const res = await api(`/prices/historical/${asset.symbol}?period=${period}`);
    if (res.ok) setPriceHistory(await res.json());
  }, [asset]);

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

  const allTransactions = useMemo(() => {
    const tradeRows = trades.map((t) => ({
      date: t.date,
      type: t.type,
      quantity: t.quantity,
      price: t.price,
      total: t.amount,
      account: t.account_name,
    }));
    const dividendRows = dividends.map((d) => ({
      date: d.date,
      type: d.type || 'DIVIDEND',
      quantity: null,
      price: null,
      total: d.amount,
      account: d.account_name,
    }));
    return [...tradeRows, ...dividendRows].sort((a, b) => b.date.localeCompare(a.date));
  }, [trades, dividends]);

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
      <nav className="mb-4 flex items-center gap-2 text-sm text-[var(--text-secondary)]">
        <Link to="/assets" className="hover:text-[var(--text-primary)]">Assets</Link>
        <span>/</span>
        <span className="text-[var(--text-primary)] font-medium">{asset.symbol}</span>
      </nav>

      <AssetHero asset={asset} onToggleFavorite={handleToggleFavorite} onRefreshPrice={handleRefreshPrice} />

      {position && <PositionStrip position={position} asset={asset} />}

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
        dividendDates={priceHistory?.dividend_dates || []}
      />

      {activeTab === 'Overview' && (
        <OverviewTab asset={asset} position={position} />
      )}

      {activeTab === 'Transactions' && (
        <Card className="p-0 overflow-hidden">
          {allTransactions.length === 0 ? (
            <NoTransactionsEmpty />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-primary)]">
                  <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-secondary)]">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-secondary)]">Type</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-secondary)]">Qty</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-secondary)]">Price</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-secondary)]">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-secondary)]">Account</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-primary)]">
                {allTransactions.map((txn, i) => (
                  <tr key={i} className="hover:bg-[var(--bg-tertiary)] transition-colors">
                    <td className="px-4 py-3 text-[var(--text-primary)]">{formatDate(txn.date)}</td>
                    <td className="px-4 py-3"><TransactionBadge type={txn.type} /></td>
                    <td className="px-4 py-3 text-right text-[var(--text-primary)]">
                      {txn.quantity != null ? formatNumber(txn.quantity) : '--'}
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--text-primary)]">
                      {txn.price != null ? formatCurrency(txn.price, asset.currency) : '--'}
                    </td>
                    <td className="px-4 py-3 text-right text-[var(--text-primary)]">
                      {txn.total != null ? formatCurrency(txn.total, asset.currency) : '--'}
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{txn.account || '--'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </PageContainer>
  );
}
