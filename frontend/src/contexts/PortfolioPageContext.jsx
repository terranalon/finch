import { createContext, useContext } from 'react';

const PortfolioPageContext = createContext(undefined);

export function PortfolioPageProvider({ children, value }) {
  return (
    <PortfolioPageContext.Provider value={value}>
      {children}
    </PortfolioPageContext.Provider>
  );
}

export function usePortfolioPage() {
  const context = useContext(PortfolioPageContext);
  if (!context) {
    throw new Error('usePortfolioPage must be used within PortfolioPageProvider');
  }
  return context;
}
