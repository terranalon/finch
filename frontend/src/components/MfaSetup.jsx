/**
 * MFA Setup Components
 *
 * Components for setting up and managing MFA (TOTP and Email OTP).
 */

import { useState, useEffect } from 'react';
import { setupTotp, confirmTotp, setupEmailOtp, disableMfa, disableMfaMethod, regenerateRecoveryCodes } from '../lib/api';

// Reusable code input component for verification codes
export function CodeInput({ value, onChange, placeholder = '000000', maxLength = 6 }) {
  return (
    <input
      type="text"
      inputMode="numeric"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      maxLength={maxLength}
      className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
    />
  );
}

// Reusable error alert component
export function ErrorAlert({ message }) {
  if (!message) return null;
  return (
    <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
      <p className="text-sm text-negative dark:text-negative-dark">{message}</p>
    </div>
  );
}

// Reusable form buttons component
export function FormButtons({ onCancel, submitLabel, loading, disabled, variant = 'primary' }) {
  const submitClassName = variant === 'danger'
    ? 'flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-negative text-white hover:bg-negative/90 transition-colors disabled:opacity-50'
    : 'flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50';

  return (
    <div className="flex gap-3">
      <button
        type="button"
        onClick={onCancel}
        className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={loading || disabled}
        className={submitClassName}
      >
        {submitLabel}
      </button>
    </div>
  );
}

// Recovery Codes Display
export function RecoveryCodesDisplay({ codes, onClose }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(codes.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const content = `Finch Portfolio Recovery Codes
Generated: ${new Date().toLocaleString()}

Keep these codes in a safe place. Each code can only be used once.

${codes.join('\n')}`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'finch-recovery-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="rounded-md bg-amber-50 dark:bg-amber-900/20 p-4">
        <p className="text-sm text-amber-800 dark:text-amber-200">
          <strong>Important:</strong> Save these recovery codes in a secure place.
          You&apos;ll need them if you lose access to your authenticator.
          Each code can only be used once.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 p-4 bg-[var(--bg-tertiary)] rounded-lg font-mono text-sm">
        {codes.map((code, i) => (
          <div key={i} className="text-[var(--text-primary)]">{code}</div>
        ))}
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleCopy}
          className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
        >
          {copied ? 'Copied!' : 'Copy Codes'}
        </button>
        <button
          onClick={handleDownload}
          className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
        >
          Download
        </button>
      </div>

      {onClose && (
        <button
          onClick={onClose}
          className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors"
        >
          I&apos;ve saved my codes
        </button>
      )}
    </div>
  );
}

// TOTP Setup Component
export function TotpSetup({ onComplete, onCancel, requireVerification = false }) {
  const [step, setStep] = useState('loading'); // loading, verify-existing, scan, verify, codes
  const [secret, setSecret] = useState('');
  const [qrCode, setQrCode] = useState('');
  const [code, setCode] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Start setup on mount
  useEffect(() => {
    async function startSetup() {
      try {
        const data = await setupTotp();
        setSecret(data.secret);
        setQrCode(data.qr_code_base64);
        setStep(requireVerification ? 'verify-existing' : 'scan');
      } catch (err) {
        setError(err.message || 'Failed to start TOTP setup');
        setStep('error');
      }
    }
    startSetup();
  }, [requireVerification]);

  const handleVerify = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await confirmTotp(secret, code, requireVerification ? verificationCode : null);
      if (data.recovery_codes) {
        setRecoveryCodes(data.recovery_codes);
        setStep('codes');
      } else {
        onComplete?.();
      }
    } catch (err) {
      setError(err.message || 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'loading') {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
      </div>
    );
  }

  if (step === 'error') {
    return (
      <div className="space-y-4">
        <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-4">
          <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
        </div>
        <button
          onClick={onCancel}
          className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
        >
          Close
        </button>
      </div>
    );
  }

  if (step === 'codes') {
    return (
      <RecoveryCodesDisplay
        codes={recoveryCodes}
        onClose={() => onComplete?.()}
      />
    );
  }

  // Step for verifying existing MFA when adding TOTP as second method
  if (step === 'verify-existing') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <h3 className="text-lg font-medium text-[var(--text-primary)]">
            Verify your identity
          </h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Enter the code sent to your email to add a new authentication method.
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
            <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            Email verification code
          </label>
          <input
            type="text"
            inputMode="numeric"
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
            placeholder="000000"
            maxLength={6}
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => setStep('scan')}
            disabled={verificationCode.length !== 6}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-medium text-[var(--text-primary)]">
          Set up authenticator app
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.)
        </p>
      </div>

      {/* QR Code */}
      <div className="flex justify-center">
        <div className="p-4 bg-white rounded-lg">
          <img
            src={`data:image/png;base64,${qrCode}`}
            alt="QR Code for TOTP"
            className="w-48 h-48"
          />
        </div>
      </div>

      {/* Manual entry key */}
      <div className="text-center">
        <p className="text-xs text-[var(--text-tertiary)] mb-1">
          Can&apos;t scan? Enter this code manually:
        </p>
        <code className="px-3 py-1.5 bg-[var(--bg-tertiary)] rounded text-sm font-mono text-[var(--text-primary)]">
          {secret}
        </code>
      </div>

      {/* Verification form */}
      <form onSubmit={handleVerify} className="space-y-4">
        {error && (
          <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
            <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            Enter the 6-digit code from your app
          </label>
          <input
            type="text"
            inputMode="numeric"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="000000"
            maxLength={6}
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || code.length !== 6}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            {loading ? 'Verifying...' : 'Verify'}
          </button>
        </div>
      </form>
    </div>
  );
}

// Email OTP Setup Component
export function EmailOtpSetup({ onComplete, onCancel, requireVerification = false }) {
  const [step, setStep] = useState(requireVerification ? 'verify' : 'confirm'); // verify, confirm, codes
  const [verificationCode, setVerificationCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleEnable = async () => {
    setError('');
    setLoading(true);

    try {
      const data = await setupEmailOtp(requireVerification ? verificationCode : null);
      if (data.recovery_codes) {
        setRecoveryCodes(data.recovery_codes);
        setStep('codes');
      } else {
        onComplete?.();
      }
    } catch (err) {
      setError(err.message || 'Failed to enable Email OTP');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'codes') {
    return (
      <RecoveryCodesDisplay
        codes={recoveryCodes}
        onClose={() => onComplete?.()}
      />
    );
  }

  // Step for verifying existing MFA when adding Email OTP as second method
  if (step === 'verify') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <h3 className="text-lg font-medium text-[var(--text-primary)]">
            Verify your identity
          </h3>
          <p className="text-sm text-[var(--text-secondary)] mt-1">
            Enter your authenticator code to add Email OTP.
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
            <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            Authenticator code
          </label>
          <input
            type="text"
            inputMode="numeric"
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
            placeholder="000000"
            maxLength={6}
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleEnable}
            disabled={loading || verificationCode.length !== 6}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            {loading ? 'Enabling...' : 'Enable Email OTP'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-medium text-[var(--text-primary)]">
          Enable Email OTP
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          We&apos;ll send a one-time code to your email each time you log in.
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
          <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleEnable}
          disabled={loading}
          className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
        >
          {loading ? 'Enabling...' : 'Enable Email OTP'}
        </button>
      </div>
    </div>
  );
}

// Disable MFA Component
export function DisableMfa({ onComplete, onCancel }) {
  const [method, setMethod] = useState('totp'); // totp, recovery
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleDisable = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const mfaCode = method === 'totp' ? code : null;
      const recoveryCode = method === 'recovery' ? code : null;
      await disableMfa(mfaCode, recoveryCode);
      onComplete?.();
    } catch (err) {
      setError(err.message || 'Failed to disable MFA');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-medium text-[var(--text-primary)]">
          Disable Two-Factor Authentication
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          Enter your verification code to disable MFA
        </p>
      </div>

      <form onSubmit={handleDisable} className="space-y-4">
        {error && (
          <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
            <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
          </div>
        )}

        {/* Method selector */}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setMethod('totp');
              setCode('');
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              method === 'totp'
                ? 'bg-accent text-white'
                : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
            }`}
          >
            Authenticator
          </button>
          <button
            type="button"
            onClick={() => {
              setMethod('recovery');
              setCode('');
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              method === 'recovery'
                ? 'bg-accent text-white'
                : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)]'
            }`}
          >
            Recovery Code
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            {method === 'totp' ? 'Authenticator code' : 'Recovery code'}
          </label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder={method === 'totp' ? '000000' : 'XXXX-XXXX-XXXX'}
            maxLength={method === 'totp' ? 6 : 14}
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !code}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-negative text-white hover:bg-negative/90 transition-colors disabled:opacity-50"
          >
            {loading ? 'Disabling...' : 'Disable MFA'}
          </button>
        </div>
      </form>
    </div>
  );
}

// Regenerate Recovery Codes Component
export function RegenerateRecoveryCodes({ onComplete, onCancel }) {
  const [step, setStep] = useState('confirm'); // confirm, verify, codes
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegenerate = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await regenerateRecoveryCodes(code);
      setRecoveryCodes(data.recovery_codes);
      setStep('codes');
    } catch (err) {
      setError(err.message || 'Failed to regenerate codes');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'codes') {
    return (
      <RecoveryCodesDisplay
        codes={recoveryCodes}
        onClose={() => onComplete?.()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-medium text-[var(--text-primary)]">
          Regenerate Recovery Codes
        </h3>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          This will invalidate all existing recovery codes.
          Enter your authenticator code to continue.
        </p>
      </div>

      <form onSubmit={handleRegenerate} className="space-y-4">
        {error && (
          <div className="rounded-md bg-negative-bg dark:bg-negative-bg-dark p-3">
            <p className="text-sm text-negative dark:text-negative-dark">{error}</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
            Authenticator code
          </label>
          <input
            type="text"
            inputMode="numeric"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="000000"
            maxLength={6}
            className="w-full px-3 py-2.5 rounded-lg text-sm bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent"
          />
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || code.length !== 6}
            className="flex-1 px-4 py-2.5 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-50"
          >
            {loading ? 'Regenerating...' : 'Regenerate Codes'}
          </button>
        </div>
      </form>
    </div>
  );
}

// Disable Individual MFA Method Component
export function DisableMfaMethod({ method, onComplete, onCancel }) {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await disableMfaMethod(method, code);
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const methodLabel = method === 'totp' ? 'Authenticator App' : 'Email OTP';

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold text-[var(--text-primary)]">
        Disable {methodLabel}
      </h3>

      <p className="text-sm text-[var(--text-secondary)]">
        Enter your authenticator code or recovery code to disable this method.
      </p>

      <ErrorAlert message={error} />

      <div>
        <label className="block text-sm font-medium text-[var(--text-primary)] mb-1.5">
          Verification code
        </label>
        <CodeInput
          value={code}
          onChange={setCode}
          placeholder="Enter code"
          maxLength={14}
        />
      </div>

      <FormButtons
        onCancel={onCancel}
        submitLabel={loading ? 'Disabling...' : 'Disable'}
        loading={loading}
        disabled={!code}
        variant="danger"
      />
    </form>
  );
}
