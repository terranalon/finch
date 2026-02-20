/**
 * Verification Pending Page
 *
 * Shown after registration to prompt user to check their email.
 */

import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { AuthLayout } from '../components/auth';
import { resendVerification } from '../lib/api';

export default function VerificationPending() {
  const [resending, setResending] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

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
    <AuthLayout page="verification-pending">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
          Check your email
        </h2>
        <p className="text-[13px] text-[var(--text-secondary)]">
          We&apos;ve sent a verification link to:
        </p>
        {email && (
          <p className="font-medium text-[var(--text-primary)] mt-1">{email}</p>
        )}
        <p className="text-[13px] text-[var(--text-tertiary)] mt-1">
          Click the link in the email to verify your account.
        </p>

        <div className="py-6">
          <svg
            className="mx-auto h-16 w-16 text-accent"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
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
          <div className="rounded-md bg-[var(--positive-bg)] p-4 mb-4">
            <p className="text-sm text-[var(--positive)]">{message}</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-[var(--negative-bg)] p-4 mb-4">
            <p className="text-sm text-[var(--negative)]">{error}</p>
          </div>
        )}

        <button
          onClick={handleResend}
          disabled={resending || !email}
          className="btn-secondary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {resending ? 'Sending...' : 'Resend verification email'}
        </button>

        <p className="text-[13px] text-[var(--text-tertiary)] mt-5">
          Already verified?{' '}
          <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
