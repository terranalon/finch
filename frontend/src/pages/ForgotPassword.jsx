/**
 * Forgot Password Page
 *
 * Allows users to request a password reset email.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthLayout, AuthAlert, EmailIcon } from '../components/auth';
import { forgotPassword } from '../lib/api';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
      <AuthLayout page="forgot-password">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
            Check your email
          </h2>

          <div className="py-4">
            <EmailIcon />
          </div>

          <p className="text-[var(--text-secondary)]">
            If an account exists for <strong>{email}</strong>, we&apos;ve sent a password reset link.
          </p>

          <p className="text-[13px] text-[var(--text-tertiary)] mt-2">
            The link will expire in 1 hour.
          </p>

          <Link
            to="/login"
            className="btn-secondary inline-block w-full py-2.5 mt-6"
          >
            Back to sign in
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout page="forgot-password">
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
        Reset your password
      </h2>
      <p className="text-[13px] text-[var(--text-secondary)] mb-6">
        Enter your email address and we&apos;ll send you a link to reset your password.
      </p>

      <form onSubmit={handleSubmit}>
        <AuthAlert message={error} />

        <div>
          <label htmlFor="email" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
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
            className="w-full px-3 py-2 text-sm border border-[var(--border-primary)] placeholder-[var(--text-tertiary)] text-[var(--text-primary)] bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors"
            placeholder="you@example.com"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-2.5 mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Sending...' : 'Send reset link'}
        </button>
      </form>

      <p className="text-center text-[13px] text-[var(--text-tertiary)] mt-5">
        Remember your password?{' '}
        <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
