/**
 * Verification Pending Page
 *
 * Shown after registration to prompt user to check their email.
 */

import { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { AuthLayout, AuthAlert, EmailIcon } from '../components/auth';
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
          <EmailIcon />
        </div>

        <AuthAlert message={message} variant="success" />
        <AuthAlert message={error} />

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
