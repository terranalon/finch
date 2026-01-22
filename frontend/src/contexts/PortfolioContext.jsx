import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import { useAuth } from './AuthContext';

const PortfolioContext = createContext(undefined);

/**
 * Portfolio provider for managing selected portfolio globally.
 * Persists preference to localStorage.
 * Respects user's default portfolio and show_combined_view preference.
 */
export function PortfolioProvider({ children }) {
  const { isAuthenticated, user } = useAuth();
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState(() => {
    const stored = localStorage.getItem('finch-portfolio-id');
    // Return stored value, or undefined to indicate "needs initialization"
    // null explicitly means "All Portfolios", undefined means "not yet decided"
    return stored !== null ? (stored || null) : undefined;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // User preference for showing "All Portfolios" option
  const showCombinedView = user?.show_combined_view ?? true;

  // Fetch portfolios when authenticated
  useEffect(() => {
    async function fetchPortfolios() {
      if (!isAuthenticated) {
        setPortfolios([]);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await api('/portfolios?include_values=true');
        if (response.ok) {
          const data = await response.json();
          setPortfolios(data);

          // Handle initial portfolio selection
          if (selectedPortfolioId === undefined) {
            // First load - no stored preference
            // Find user's default portfolio, or fall back to first portfolio if combined view disabled
            const defaultPortfolio = data.find((p) => p.is_default);
            if (defaultPortfolio) {
              setSelectedPortfolioId(defaultPortfolio.id);
              localStorage.setItem('finch-portfolio-id', defaultPortfolio.id);
            } else if (!showCombinedView && data.length > 0) {
              // No default set but combined view disabled - use first portfolio
              setSelectedPortfolioId(data[0].id);
              localStorage.setItem('finch-portfolio-id', data[0].id);
            } else {
              // Use "All Portfolios"
              setSelectedPortfolioId(null);
            }
          } else if (selectedPortfolioId && !data.some((p) => p.id === selectedPortfolioId)) {
            // Stored selection no longer exists
            const defaultPortfolio = data.find((p) => p.is_default);
            if (defaultPortfolio) {
              setSelectedPortfolioId(defaultPortfolio.id);
              localStorage.setItem('finch-portfolio-id', defaultPortfolio.id);
            } else {
              setSelectedPortfolioId(null);
              localStorage.removeItem('finch-portfolio-id');
            }
          }
        } else {
          setError('Failed to fetch portfolios');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchPortfolios();
  }, [isAuthenticated, showCombinedView]);

  // When showCombinedView is disabled and user is viewing "All Portfolios", switch to a specific portfolio
  useEffect(() => {
    if (!showCombinedView && selectedPortfolioId === null && portfolios.length > 0) {
      const defaultPortfolio = portfolios.find((p) => p.is_default);
      const targetId = defaultPortfolio?.id || portfolios[0].id;
      setSelectedPortfolioId(targetId);
      localStorage.setItem('finch-portfolio-id', targetId);
    }
  }, [showCombinedView, selectedPortfolioId, portfolios]);

  const selectPortfolio = useCallback((portfolioId) => {
    setSelectedPortfolioId(portfolioId);
    if (portfolioId) {
      localStorage.setItem('finch-portfolio-id', portfolioId);
    } else {
      localStorage.removeItem('finch-portfolio-id');
    }
  }, []);

  const refetchPortfolios = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const response = await api('/portfolios?include_values=true');
      if (response.ok) {
        const data = await response.json();
        setPortfolios(data);

        // If selected portfolio was deleted, reset to all
        if (selectedPortfolioId && !data.some((p) => p.id === selectedPortfolioId)) {
          setSelectedPortfolioId(null);
          localStorage.removeItem('finch-portfolio-id');
        }
      }
    } catch (err) {
      console.error('Failed to refetch portfolios:', err);
    }
  }, [isAuthenticated, selectedPortfolioId]);

  const selectedPortfolio = selectedPortfolioId
    ? portfolios.find((p) => p.id === selectedPortfolioId)
    : null;

  // The portfolio's default currency (null if viewing "All Portfolios")
  const portfolioCurrency = selectedPortfolio?.default_currency || null;

  return (
    <PortfolioContext.Provider
      value={{
        portfolios,
        selectedPortfolioId,
        selectedPortfolio,
        portfolioCurrency,
        selectPortfolio,
        refetchPortfolios,
        showCombinedView,
        loading,
        error,
      }}
    >
      {children}
    </PortfolioContext.Provider>
  );
}

/**
 * Hook to access portfolio context
 */
export function usePortfolio() {
  const context = useContext(PortfolioContext);
  if (context === undefined) {
    throw new Error('usePortfolio must be used within a PortfolioProvider');
  }
  return context;
}

export default PortfolioContext;
