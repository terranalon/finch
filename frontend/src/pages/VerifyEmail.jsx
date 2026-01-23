/**
 * Verify Email Page
 *
 * Handles email verification when user clicks the link from their email.
 */

import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTheme } from '../contexts';
import { FinchIcon, ThemeToggle } from '../components/ui';
import { verifyEmail } from '../lib/api';

export default function VerifyEmail() {
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [error, setError] = useState('');

  const { theme, toggleTheme } = useTheme();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  useEffect(() => {
    async function verify() {
      if (!token) {
        setStatus('error');
        setError('No verification token provided');
        return;
      }

      try {
        await verifyEmail(token);
        setStatus('success');
      } catch (err) {
        setStatus('error');
        setError(err.message || 'Verification failed');
      }
    }

    verify();
  }, [token]);

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
        </div>

        {status === 'verifying' && (
          <div className="space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto" />
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Verifying your email...
            </h2>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-6">
            <div className="py-4">
              <svg
                className="mx-auto h-16 w-16 text-positive"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Email verified!
            </h2>
            <p className="text-[var(--text-secondary)]">
              Your email has been verified successfully. You can now sign in to your account.
            </p>
            <Link
              to="/login"
              className="btn-primary inline-block w-full py-2.5"
            >
              Sign in
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-6">
            <div className="py-4">
              <svg
                className="mx-auto h-16 w-16 text-negative"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Verification failed
            </h2>
            <p className="text-[var(--text-secondary)]">{error}</p>
            <div className="space-y-3">
              <p className="text-sm text-[var(--text-tertiary)]">
                The link may have expired or already been used.
              </p>
              <Link
                to="/login"
                className="btn-secondary inline-block w-full py-2.5"
              >
                Back to sign in
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
