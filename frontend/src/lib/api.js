/**
 * Centralized API client with authentication support.
 *
 * Handles:
 * - Automatic auth header injection
 * - Token storage in localStorage
 * - Automatic token refresh on 401
 * - Login/register/logout functions
 */

const API_BASE = 'http://localhost:8000/api';

/**
 * Get stored auth token
 */
function getToken() {
  return localStorage.getItem('access_token');
}

/**
 * Set auth token
 */
export function setToken(token) {
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
}

/**
 * Set refresh token
 */
export function setRefreshToken(token) {
  if (token) {
    localStorage.setItem('refresh_token', token);
  } else {
    localStorage.removeItem('refresh_token');
  }
}

/**
 * Get refresh token
 */
export function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

/**
 * Clear all auth tokens
 */
export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  return !!getToken();
}

/**
 * Refresh the access token using refresh token
 */
async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (response.ok) {
      const data = await response.json();
      setToken(data.access_token);
      if (data.refresh_token) {
        setRefreshToken(data.refresh_token);
      }
      return true;
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
  }

  // Refresh failed - clear tokens
  clearTokens();
  return false;
}

/**
 * Make an authenticated API request.
 *
 * Automatically adds Authorization header if token exists.
 * Attempts token refresh on 401 responses.
 *
 * @param {string} endpoint - API endpoint (e.g., '/accounts')
 * @param {object} options - fetch options
 * @returns {Promise<Response>}
 */
export async function api(endpoint, options = {}) {
  const token = getToken();
  const isFormData = options.body instanceof FormData;

  // Don't set Content-Type for FormData (browser sets it with boundary)
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle 401 - try to refresh token
  if (response.status === 401 && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      // Retry the original request with new token
      headers['Authorization'] = `Bearer ${getToken()}`;
      return fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });
    }
  }

  return response;
}

/**
 * Login with email and password
 *
 * @param {string} email
 * @param {string} password
 * @returns {Promise<object>} Auth response with tokens and user
 */
export async function login(email, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  const data = await response.json();
  setToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

/**
 * Register a new user
 *
 * @param {string} email
 * @param {string} password
 * @param {string} name
 * @returns {Promise<object>} Auth response with tokens and user
 */
export async function register(email, password, name) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }

  const data = await response.json();
  setToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

/**
 * Logout - clears tokens and notifies server
 */
export async function logout() {
  const token = getToken();
  const refreshToken = getRefreshToken();

  if (token && refreshToken) {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (error) {
      console.error('Logout request failed:', error);
    }
  }

  clearTokens();
}

export default api;
