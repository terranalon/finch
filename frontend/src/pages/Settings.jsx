import { useState, useEffect } from 'react';
import { cn } from '../lib';
import { getMfaStatus, setPrimaryMfaMethod } from '../lib/api';
import { useTheme, useCurrency, useAuth, SUPPORTED_CURRENCIES } from '../contexts';
import { PageContainer } from '../components/layout';
import { Skeleton } from '../components/ui';
import { ChangePassword } from '../components/ChangePassword';
import { TotpSetup, EmailOtpSetup, DisableMfaMethod, RegenerateRecoveryCodes } from '../components/MfaSetup';

// ─── Icons ───────────────────────────────────────────────

function UserCircleIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    </svg>
  );
}

function ShieldCheckIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
    </svg>
  );
}

function BellIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
    </svg>
  );
}

function SunIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
    </svg>
  );
}

function MoonIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
    </svg>
  );
}

function ComputerDesktopIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 12V5.25" />
    </svg>
  );
}

function EnvelopeIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
    </svg>
  );
}

// ─── Constants ────────────────────────────────────────────

const TABS = [
  { id: 'profile', label: 'Profile', icon: UserCircleIcon },
  { id: 'security', label: 'Security', icon: ShieldCheckIcon },
  { id: 'notifications', label: 'Notifications', icon: BellIcon },
];

// ─── Shared Components ───────────────────────────────────

function SettingsCard({ description, children }) {
  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-6 overflow-hidden">
      {description && (
        <p className="text-[13px] text-[var(--text-tertiary)] mb-5 pb-4 border-b border-[var(--border-subtle)]">
          {description}
        </p>
      )}
      {children}
    </div>
  );
}

function FormGroup({ label, hint, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[13px] font-medium text-[var(--text-secondary)]">{label}</label>
      {children}
      {hint && <p className="text-[11px] text-[var(--text-faint)] mt-0.5">{hint}</p>}
    </div>
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative w-[42px] h-6 rounded-full transition-colors shrink-0 cursor-pointer',
        checked ? 'bg-accent' : 'bg-[var(--border-primary)]'
      )}
    >
      <span
        className={cn(
          'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform shadow-sm',
          checked && 'translate-x-[18px]'
        )}
      />
    </button>
  );
}

function ThemeSelector({ value, onChange }) {
  const options = [
    { id: 'light', label: 'Light', icon: SunIcon },
    { id: 'dark', label: 'Dark', icon: MoonIcon },
    { id: 'system', label: 'System', icon: ComputerDesktopIcon },
  ];

  return (
    <div className="flex gap-2.5">
      {options.map((opt) => {
        const Icon = opt.icon;
        const selected = value === opt.id;
        return (
          <button
            key={opt.id}
            onClick={() => onChange(opt.id)}
            className={cn(
              'flex-1 flex flex-col items-center gap-2 py-4 px-3 rounded-[10px] border-2 transition-all cursor-pointer',
              selected
                ? 'border-accent bg-accent/10'
                : 'border-[var(--border-primary)] hover:border-[var(--text-faint)]'
            )}
          >
            <Icon className={cn('w-6 h-6', selected ? 'text-accent' : 'text-[var(--text-tertiary)]')} />
            <span className={cn('text-[13px] font-medium', selected ? 'text-accent font-semibold' : 'text-[var(--text-secondary)]')}>
              {opt.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

// ─── Profile Panel ───────────────────────────────────────

function ProfilePanel({ user, theme, setTheme, currency, setCurrency, updatePreferences }) {
  const [username, setUsername] = useState(user?.username ?? '');

  return (
    <SettingsCard description="Your personal information">
      {/* Personal info */}
      <div className="space-y-4">
        <FormGroup label="Username">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full py-[9px] px-3.5 text-[13px] bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg text-[var(--text-primary)] outline-none transition-colors focus:border-accent focus:shadow-[0_0_0_3px_rgba(59,130,246,0.15)]"
          />
        </FormGroup>
        <FormGroup label="Email Address" hint="Contact support to change your email address">
          <input
            type="email"
            value={user?.email ?? ''}
            disabled
            className="w-full py-[9px] px-3.5 text-[13px] bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg text-[var(--text-tertiary)] outline-none opacity-60 cursor-not-allowed"
          />
        </FormGroup>
      </div>
      <div className="mt-5">
        <button className="inline-flex items-center gap-1.5 px-[18px] py-[9px] rounded-lg text-[13px] font-semibold bg-accent text-white hover:bg-accent-hover transition-colors cursor-pointer">
          Save Changes
        </button>
      </div>

      {/* Appearance */}
      <div className="h-px bg-[var(--border-primary)] my-6" />
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3.5">Appearance</h3>
      <label className="block text-[13px] font-medium text-[var(--text-secondary)] mb-2.5">Theme</label>
      <ThemeSelector value={theme} onChange={setTheme} />

      {/* Preferences */}
      <div className="h-px bg-[var(--border-primary)] my-6" />
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-3.5">Preferences</h3>
      <FormGroup label="Display Currency" hint="All values will be converted to this currency">
        <select
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
          className="w-full py-[9px] px-3.5 text-[13px] bg-[var(--bg-tertiary)] border border-[var(--border-primary)] rounded-lg text-[var(--text-primary)] outline-none cursor-pointer transition-colors focus:border-accent focus:shadow-[0_0_0_3px_rgba(59,130,246,0.15)] appearance-none bg-no-repeat bg-[right_12px_center] bg-[length:12px] bg-[url('data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20fill%3D%22none%22%20stroke%3D%22%2364748B%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m2%204%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')]"
        >
          {SUPPORTED_CURRENCIES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.code} - {c.name}
            </option>
          ))}
        </select>
      </FormGroup>
      <div className="flex items-center justify-between mt-3">
        <div>
          <p className="text-[13px] text-[var(--text-primary)]">Show &quot;All Portfolios&quot; option</p>
          <p className="text-[11px] text-[var(--text-faint)] mt-0.5">
            When enabled, you can view all portfolios combined in the portfolio selector
          </p>
        </div>
        <Toggle
          checked={user?.show_combined_view ?? true}
          onChange={async (checked) => {
            try { await updatePreferences({ show_combined_view: checked }); } catch { /* UI stays in sync */ }
          }}
        />
      </div>
    </SettingsCard>
  );
}

// ─── Security Panel ──────────────────────────────────────

function SecurityPanel() {
  const [modal, setModal] = useState(null);
  const [mfaStatus, setMfaStatus] = useState({
    mfa_enabled: false,
    totp_enabled: false,
    email_otp_enabled: false,
    primary_method: null,
    has_recovery_codes: false,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        setMfaStatus(await getMfaStatus());
      } catch (err) {
        console.error('Failed to fetch MFA status:', err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const refreshMfaStatus = async () => {
    try { setMfaStatus(await getMfaStatus()); } catch { /* ignore */ }
  };

  const handleMfaComplete = async () => {
    await refreshMfaStatus();
    setModal(null);
  };

  const handlePrimaryMethodChange = async (method) => {
    setError('');
    try {
      await setPrimaryMfaMethod(method);
      await refreshMfaStatus();
    } catch (err) {
      setError(err.message);
    }
  };

  const closeModal = () => setModal(null);

  if (loading) {
    return (
      <SettingsCard description="Password and authentication settings">
        <div className="space-y-3">
          <Skeleton className="h-14 w-full rounded-[10px]" />
          <Skeleton className="h-4 w-48 mt-4" />
          <Skeleton className="h-[52px] w-full rounded-[10px]" />
          <Skeleton className="h-[52px] w-full rounded-[10px]" />
        </div>
      </SettingsCard>
    );
  }

  return (
    <>
      <SettingsCard description="Password and authentication settings">
        {/* Password row */}
        <div className="flex items-center justify-between py-3.5 px-4 rounded-[10px] bg-[var(--bg-tertiary)]">
          <div>
            <p className="text-[13px] font-medium text-[var(--text-primary)]">Password</p>
            <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">Change your account password</p>
          </div>
          <button
            onClick={() => setModal('password')}
            className="inline-flex items-center gap-1.5 px-[18px] py-[9px] rounded-lg text-[13px] font-medium bg-[var(--bg-tertiary)] border border-[var(--border-primary)] text-[var(--text-primary)] hover:border-[var(--text-faint)] hover:bg-[var(--bg-secondary)] transition-all cursor-pointer"
          >
            Change Password
          </button>
        </div>

        {/* Two-factor authentication */}
        <p className="text-[13px] font-semibold text-[var(--text-secondary)] mt-[18px] mb-2.5">
          Two-factor authentication
        </p>

        {error && (
          <div className="mb-3 p-3 rounded-lg bg-negative/10 text-negative text-sm">{error}</div>
        )}

        {/* Authenticator App card */}
        <div className="flex items-center justify-between p-3 rounded-[10px] bg-[var(--bg-primary)] border border-[var(--border-primary)]">
          <div className="flex items-center gap-3">
            <div className="w-[34px] h-[34px] rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center">
              <ShieldCheckIcon className="w-4 h-4 text-[var(--text-tertiary)]" />
            </div>
            <div>
              <p className="text-[13px] font-medium text-[var(--text-primary)]">Authenticator App</p>
              <p className="text-[11px] text-[var(--text-tertiary)] mt-px">Use Google Authenticator, Authy, etc.</p>
            </div>
          </div>
          <Toggle
            checked={mfaStatus.totp_enabled}
            onChange={() => setModal(mfaStatus.totp_enabled ? 'disable-totp' : 'totp')}
          />
        </div>

        {/* Email OTP card */}
        <div className="flex items-center justify-between p-3 rounded-[10px] bg-[var(--bg-primary)] border border-[var(--border-primary)] mt-2">
          <div className="flex items-center gap-3">
            <div className="w-[34px] h-[34px] rounded-lg bg-[var(--bg-tertiary)] flex items-center justify-center">
              <EnvelopeIcon className="w-4 h-4 text-[var(--text-tertiary)]" />
            </div>
            <div>
              <p className="text-[13px] font-medium text-[var(--text-primary)]">Email OTP</p>
              <p className="text-[11px] text-[var(--text-tertiary)] mt-px">Codes sent to your email</p>
            </div>
          </div>
          <Toggle
            checked={mfaStatus.email_otp_enabled}
            onChange={() => setModal(mfaStatus.email_otp_enabled ? 'disable-email' : 'email')}
          />
        </div>

        {/* Default method dropdown */}
        {mfaStatus.totp_enabled && mfaStatus.email_otp_enabled && (
          <div className="flex items-center justify-between pt-3 mt-2">
            <label className="text-[13px] text-[var(--text-secondary)]">Default login method</label>
            <select
              value={mfaStatus.primary_method || 'totp'}
              onChange={(e) => handlePrimaryMethodChange(e.target.value)}
              className="px-3 py-1.5 rounded-lg text-[13px] bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-primary)] cursor-pointer"
            >
              <option value="totp">Authenticator App</option>
              <option value="email">Email OTP</option>
            </select>
          </div>
        )}

        {/* Recovery codes */}
        {mfaStatus.has_recovery_codes && (
          <button
            onClick={() => setModal('regenerate')}
            className="block w-full mt-3 py-[9px] rounded-lg text-[13px] font-medium bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-primary)] hover:border-[var(--text-faint)] hover:bg-[var(--bg-tertiary)] transition-all cursor-pointer text-center"
          >
            Regenerate Recovery Codes
          </button>
        )}
      </SettingsCard>

      {/* Modals */}
      {modal && (
        <>
          <div className="fixed inset-0 bg-black/50 z-50" onClick={closeModal} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
              className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl shadow-xl max-w-md w-full p-6"
              onClick={(e) => e.stopPropagation()}
            >
              {modal === 'password' && (
                <ChangePassword onComplete={closeModal} onCancel={closeModal} />
              )}
              {modal === 'totp' && (
                <TotpSetup
                  onComplete={handleMfaComplete}
                  onCancel={closeModal}
                  requireVerification={mfaStatus.email_otp_enabled}
                />
              )}
              {modal === 'email' && (
                <EmailOtpSetup
                  onComplete={handleMfaComplete}
                  onCancel={closeModal}
                  requireVerification={mfaStatus.totp_enabled}
                />
              )}
              {modal === 'disable-totp' && (
                <DisableMfaMethod method="totp" onComplete={handleMfaComplete} onCancel={closeModal} />
              )}
              {modal === 'disable-email' && (
                <DisableMfaMethod method="email" onComplete={handleMfaComplete} onCancel={closeModal} />
              )}
              {modal === 'regenerate' && (
                <RegenerateRecoveryCodes onComplete={closeModal} onCancel={closeModal} />
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}

// ─── Notifications Panel ─────────────────────────────────

function NotificationsPanel() {
  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    priceAlerts: false,
    weeklyDigest: true,
    marketNews: false,
  });

  const update = (key) => (val) => setNotifications((prev) => ({ ...prev, [key]: val }));

  const rows = [
    { key: 'emailAlerts', label: 'Email alerts for significant portfolio changes' },
    { key: 'priceAlerts', label: 'Price alerts for watched assets' },
    { key: 'weeklyDigest', label: 'Weekly portfolio digest' },
    { key: 'marketNews', label: 'Market news and insights' },
  ];

  return (
    <SettingsCard description="Choose what updates you receive">
      <div className="space-y-2.5">
        {rows.map((row) => (
          <div key={row.key} className="flex items-center justify-between py-1">
            <span className="text-[13px] text-[var(--text-primary)]">{row.label}</span>
            <Toggle checked={notifications[row.key]} onChange={update(row.key)} />
          </div>
        ))}
      </div>
    </SettingsCard>
  );
}

// ─── Main Component ──────────────────────────────────────

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const { currency, setCurrency } = useCurrency();
  const { user, updatePreferences } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');

  return (
    <PageContainer className="mx-0 max-w-none">
      <div className="max-w-[780px] w-full mx-auto">
        {/* Page title */}
        <div className="mb-6">
          <h1 className="text-[22px] font-bold tracking-[-0.3px] text-[var(--text-primary)]">Settings</h1>
          <p className="text-[13px] text-[var(--text-tertiary)] mt-0.5">Manage your account settings and preferences</p>
        </div>

        {/* Tab bar */}
        <div className="flex items-center gap-0.5 p-[3px] bg-[var(--bg-tertiary)] rounded-[10px] mb-5">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[13px] font-medium transition-all cursor-pointer whitespace-nowrap',
                  isActive
                    ? 'bg-[var(--bg-secondary)] text-[var(--text-primary)] font-semibold shadow-sm'
                    : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
                )}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab panels */}
        {activeTab === 'profile' && (
          <ProfilePanel
            user={user}
            theme={theme}
            setTheme={setTheme}
            currency={currency}
            setCurrency={setCurrency}
            updatePreferences={updatePreferences}
          />
        )}
        {activeTab === 'security' && <SecurityPanel />}
        {activeTab === 'notifications' && <NotificationsPanel />}
      </div>
    </PageContainer>
  );
}
