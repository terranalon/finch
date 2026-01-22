import { createContext, useContext, useState } from 'react';

const CurrencyContext = createContext(undefined);

/**
 * Supported currencies for display
 */
export const SUPPORTED_CURRENCIES = [
  { code: 'USD', symbol: '$', name: 'US Dollar' },
  { code: 'ILS', symbol: '\u20AA', name: 'Israeli Shekel' },
  { code: 'EUR', symbol: '\u20AC', name: 'Euro' },
  { code: 'GBP', symbol: '\u00A3', name: 'British Pound' },
];

/**
 * Currency provider for managing display currency globally.
 * Persists preference to localStorage.
 */
export function CurrencyProvider({ children }) {
  const [currency, setCurrency] = useState(() => {
    const stored = localStorage.getItem('finch-currency');
    if (stored && SUPPORTED_CURRENCIES.some((c) => c.code === stored)) {
      return stored;
    }
    return 'USD';
  });

  const changeCurrency = (newCurrency) => {
    if (SUPPORTED_CURRENCIES.some((c) => c.code === newCurrency)) {
      setCurrency(newCurrency);
      localStorage.setItem('finch-currency', newCurrency);
    }
  };

  const currentCurrencyInfo = SUPPORTED_CURRENCIES.find((c) => c.code === currency) || SUPPORTED_CURRENCIES[0];

  return (
    <CurrencyContext.Provider
      value={{
        currency,
        setCurrency: changeCurrency,
        currencySymbol: currentCurrencyInfo.symbol,
        currencyName: currentCurrencyInfo.name,
        supportedCurrencies: SUPPORTED_CURRENCIES,
      }}
    >
      {children}
    </CurrencyContext.Provider>
  );
}

/**
 * Hook to access currency context
 */
export function useCurrency() {
  const context = useContext(CurrencyContext);
  if (context === undefined) {
    throw new Error('useCurrency must be used within a CurrencyProvider');
  }
  return context;
}

export default CurrencyContext;
