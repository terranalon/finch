/**
 * Verify Email Page
 *
 * Handles email verification when user clicks the link from their email.
 */

import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { AuthLayout, SuccessIcon, ErrorIcon } from '../components/auth';
import { verifyEmail } from '../lib/api';

export default function VerifyEmail() {
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [error, setError] = useState('');

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
    <AuthLayout page="verify-email">
      <div className="text-center">
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
              <SuccessIcon />
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
              <ErrorIcon />
            </div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Verification failed
            </h2>
            <p className="text-[var(--text-secondary)]">{error}</p>
            <div className="space-y-3">
              <p className="text-[13px] text-[var(--text-tertiary)]">
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
    </AuthLayout>
  );
}
