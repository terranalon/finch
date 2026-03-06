import { useState, useEffect } from 'react';
import { useCurrency, usePortfolio } from '../contexts';
import api from '../lib/api';

export function useDashboardData() {
  const { currency: globalCurrency } = useCurrency();
  const { selectedPortfolioId, portfolioCurrency } = usePortfolio();
  const currency = portfolioCurrency || globalCurrency;

  const [summary, setSummary] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [cashFlows, setCashFlows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);
      try {
        const portfolioParam = selectedPortfolioId
          ? `&portfolio_id=${selectedPortfolioId}`
          : '';

        const [summaryRes, snapshotsRes, cashRes] = await Promise.all([
          api(`/api/dashboard/summary?display_currency=${currency}${portfolioParam}`),
          api(`/api/snapshots/portfolio?limit=365${portfolioParam}`),
          api(`/api/transactions/cash?display_currency=${currency}${portfolioParam}`),
        ]);

        if (cancelled) return;

        setSummary(summaryRes);
        setSnapshots(snapshotsRes.items || snapshotsRes || []);
        setCashFlows(
          (cashRes.items || cashRes || []).map((t) => ({
            date: t.date,
            amount: t.type === 'WITHDRAWAL' ? -Math.abs(t.amount) : t.amount,
          }))
        );
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAll();
    return () => { cancelled = true; };
  }, [currency, selectedPortfolioId]);

  return { summary, snapshots, cashFlows, loading, error, currency };
}
