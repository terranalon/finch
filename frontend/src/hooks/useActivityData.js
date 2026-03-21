import { useState, useEffect } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import { api, transformTrade, transformDividend, transformForex, transformCash } from '../lib';

async function fetchJson(endpoint, label) {
  const res = await api(endpoint);
  if (!res.ok) throw new Error(`Failed to fetch ${label}: ${res.statusText}`);
  return res.json();
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

      const portfolioParam = selectedPortfolioId ? `&portfolio_id=${selectedPortfolioId}` : '';
      const currencyParam = currency ? `&display_currency=${currency}` : '';

      try {
        const [accountsData, tradesData, dividendsData, forexData, cashData] = await Promise.all([
          fetchJson(`/accounts?is_active=true${portfolioParam}`, 'accounts'),
          fetchJson(`/transactions/trades?limit=500${portfolioParam}${currencyParam}`, 'trades'),
          fetchJson(`/transactions/dividends?limit=500${portfolioParam}${currencyParam}`, 'dividends'),
          fetchJson(`/transactions/forex?limit=500${portfolioParam}`, 'forex'),
          fetchJson(`/transactions/cash?limit=500${portfolioParam}${currencyParam}`, 'cash'),
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
