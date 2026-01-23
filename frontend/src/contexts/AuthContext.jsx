import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  isAuthenticated,
  clearTokens,
  api
} from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    async function checkAuth() {
      if (isAuthenticated()) {
        try {
          // Fetch current user profile
          const response = await api('/auth/me');
          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
          } else {
            // Token invalid, clear it
            clearTokens();
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          clearTokens();
        }
      }
      setLoading(false);
    }
    checkAuth();
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await apiLogin(email, password);
    // Only set user if we got full tokens (not MFA required)
    if (data.user && !data.mfa_required) {
      setUser(data.user);
    }
    return data;
  }, []);

  const register = useCallback(async (email, password) => {
    // Registration now requires email verification
    // So we don't get tokens back - just a success message
    const data = await apiRegister(email, password);
    return data;
  }, []);

  const setUserFromMfa = useCallback((userData) => {
    setUser(userData);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const updatePreferences = useCallback(async (preferences) => {
    const response = await api('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(preferences),
    });
    if (response.ok) {
      const userData = await response.json();
      setUser(userData);
      return userData;
    }
    throw new Error('Failed to update preferences');
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    updatePreferences,
    setUserFromMfa,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
