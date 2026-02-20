import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts';
import { AuthLayout } from '../components/auth';

export default function Login() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login(identifier, password);

      if (result.mfa_required) {
        navigate('/mfa-verify', {
          state: {
            tempToken: result.temp_token,
            methods: result.methods,
            identifier,
            primaryMethod: result.primary_method,
          },
        });
        return;
      }

      navigate('/');
    } catch (err) {
      if (err.code === 'email_not_verified') {
        navigate('/verification-pending', { state: { email: err.email || identifier } });
        return;
      }
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError('');
    setLoading(true);

    try {
      const result = await login('demo@finch.com', 'Demo1234');
      if (result.mfa_required) {
        setError('Demo account has MFA enabled. Please use regular login.');
        return;
      }
      navigate('/');
    } catch (err) {
      setError('Demo login failed. Make sure the demo user is seeded.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout page="login">
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">
        Sign in to your account
      </h2>

      <form onSubmit={handleSubmit}>
        {error && (
          <div className="rounded-md bg-[var(--negative-bg)] p-4 mb-4" role="alert">
            <p className="text-sm text-[var(--negative)]">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label htmlFor="identifier" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
              Email or username
            </label>
            <input
              id="identifier"
              name="identifier"
              type="text"
              autoComplete="username"
              required
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-[var(--border-primary)] text-[var(--text-primary)] bg-white placeholder-[var(--text-tertiary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors"
              placeholder="Email or username"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor="password" className="text-[13px] font-medium text-[var(--text-primary)]">
                Password
              </label>
              <Link to="/forgot-password" className="text-xs text-accent hover:text-accent-hover font-medium">
                Forgot password?
              </Link>
            </div>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-[var(--border-primary)] text-[var(--text-primary)] bg-white placeholder-[var(--text-tertiary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors"
              placeholder="Enter your password"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-2.5 mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>

      <p className="text-center text-[13px] text-[var(--text-tertiary)] mt-5">
        Don't have an account?{' '}
        <Link to="/register" className="text-accent hover:text-accent-hover font-medium">
          Create one
        </Link>
      </p>

      <p className="text-center text-[13px] text-[var(--text-tertiary)] mt-2">
        Just exploring?{' '}
        <button
          type="button"
          onClick={handleDemoLogin}
          disabled={loading}
          className="text-accent hover:text-accent-hover font-medium bg-transparent border-none cursor-pointer p-0 disabled:opacity-50"
        >
          Try the demo
        </button>
      </p>
    </AuthLayout>
  );
}
