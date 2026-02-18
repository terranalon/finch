import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { api } from '../lib/api';
import { usePortfolio } from '../contexts';

/**
 * Hook for full portfolio CRUD + account linking on the /portfolios management page.
 * Fetches portfolios with accounts and values included.
 * Every successful mutation triggers the global refetchPortfolios() to keep the navbar in sync.
 */
export function usePortfolioManagement() {
  const { refetchPortfolios } = usePortfolio();
  const [portfolios, setPortfolios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPortfolios = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api('/portfolios?include_accounts=true&include_values=true');
      if (response.ok) {
        const data = await response.json();
        setPortfolios(data);
      } else {
        const data = await response.json();
        setError(data.message || 'Failed to fetch portfolios');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolios();
  }, [fetchPortfolios]);

  /**
   * Wraps a mutation API call with toast notifications and automatic refetch.
   * Returns true on success, false on failure.
   */
  const mutate = useCallback(async (url, options, successMessage, errorMessage) => {
    try {
      const response = await api(url, options);
      if (response.ok) {
        toast.success(successMessage);
        await fetchPortfolios();
        await refetchPortfolios();
        return true;
      }
      const result = await response.json();
      toast.error(result.message || errorMessage);
      return false;
    } catch (err) {
      toast.error(err.message);
      return false;
    }
  }, [fetchPortfolios, refetchPortfolios]);

  const createPortfolio = useCallback(async (data) => {
    return mutate(
      '/portfolios',
      { method: 'POST', body: JSON.stringify(data) },
      'Portfolio created',
      'Failed to create portfolio'
    );
  }, [mutate]);

  const updatePortfolio = useCallback(async (id, data) => {
    return mutate(
      `/portfolios/${id}`,
      { method: 'PUT', body: JSON.stringify(data) },
      'Portfolio updated',
      'Failed to update portfolio'
    );
  }, [mutate]);

  const deletePortfolio = useCallback(async (id) => {
    return mutate(
      `/portfolios/${id}?confirm=true`,
      { method: 'DELETE' },
      'Portfolio deleted',
      'Failed to delete portfolio'
    );
  }, [mutate]);

  const setDefault = useCallback(async (id) => {
    return mutate(
      `/portfolios/${id}`,
      { method: 'PATCH', body: JSON.stringify({ is_default: true }) },
      'Default portfolio updated',
      'Failed to set default portfolio'
    );
  }, [mutate]);

  const linkAccount = useCallback(async (portfolioId, accountId) => {
    return mutate(
      `/portfolios/${portfolioId}/accounts/${accountId}`,
      { method: 'PUT' },
      'Account linked',
      'Failed to link account'
    );
  }, [mutate]);

  const unlinkAccount = useCallback(async (portfolioId, accountId) => {
    return mutate(
      `/portfolios/${portfolioId}/accounts/${accountId}`,
      { method: 'DELETE' },
      'Account unlinked',
      'Failed to unlink account'
    );
  }, [mutate]);

  const deleteAccount = useCallback(async (accountId) => {
    return mutate(
      `/accounts/${accountId}`,
      { method: 'DELETE' },
      'Account deleted',
      'Failed to delete account'
    );
  }, [mutate]);

  const fetchDeletionPreview = useCallback(async (id) => {
    const response = await api(`/portfolios/${id}/deletion-preview`);
    if (response.ok) {
      return response.json();
    }
    const data = await response.json();
    throw new Error(data.message || 'Failed to fetch deletion preview');
  }, []);

  const fetchLinkableAccounts = useCallback(async (id) => {
    const response = await api(`/portfolios/${id}/linkable-accounts`);
    if (response.ok) {
      return response.json();
    }
    const data = await response.json();
    throw new Error(data.message || 'Failed to fetch linkable accounts');
  }, []);

  return {
    portfolios,
    loading,
    error,
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    setDefault,
    linkAccount,
    unlinkAccount,
    deleteAccount,
    fetchDeletionPreview,
    fetchLinkableAccounts,
    refetch: fetchPortfolios,
  };
}
