import { useState, useEffect } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import { api, transformTrade, transformDividend, transformForex, transformCash } from '../lib';

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

export function useActivityData() {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  const currency = portfolioCurrency || globalCurrency;

  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      const shared = { portfolio_id: selectedPortfolioId };
      const withCurrency = { ...shared, display_currency: currency };

      try {
        const [accountsData, tradesData, dividendsData, forexData, cashData] = await Promise.all([
          fetchJson(`/accounts${buildQuery({ is_active: true, ...shared })}`, 'accounts'),
          fetchJson(`/transactions/trades${buildQuery({ limit: 500, ...withCurrency })}`, 'trades'),
          fetchJson(`/transactions/dividends${buildQuery({ limit: 500, ...withCurrency })}`, 'dividends'),
          fetchJson(`/transactions/forex${buildQuery({ limit: 500, ...shared })}`, 'forex'),
          fetchJson(`/transactions/cash${buildQuery({ limit: 500, ...withCurrency })}`, 'cash'),
        ]);

        if (cancelled) return;

        const allTransactions = [
          ...tradesData.items.map(transformTrade),
          ...dividendsData.items.map(transformDividend),
          ...forexData.items.map(transformForex),
          ...cashData.items.map(transformCash),
        ];

        allTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));

        setTransactions(allTransactions);
        setAccounts(accountsData.items);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [currency, selectedPortfolioId]);

  return { transactions, accounts, loading, error, currency };
}
