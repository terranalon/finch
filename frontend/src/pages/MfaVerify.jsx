/**
 * MFA Verify Page
 *
 * Handles MFA verification during login flow.
 */

import { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts';
import { AuthLayout } from '../components/auth';
import { verifyMfa, sendMfaEmailCode } from '../lib/api';

function getCodeLabel(method) {
  switch (method) {
    case 'totp':
      return 'Authenticator code';
    case 'email':
      return 'Email code';
    default:
      return 'Verification code';
  }
}

function EmailOtpStatus({ emailSent, sendingCode, resendCooldown, onSendCode }) {
  // Sending initial code
  if (!emailSent && sendingCode) {
    return (
      <div className="flex items-center justify-center gap-2 text-[var(--text-secondary)]">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-accent" />
        <span className="text-sm">Sending code to your email...</span>
      </div>
    );
  }

  // Code sent - show resend button
  if (emailSent) {
    let buttonText = 'Resend code';
    if (resendCooldown > 0) {
      buttonText = `Resend code (${resendCooldown}s)`;
    } else if (sendingCode) {
      buttonText = 'Sending...';
    }

    return (
      <button
        type="button"
        onClick={onSendCode}
        disabled={sendingCode || resendCooldown > 0}
        className="text-accent hover:text-accent-hover text-sm font-medium disabled:opacity-50"
      >
        {buttonText}
      </button>
    );
  }

  // Initial state - show send button
  return (
    <button
      type="button"
      onClick={onSendCode}
      disabled={sendingCode}
      className="text-accent hover:text-accent-hover text-sm font-medium disabled:opacity-50"
    >
      {sendingCode ? 'Sending...' : 'Send code to my email'}
    </button>
  );
}

export default function MfaVerify() {
  const [code, setCode] = useState('');
  const [method, setMethod] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [showMethodSelector, setShowMethodSelector] = useState(false);

  const location = useLocation();
  const navigate = useNavigate();

  const { tempToken, methods, email, primaryMethod } = location.state || {};

  // Redirect if no temp token
  useEffect(() => {
    if (!tempToken) {
      navigate('/login');
    }
  }, [tempToken, navigate]);

  // Set default method based on primaryMethod from backend
  useEffect(() => {
    if (methods && methods.length > 0 && !method) {
      if (primaryMethod && methods.includes(primaryMethod)) {
        setMethod(primaryMethod);
      } else {
        setMethod(methods[0]);
      }
    }
  }, [methods, method, primaryMethod]);

  // Cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleSendEmailCode = async () => {
    if (resendCooldown > 0) return;

    setSendingCode(true);
    setError('');
    setMessage('');

    try {
      await sendMfaEmailCode(tempToken);
      setEmailSent(true);
      setMessage('Verification code sent to your email');
      setResendCooldown(60);
    } catch (err) {
      setError(err.message || 'Failed to send code');
    } finally {
      setSendingCode(false);
    }
  };

  // Auto-send email code when email is the primary method
  useEffect(() => {
    const shouldAutoSend =
      method === 'email' &&
      !emailSent &&
      !sendingCode &&
      tempToken &&
      (methods?.length === 1 || primaryMethod === 'email');

    if (shouldAutoSend) {
      handleSendEmailCode();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [method, emailSent, tempToken]);

  // Get setUserFromMfa from context
  const { setUserFromMfa } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const result = await verifyMfa(tempToken, code, method);
      // MFA successful, tokens are set in api.js
      // Set user in context
      if (result.user) {
        setUserFromMfa(result.user);
      }
      navigate('/');
    } catch (err) {
      setError(err.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  if (!tempToken) {
    return null;
  }

  return (
    <AuthLayout page="mfa-verify">
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
        Two-factor authentication
      </h2>
      <p className="text-[13px] text-[var(--text-secondary)] mb-6">
        Enter your verification code to continue
      </p>

      <form onSubmit={handleSubmit}>
        {error && (
          <div className="rounded-md bg-[var(--negative-bg)] p-4 mb-4" role="alert">
            <p className="text-sm text-[var(--negative)]">{error}</p>
          </div>
        )}

        {/* Method selector - only show if user wants to switch */}
        {methods && methods.length > 1 && showMethodSelector && (
          <div className="mb-4">
            <label className="block text-[13px] font-medium text-[var(--text-primary)] mb-2">
              Verification method
            </label>
            <div className="flex gap-2">
              {methods.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    setMethod(m);
                    setCode('');
                    setError('');
                    setMessage('');
                    if (m !== 'email') {
                      setEmailSent(false);
                    }
                  }}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                    method === m
                      ? 'bg-accent text-white'
                      : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--border-primary)]'
                  }`}
                >
                  {m === 'totp' ? 'Authenticator' : 'Email'}
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <label htmlFor="code" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
            {getCodeLabel(method)}
          </label>
          <input
            id="code"
            name="code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-[var(--border-primary)] placeholder-[var(--text-tertiary)] text-[var(--text-primary)] bg-white rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors text-center text-2xl tracking-widest"
            placeholder="000000"
            maxLength={method === 'recovery' ? 14 : 6}
          />
          {method === 'email' && (
            <div className="text-center mt-2">
              <EmailOtpStatus
                emailSent={emailSent}
                sendingCode={sendingCode}
                resendCooldown={resendCooldown}
                onSendCode={handleSendEmailCode}
              />
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !code}
          className="btn-primary w-full py-2.5 mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Verifying...' : 'Verify'}
        </button>
      </form>

      <div className="text-center mt-5 space-y-2">
        <p className="text-[13px] text-[var(--text-tertiary)]">
          Lost access to your authenticator?
        </p>
        <button
          type="button"
          onClick={() => {
            setMethod('recovery');
            setCode('');
            setError('');
            setMessage('');
          }}
          className="text-accent hover:text-accent-hover text-[13px] font-medium"
        >
          Use a recovery code
        </button>
      </div>

      {methods && methods.length > 1 && !showMethodSelector && (
        <div className="text-center mt-3">
          <button
            type="button"
            onClick={() => setShowMethodSelector(true)}
            className="text-accent hover:text-accent-hover text-[13px] font-medium"
          >
            Use a different verification method
          </button>
        </div>
      )}

      <div className="text-center mt-3">
        <Link
          to="/login"
          className="text-[13px] text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
        >
          &larr; Back to sign in
        </Link>
      </div>
    </AuthLayout>
  );
}
