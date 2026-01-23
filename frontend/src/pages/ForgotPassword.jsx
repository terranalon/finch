/**
 * Forgot Password Page
 *
 * Allows users to request a password reset email.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../contexts';
import { FinchIcon, ThemeToggle } from '../components/ui';
import { forgotPassword } from '../lib/api';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { theme, toggleTheme } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      setError(err.message || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[var(--bg-primary)] py-12 px-4 sm:px-6 lg:px-8 relative">
        <div className="absolute top-4 right-4">
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>

        <div className="max-w-md w-full space-y-8 text-center">
          <div>
            <div className="flex items-center justify-center gap-2">
              <FinchIcon className="size-10 text-accent" />
              <h1 className="text-4xl font-bold text-[var(--text-primary)]">
                <span className="text-accent">Fin</span>ch
              </h1>
            </div>
            <h2 className="mt-6 text-2xl font-bold text-[var(--text-primary)]">
              Check your email
            </h2>
          </div>

          <div className="py-4">
            <svg
              className="mx-auto h-16 w-16 text-accent"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>

          <p className="text-[var(--text-secondary)]">
            If an account exists for <strong>{email}</strong>, we&apos;ve sent a password reset link.
          </p>

          <p className="text-sm text-[var(--text-tertiary)]">
            The link will expire in 1 hour.
          </p>

          <Link
            to="/login"
            className="btn-secondary inline-block w-full py-2.5 mt-6"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    );
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
            Reset your password
          </h2>
          <p className="mt-2 text-center text-sm text-[var(--text-secondary)]">
            Enter your email address and we&apos;ll send you a link to reset your password.
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-4" role="alert">
              <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
            </div>
          )}

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
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Sending...' : 'Send reset link'}
            </button>
          </div>

          <p className="text-center text-sm text-[var(--text-tertiary)]">
            Remember your password?{' '}
            <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
