import { useState, useEffect, useCallback, useRef } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import api from '../lib/api';
import { mergeRecentActivity } from './assetActivity';

const RECENT_LIMIT = 5;

/**
 * Owns all data fetching for the Asset Detail page.
 *
 * Returns:
 *   asset, position, recentActivity (max 5 merged rows), activityCount (total
 *   trades + dividends for the "View all N" link), priceHistory, chartPeriod,
 *   loading, error, and the setChartPeriod / toggleFavorite / refreshPrice handlers.
 */
export function useAssetDetailData(id) {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  const currency = portfolioCurrency || globalCurrency;

  const [asset, setAsset] = useState(null);
  const [position, setPosition] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [activityCount, setActivityCount] = useState(0);
  const [priceHistory, setPriceHistory] = useState(null);
  const [chartPeriod, setChartPeriod] = useState('1y');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const latestPeriodRequest = useRef(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      let assetData;
      try {
        const res = await api(`/assets/${id}/detail`);
        if (!res.ok) {
          if (!cancelled) {
            setError(res.status === 404 ? 'Asset not found' : 'Failed to load asset');
            setLoading(false);
          }
          return;
        }
        assetData = await res.json();
      } catch {
        if (!cancelled) {
          setError('Failed to load asset. Please try again.');
          setLoading(false);
        }
        return;
      }

      if (cancelled) return;
      setAsset(assetData);

      const symbol = assetData.symbol;
      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';

      const [posRes, tradesRes, dividendsRes, pricesRes] = await Promise.allSettled([
        api(`/positions?limit=100&display_currency=${currency}${portfolioParam}`).then((r) => r.json()),
        api(`/transactions/trades?symbol=${symbol}&limit=${RECENT_LIMIT}`).then((r) => r.json()),
        api(`/transactions/dividends?symbol=${symbol}&limit=${RECENT_LIMIT}`).then((r) => r.json()),
        api(`/prices/historical/${symbol}?period=${chartPeriod}`).then((r) => r.json()),
      ]);

      if (cancelled) return;

      if (posRes.status === 'fulfilled') {
        const items = posRes.value.items || [];
        setPosition(items.find((p) => p.asset_id === assetData.id) || null);
      }

      const trades = tradesRes.status === 'fulfilled' ? tradesRes.value.items || [] : [];
      const dividends = dividendsRes.status === 'fulfilled' ? dividendsRes.value.items || [] : [];
      const tradesTotal = tradesRes.status === 'fulfilled' ? tradesRes.value.total ?? trades.length : 0;
      const dividendsTotal = dividendsRes.status === 'fulfilled' ? dividendsRes.value.total ?? dividends.length : 0;

      setRecentActivity(mergeRecentActivity(trades, dividends, RECENT_LIMIT));
      setActivityCount(tradesTotal + dividendsTotal);

      if (pricesRes.status === 'fulfilled') setPriceHistory(pricesRes.value);

      setLoading(false);
    }

    load();
    return () => { cancelled = true; };
    // chartPeriod intentionally omitted: the initial load uses the default
    // period, and period switches are handled imperatively by handlePeriodChange.
    // Re-running the full load on every period change would be wasteful.
  }, [id, currency, selectedPortfolioId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePeriodChange = useCallback(async (period) => {
    setChartPeriod(period);
    if (!asset) return;
    const requestId = ++latestPeriodRequest.current;
    const res = await api(`/prices/historical/${asset.symbol}?period=${period}`);
    if (res.ok && requestId === latestPeriodRequest.current) {
      setPriceHistory(await res.json());
    }
  }, [asset]);

  const toggleFavorite = useCallback(async () => {
    if (!asset) return;
    const res = await api(`/assets/${asset.id}/favorite`, { method: 'PUT' });
    if (res.ok) setAsset((prev) => ({ ...prev, is_favorite: !prev.is_favorite }));
  }, [asset]);

  const refreshPrice = useCallback(async () => {
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

  return {
    asset,
    position,
    recentActivity,
    activityCount,
    priceHistory,
    chartPeriod,
    loading,
    error,
    currency,
    setChartPeriod: handlePeriodChange,
    toggleFavorite,
    refreshPrice,
  };
}
