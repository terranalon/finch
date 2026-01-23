/**
 * MFA Verify Page
 *
 * Handles MFA verification during login flow.
 */

import { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth, useTheme } from '../contexts';
import { FinchIcon, ThemeToggle } from '../components/ui';
import { verifyMfa, sendMfaEmailCode } from '../lib/api';

function getCodeLabel(method) {
  switch (method) {
    case 'totp':
      return 'Authenticator code';
    case 'email':
      return 'Email code';
    default:
      return 'Verification code';
  }
}

export default function MfaVerify() {
  const [code, setCode] = useState('');
  const [method, setMethod] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);

  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const { tempToken, methods, email } = location.state || {};

  // Redirect if no temp token
  useEffect(() => {
    if (!tempToken) {
      navigate('/login');
    }
  }, [tempToken, navigate]);

  // Set default method
  useEffect(() => {
    if (methods && methods.length > 0 && !method) {
      setMethod(methods[0]);
    }
  }, [methods, method]);

  const handleSendEmailCode = async () => {
    setSendingCode(true);
    setError('');
    setMessage('');

    try {
      await sendMfaEmailCode(tempToken);
      setMessage('Verification code sent to your email');
    } catch (err) {
      setError(err.message || 'Failed to send code');
    } finally {
      setSendingCode(false);
    }
  };

  // Get setUserFromMfa from context
  const { setUserFromMfa } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const result = await verifyMfa(tempToken, code, method);
      // MFA successful, tokens are set in api.js
      // Set user in context
      if (result.user) {
        setUserFromMfa(result.user);
      }
      navigate('/');
    } catch (err) {
      setError(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  if (!tempToken) {
    return null;
  }

  return (
    <div className="min-h-dvh flex items-center justify-center bg-[var(--bg-primary)] py-12 px-4 sm:px-6 lg:px-8 relative">
      <div className="absolute top-4 right-4">
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
      </div>

      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex items-center justify-center gap-2">
            <FinchIcon className="size-10 text-accent" />
            <h1 className="text-4xl font-bold text-[var(--text-primary)]">
              <span className="text-accent">Fin</span>ch
            </h1>
          </div>
          <h2 className="mt-6 text-center text-2xl font-bold text-[var(--text-primary)]">
            Two-factor authentication
          </h2>
          <p className="mt-2 text-center text-sm text-[var(--text-secondary)]">
            Enter your verification code to continue
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-4" role="alert">
              <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
            </div>
          )}

          {message && (
            <div className="rounded-md bg-positive-bg dark:bg-positive-bg-dark p-4">
              <p className="text-sm text-positive dark:text-positive-dark">{message}</p>
            </div>
          )}

          {/* Method selector */}
          {methods && methods.length > 1 && (
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                Verification method
              </label>
              <div className="flex gap-2">
                {methods.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => {
                      setMethod(m);
                      setCode('');
                      setError('');
                    }}
                    className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                      method === m
                        ? 'bg-accent text-white'
                        : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                    }`}
                  >
                    {m === 'totp' ? 'Authenticator' : 'Email'}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Email OTP - send code button */}
          {method === 'email' && (
            <div className="text-center">
              <button
                type="button"
                onClick={handleSendEmailCode}
                disabled={sendingCode}
                className="text-accent hover:text-accent-hover text-sm font-medium disabled:opacity-50"
              >
                {sendingCode ? 'Sending...' : 'Send code to my email'}
              </button>
            </div>
          )}

          <div>
            <label htmlFor="code" className="block text-sm font-medium text-[var(--text-primary)]">
              {getCodeLabel(method)}
            </label>
            <input
              id="code"
              name="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-[var(--border-primary)] placeholder-[var(--text-tertiary)] text-[var(--text-primary)] bg-[var(--bg-secondary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent sm:text-sm transition-colors text-center text-2xl tracking-widest"
              placeholder="000000"
              maxLength={method === 'recovery' ? 14 : 6}
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={loading || !code}
              className="btn-primary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Verifying...' : 'Verify'}
            </button>
          </div>

          {/* Recovery code option */}
          <div className="text-center space-y-2">
            <p className="text-sm text-[var(--text-tertiary)]">
              Lost access to your authenticator?
            </p>
            <button
              type="button"
              onClick={() => {
                setMethod('recovery');
                setCode('');
                setError('');
              }}
              className="text-accent hover:text-accent-hover text-sm font-medium"
            >
              Use a recovery code
            </button>
          </div>

          <div className="text-center">
            <Link
              to="/login"
              className="text-sm text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
            >
              &larr; Back to sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
