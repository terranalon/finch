/**
 * Login Page - Finch Portfolio Tracker
 *
 * Handles user authentication with email/password.
 * Includes "Try Demo" button for quick access.
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth, useTheme } from '../contexts';
import { FinchIcon, ThemeToggle } from '../components/ui';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(email, password);

      // Check if MFA is required
      if (result.mfa_required) {
        navigate('/mfa-verify', {
          state: {
            tempToken: result.temp_token,
            methods: result.methods,
            email,
          },
        });
        return;
      }

      navigate('/');
    } catch (err) {
      // Handle email not verified
      if (err.code === 'email_not_verified') {
        navigate('/verification-pending', { state: { email: err.email || email } });
        return;
      }
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError('');
    setLoading(true);

    try {
      const result = await login('demo@finch.com', 'Demo1234');
      if (result.mfa_required) {
        setError('Demo account has MFA enabled. Please use regular login.');
        return;
      }
      navigate('/');
    } catch (err) {
      setError('Demo login failed. Make sure the demo user is seeded.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center bg-[var(--bg-primary)] py-12 px-4 sm:px-6 lg:px-8 relative">
      {/* Theme toggle in top-right corner */}
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
          <h2 className="mt-6 text-center text-2xl font-bold text-[var(--text-primary)] text-balance">
            Sign in to your account
          </h2>
          <p className="mt-2 text-center text-sm text-[var(--text-secondary)] text-pretty">
            Or{' '}
            <Link to="/register" className="font-medium text-accent hover:text-accent-hover">
              create a new account
            </Link>
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-4" role="alert">
              <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[var(--text-primary)]">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-[var(--border-primary)] placeholder-[var(--text-tertiary)] text-[var(--text-primary)] bg-[var(--bg-secondary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent sm:text-sm transition-colors"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label htmlFor="password" className="block text-sm font-medium text-[var(--text-primary)]">
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-sm text-accent hover:text-accent-hover"
                >
                  Forgot password?
                </Link>
              </div>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-[var(--border-primary)] placeholder-[var(--text-tertiary)] text-[var(--text-primary)] bg-[var(--bg-secondary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent sm:text-sm transition-colors"
                placeholder="Enter your password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--border-primary)]"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-[var(--bg-primary)] text-[var(--text-tertiary)]">Or</span>
            </div>
          </div>

          <div>
            <button
              type="button"
              onClick={handleDemoLogin}
              disabled={loading}
              className="btn-secondary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Try Demo Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
