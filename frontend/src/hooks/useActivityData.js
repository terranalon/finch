import { useState, useEffect } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import { api, transformTrade, transformDividend, transformForex, transformCash } from '../lib';

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
        const [accountsRes, tradesRes, dividendsRes, forexRes, cashRes] = await Promise.all([
          api(`/accounts?is_active=true${portfolioParam}`),
          api(`/transactions/trades?limit=500${portfolioParam}${currencyParam}`),
          api(`/transactions/dividends?limit=500${portfolioParam}${currencyParam}`),
          api(`/transactions/forex?limit=500${portfolioParam}`),
          api(`/transactions/cash?limit=500${portfolioParam}${currencyParam}`),
        ]);

        if (cancelled) return;

        if (!accountsRes.ok) throw new Error(`Failed to fetch accounts: ${accountsRes.statusText}`);
        if (!tradesRes.ok) throw new Error(`Failed to fetch trades: ${tradesRes.statusText}`);
        if (!dividendsRes.ok) throw new Error(`Failed to fetch dividends: ${dividendsRes.statusText}`);
        if (!forexRes.ok) throw new Error(`Failed to fetch forex: ${forexRes.statusText}`);
        if (!cashRes.ok) throw new Error(`Failed to fetch cash: ${cashRes.statusText}`);

        const [accountsData, tradesData, dividendsData, forexData, cashData] = await Promise.all([
          accountsRes.json(),
          tradesRes.json(),
          dividendsRes.json(),
          forexRes.json(),
          cashRes.json(),
        ]);

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
