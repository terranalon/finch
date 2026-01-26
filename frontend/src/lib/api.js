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
 * Handle API response: check for errors and parse JSON.
 *
 * @param {Response} response - fetch response
 * @param {string} defaultError - default error message if none in response
 * @returns {Promise<object>} parsed JSON response
 * @throws {Error} if response is not ok
 */
async function handleResponse(response, defaultError) {
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || defaultError);
  }
  return response.json();
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

/**
 * Verify email with token from verification link
 *
 * @param {string} token - Verification token from email
 */
export async function verifyEmail(token) {
  const response = await fetch(`${API_BASE}/auth/verify-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  return handleResponse(response, 'Email verification failed');
}

/**
 * Resend verification email
 *
 * @param {string} email - User's email address
 */
export async function resendVerification(email) {
  const response = await fetch(`${API_BASE}/auth/resend-verification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return handleResponse(response, 'Failed to resend verification email');
}

/**
 * Reset password with token from reset link
 *
 * @param {string} token - Reset token from email
 * @param {string} newPassword - New password
 */
export async function resetPassword(token, newPassword) {
  const response = await fetch(`${API_BASE}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  return handleResponse(response, 'Password reset failed');
}

/**
 * Change password for authenticated user
 *
 * @param {string} currentPassword - User's current password
 * @param {string} newPassword - New password
 */
export async function changePassword(currentPassword, newPassword) {
  const response = await api('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  return handleResponse(response, 'Failed to change password');
}

/**
 * Request password reset email
 *
 * @param {string} email - User's email address
 */
export async function forgotPassword(email) {
  const response = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  return handleResponse(response, 'Failed to send reset email');
}

/**
 * Verify MFA code during login
 *
 * @param {string} tempToken - Temporary token from login response
 * @param {string} code - MFA code
 * @param {string} method - MFA method (totp, email, recovery)
 */
export async function verifyMfa(tempToken, code, method) {
  const response = await fetch(`${API_BASE}/auth/mfa/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ temp_token: tempToken, code, method }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'MFA verification failed');
  }

  const data = await response.json();
  setToken(data.access_token);
  setRefreshToken(data.refresh_token);
  return data;
}

/**
 * Send MFA email code during login
 *
 * @param {string} tempToken - Temporary token from login response
 */
export async function sendMfaEmailCode(tempToken) {
  const response = await fetch(`${API_BASE}/auth/mfa/send-email-code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ temp_token: tempToken }),
  });
  return handleResponse(response, 'Failed to send email code');
}

/**
 * Start TOTP setup for authenticated user
 *
 * @returns {Promise<{secret: string, qr_code_base64: string}>}
 */
export async function setupTotp() {
  const response = await api('/auth/mfa/setup/totp', {
    method: 'POST',
  });
  return handleResponse(response, 'Failed to start TOTP setup');
}

/**
 * Confirm TOTP setup with verification code
 *
 * @param {string} secret - TOTP secret from setup
 * @param {string} code - 6-digit code from authenticator app
 * @param {string|null} verificationCode - Email OTP code if adding as second method
 * @returns {Promise<{recovery_codes: string[]|null}>}
 */
export async function confirmTotp(secret, code, verificationCode = null) {
  const body = { secret, code };
  if (verificationCode) {
    body.verification_code = verificationCode;
  }
  const response = await api('/auth/mfa/confirm/totp', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return handleResponse(response, 'Failed to confirm TOTP');
}

/**
 * Enable email OTP for authenticated user
 *
 * @param {string|null} verificationCode - TOTP code if adding as second method
 * @returns {Promise<{recovery_codes: string[]|null}>}
 */
export async function setupEmailOtp(verificationCode = null) {
  const body = verificationCode ? { verification_code: verificationCode } : {};
  const response = await api('/auth/mfa/setup/email', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return handleResponse(response, 'Failed to enable email OTP');
}

/**
 * Disable MFA for authenticated user
 *
 * @param {string|null} mfaCode - TOTP code (if using authenticator)
 * @param {string|null} recoveryCode - Recovery code (if using recovery)
 * @returns {Promise<{message: string}>}
 */
export async function disableMfa(mfaCode, recoveryCode) {
  const response = await api('/auth/mfa', {
    method: 'DELETE',
    body: JSON.stringify({
      mfa_code: mfaCode,
      recovery_code: recoveryCode,
    }),
  });
  return handleResponse(response, 'Failed to disable MFA');
}

/**
 * Regenerate recovery codes for authenticated user
 *
 * @param {string} code - TOTP code for verification
 * @returns {Promise<{recovery_codes: string[]}>}
 */
export async function regenerateRecoveryCodes(code) {
  const response = await api('/auth/mfa/recovery-codes', {
    method: 'POST',
    body: JSON.stringify({ mfa_code: code }),
  });
  return handleResponse(response, 'Failed to regenerate recovery codes');
}

/**
 * Get current user's MFA status
 *
 * @returns {Promise<{mfa_enabled: boolean, totp_enabled: boolean, email_otp_enabled: boolean, primary_method: string|null, has_recovery_codes: boolean}>}
 */
export async function getMfaStatus() {
  const response = await api('/auth/mfa/status');
  return handleResponse(response, 'Failed to get MFA status');
}

/**
 * Set the primary MFA method for login
 *
 * @param {string} method - 'totp' or 'email'
 * @returns {Promise<{message: string}>}
 */
export async function setPrimaryMfaMethod(method) {
  const response = await api('/auth/mfa/primary-method', {
    method: 'PUT',
    body: JSON.stringify({ method }),
  });
  return handleResponse(response, 'Failed to set primary method');
}

/**
 * Disable a specific MFA method
 *
 * @param {string} method - 'totp' or 'email'
 * @param {string} verificationCode - TOTP code or recovery code
 * @returns {Promise<{message: string}>}
 */
export async function disableMfaMethod(method, verificationCode) {
  const response = await api(`/auth/mfa/method/${method}`, {
    method: 'DELETE',
    body: JSON.stringify({ mfa_code: verificationCode }),
  });
  return handleResponse(response, 'Failed to disable MFA method');
}

/**
 * Delete a broker data source and all associated transactions
 *
 * @param {number} sourceId - The source ID to delete
 * @returns {Promise<object>} Deletion confirmation with stats
 */
export async function deleteDataSource(sourceId) {
  const response = await api(`/broker-data/source/${sourceId}`, {
    method: 'DELETE',
  });
  return handleResponse(response, 'Failed to delete data source');
}

export default api;
