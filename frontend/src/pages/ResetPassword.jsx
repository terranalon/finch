/**
 * Reset Password Page
 *
 * Allows users to set a new password using the token from their email.
 */

import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { AuthLayout, AuthAlert, SuccessIcon, ErrorIcon } from '../components/auth';
import { resetPassword } from '../lib/api';

const INPUT_CLASS =
  'w-full px-3 py-2 text-sm border border-[var(--border-primary)] placeholder-[var(--text-tertiary)] text-[var(--text-primary)] bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors';

export default function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    if (!token) {
      setError('Invalid reset link');
      return;
    }

    setLoading(true);

    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Password reset failed');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthLayout page="reset-password">
        <div className="text-center">
          <div className="py-4">
            <ErrorIcon />
          </div>

          <h2 className="text-xl font-semibold text-[var(--text-primary)]">
            Invalid reset link
          </h2>
          <p className="text-[var(--text-secondary)] mt-2">
            This password reset link is invalid or has expired.
          </p>

          <Link
            to="/forgot-password"
            className="btn-primary inline-block w-full py-2.5 mt-6"
          >
            Request a new link
          </Link>
        </div>
      </AuthLayout>
    );
  }

  if (success) {
    return (
      <AuthLayout page="reset-password">
        <div className="text-center">
          <div className="py-4">
            <SuccessIcon />
          </div>

          <h2 className="text-xl font-semibold text-[var(--text-primary)]">
            Password reset successful!
          </h2>
          <p className="text-[var(--text-secondary)] mt-2">
            Your password has been changed. You can now sign in with your new password.
          </p>

          <Link
            to="/login"
            className="btn-primary inline-block w-full py-2.5 mt-6"
          >
            Sign in
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout page="reset-password">
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
        Set new password
      </h2>
      <p className="text-[13px] text-[var(--text-secondary)] mb-6">
        Enter your new password below.
      </p>

      <form onSubmit={handleSubmit}>
        <AuthAlert message={error} />

        <div className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
              New password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={INPUT_CLASS}
              placeholder="At least 8 characters"
            />
            <p className="mt-1 text-xs text-[var(--text-tertiary)]">
              Must contain uppercase, lowercase, and a number
            </p>
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
              Confirm new password
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={INPUT_CLASS}
              placeholder="Confirm your password"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-2.5 mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Resetting...' : 'Reset password'}
        </button>
      </form>
    </AuthLayout>
  );
}
