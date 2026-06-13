import { useState, useEffect, useMemo } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import { api } from '../lib';

async function fetchJson(endpoint, label) {
  const res = await api(endpoint);
  if (!res.ok) throw new Error(`Failed to fetch ${label}: ${res.statusText}`);
  return res.json();
}

function buildQuery(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value != null) search.set(key, value);
  }
  return `?${search.toString()}`;
}

function getSyncStatus(lastSync) {
  if (!lastSync) return { status: 'unknown', color: 'bg-[var(--text-faint)]' };
  const diffDays = Math.floor((Date.now() - new Date(lastSync)) / 86400000);
  if (diffDays <= 7) return { status: 'green', color: 'bg-[var(--positive)]' };
  if (diffDays <= 30) return { status: 'amber', color: 'bg-[var(--warning)]' };
  return { status: 'red', color: 'bg-[var(--negative)]' };
}

function formatLastSync(dateStr) {
  if (!dateStr) return 'Never';
  const diffMs = Date.now() - new Date(dateStr);
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  const diffHours = Math.floor(diffMs / 3600000);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 30) return `${diffDays} days ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Groups the positions endpoint's per-account breakdown by account_id.
 * Returns Map<accountId, Array<{ symbol, name, assetClass, quantity, marketValue, pnl, pnlPct }>>
 */
function groupHoldingsByAccount(positions) {
  const map = new Map();
  for (const pos of positions) {
    for (const acct of pos.accounts || []) {
      if (!map.has(acct.account_id)) map.set(acct.account_id, []);
      map.get(acct.account_id).push({
        symbol: pos.symbol,
        name: pos.name,
        assetClass: pos.asset_class,
        quantity: acct.quantity,
        costBasis: acct.cost_basis,
        marketValue: acct.market_value,
        pnl: acct.pnl,
        pnlPct: acct.pnl_pct,
      });
    }
  }
  // Sort each account's holdings by market value descending
  for (const holdings of map.values()) {
    holdings.sort((a, b) => (b.marketValue || 0) - (a.marketValue || 0));
  }
  return map;
}

export function useAccountsData() {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  const currency = portfolioCurrency || globalCurrency;

  const [rawAccounts, setRawAccounts] = useState([]);
  const [dashboardAccounts, setDashboardAccounts] = useState([]);
  const [positions, setPositions] = useState([]);
  const [positionsTruncated, setPositionsTruncated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = () => setRefreshKey((k) => k + 1);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      const shared = { portfolio_id: selectedPortfolioId };
      const withCurrency = { ...shared, display_currency: currency };

      try {
        const [accountsData, dashboardData, positionsData] = await Promise.all([
          fetchJson(`/accounts${buildQuery({ is_active: true, limit: 100, ...shared })}`, 'accounts'),
          fetchJson(`/dashboard/summary${buildQuery(withCurrency)}`, 'dashboard'),
          fetchJson(`/positions${buildQuery({ ...withCurrency, limit: 100 })}`, 'positions'),
        ]);

        if (cancelled) return;

        setRawAccounts(accountsData.items);
        setDashboardAccounts(dashboardData.accounts || []);
        setPositions(positionsData.items || []);
        setPositionsTruncated(positionsData.has_more || false);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [currency, selectedPortfolioId, refreshKey]);

  // Enrich accounts with values and holdings
  const { accounts, accountHoldings, totalValue } = useMemo(() => {
    const valueMap = new Map();
    for (const da of dashboardAccounts) {
      valueMap.set(da.id, { value: da.value || 0, holdingCount: da.holding_count || 0 });
    }

    const holdingsMap = groupHoldingsByAccount(positions);
    const total = dashboardAccounts.reduce((sum, a) => sum + (a.value || 0), 0);

    const enriched = rawAccounts
      .map((acct) => {
        const vals = valueMap.get(acct.id) || { value: 0, holdingCount: 0 };
        const lastSync = acct.updated_at || acct.created_at;
        return {
          ...acct,
          value: vals.value,
          holdingCount: vals.holdingCount,
          allocationPct: total > 0 ? (vals.value / total) * 100 : 0,
          lastSync,
          lastSyncFormatted: formatLastSync(lastSync),
          syncStatus: getSyncStatus(lastSync),
        };
      })
      .sort((a, b) => b.value - a.value);

    return { accounts: enriched, accountHoldings: holdingsMap, totalValue: total };
  }, [rawAccounts, dashboardAccounts, positions]);

  return { accounts, accountHoldings, totalValue, loading, error, currency, refresh, positionsTruncated };
}
