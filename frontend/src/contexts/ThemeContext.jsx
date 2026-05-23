import { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext(undefined);

/**
 * Theme provider for managing light/dark mode.
 * Supports 'light', 'dark', and 'system' preferences.
 * Persists preference to localStorage and syncs with system preference.
 */
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem('finch-theme');
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
    return 'system';
  });

  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches
  );

  // Track OS preference changes reactively
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e) => setSystemDark(e.matches);
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const isDark = theme === 'dark' || (theme === 'system' && systemDark);

  // Apply theme class and persist preference
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('finch-theme', theme);
  }, [isDark, theme]);

  // Toggle between explicit light/dark, bypassing system preference
  const toggleTheme = () => {
    setTheme(isDark ? 'light' : 'dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, isDark }}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access theme context
 */
export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export default ThemeContext;
