/**
 * Change Password Component
 *
 * Modal for changing password from Settings page.
 */

import { useState } from 'react';
import { changePassword } from '../lib/api';

export function ChangePassword({ onComplete, onCancel }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      await changePassword(currentPassword, newPassword);
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="space-y-6">
        <div className="text-center py-4">
          <svg
            className="mx-auto h-12 w-12 text-positive"
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
        <div className="text-center">
          <h3 className="text-lg font-medium text-[var(--text-primary)]">
            Password changed!
          </h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Your password has been updated successfully.
          </p>
        </div>
        <button
          onClick={() => onComplete?.()}
          className="w-full px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors"
        >
          Done
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-medium text-[var(--text-primary)]">
          Change Password
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          Enter your current password and choose a new one
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
            <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            Current password
          </label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            New password
          </label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            required
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
          <p className="mt-1 text-xs text-[var(--text-tertiary)]">
            Must contain uppercase, lowercase, and a number
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            Confirm new password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            required
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !currentPassword || !newPassword || !confirmPassword}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            {loading ? 'Changing...' : 'Change Password'}
          </button>
        </div>
      </form>
    </div>
  );
}
