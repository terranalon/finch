import { useState, useEffect, useCallback } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import api from '../lib/api';

async function fetchJson(endpoint, label) {
  const res = await api(endpoint);
  if (!res.ok) throw new Error(`Failed to fetch ${label}: ${res.statusText}`);
  return res.json();
}

export function useAssetsData() {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  const currency = portfolioCurrency || globalCurrency;

  const [assets, setAssets] = useState([]);
  const [positionMap, setPositionMap] = useState(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';

      try {
        const [assetsData, positionsData] = await Promise.all([
          fetchJson(`/assets/market?display_currency=${currency}&limit=500`, 'assets'),
          fetchJson(`/positions?display_currency=${currency}&limit=500${portfolioParam}`, 'positions').catch(() => null),
        ]);

        if (cancelled) return;

        setAssets(assetsData.items);
        setPositionMap(new Map(positionsData ? positionsData.items.map((pos) => [pos.asset_id, pos]) : []));
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [currency, selectedPortfolioId]);

  const toggleFavorite = useCallback(async (assetId) => {
    setAssets((prev) =>
      prev.map((a) => (a.id === assetId ? { ...a, is_favorite: !a.is_favorite } : a))
    );
    try {
      await api(`/assets/${assetId}/favorite`, { method: 'PUT' });
    } catch {
      setAssets((prev) =>
        prev.map((a) => (a.id === assetId ? { ...a, is_favorite: !a.is_favorite } : a))
      );
    }
  }, []);

  // Sync local state only (no API call) -- used when AssetDetailSidebar
  // already fires its own PUT /assets/:id/favorite
  const syncFavorite = useCallback((assetId, newValue) => {
    setAssets((prev) =>
      prev.map((a) => (a.id === assetId ? { ...a, is_favorite: newValue } : a))
    );
  }, []);

  return { assets, positionMap, loading, error, currency, toggleFavorite, syncFavorite };
}
