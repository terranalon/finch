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

        const [summaryResp, snapshotsResp, cashResp] = await Promise.all([
          api(`/dashboard/summary?display_currency=${currency}${portfolioParam}`),
          api(`/snapshots/portfolio?limit=365&display_currency=${currency}${portfolioParam}`),
          api(`/transactions/cash?display_currency=${currency}&limit=500${portfolioParam}`),
        ]);

        if (cancelled) return;

        const summaryRes = await summaryResp.json();
        const snapshotsRes = await snapshotsResp.json();
        const cashRes = await cashResp.json();

        setSummary(summaryRes);
        const snapshotItems = snapshotsRes.items || snapshotsRes || [];
        // API returns newest-first; chart needs oldest-first (ascending)
        const sorted = snapshotItems.slice().reverse();

        // Append a live data point for today so the chart matches the summary value
        if (summaryRes?.total_value != null) {
          const today = new Date().toISOString().slice(0, 10);
          const last = sorted[sorted.length - 1];
          if (last && last.date === today) {
            sorted[sorted.length - 1] = { ...last, value: summaryRes.total_value };
          } else {
            sorted.push({ date: today, value: summaryRes.total_value });
          }
        }

        setSnapshots(sorted);
        const cashItems = cashRes.items || cashRes || [];
        setCashFlows(
          Array.isArray(cashItems)
            ? cashItems
                .filter((t) => t.type === 'Deposit' || t.type === 'Withdrawal')
                .map((t) => ({
                  date: t.date,
                  amount: t.type === 'Withdrawal' ? -Math.abs(t.amount) : Math.abs(t.amount),
                }))
            : []
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
