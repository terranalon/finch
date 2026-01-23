/**
 * Verification Pending Page
 *
 * Shown after registration to prompt user to check their email.
 */

import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useTheme } from '../contexts';
import { FinchIcon, ThemeToggle } from '../components/ui';
import { resendVerification } from '../lib/api';

export default function VerificationPending() {
  const [resending, setResending] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const email = location.state?.email || '';

  const handleResend = async () => {
    if (!email) {
      setError('No email address available. Please register again.');
      return;
    }

    setResending(true);
    setError('');
    setMessage('');

    try {
      await resendVerification(email);
      setMessage('Verification email sent! Check your inbox.');
    } catch (err) {
      setError(err.message || 'Failed to resend verification email');
    } finally {
      setResending(false);
    }
  };

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
          <div className="mt-4 space-y-2">
            <p className="text-[var(--text-secondary)]">
              We&apos;ve sent a verification link to:
            </p>
            {email && (
              <p className="font-medium text-[var(--text-primary)]">{email}</p>
            )}
            <p className="text-sm text-[var(--text-tertiary)]">
              Click the link in the email to verify your account.
            </p>
          </div>
        </div>

        {/* Email icon */}
        <div className="py-8">
          <svg
            className="mx-auto h-24 w-24 text-accent"
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

        {message && (
          <div className="rounded-md bg-positive-bg dark:bg-positive-bg-dark p-4">
            <p className="text-sm text-positive dark:text-positive-dark">{message}</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-4">
            <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <button
            onClick={handleResend}
            disabled={resending || !email}
            className="btn-secondary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resending ? 'Sending...' : 'Resend verification email'}
          </button>

          <p className="text-sm text-[var(--text-tertiary)]">
            Already verified?{' '}
            <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
