import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../lib/api';
import { AuthLayout, AuthAlert } from '../components/auth';

export default function Register() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      await register(email, password, username);
      navigate('/verification-pending', { state: { email } });
    } catch (err) {
      if (err.details?.length > 0) {
        const mapped = {};
        for (const detail of err.details) {
          if (detail.field) {
            mapped[detail.field] = detail.message;
          }
        }
        if (Object.keys(mapped).length > 0) {
          setFieldErrors(mapped);
        } else {
          setError(err.message || 'Registration failed');
        }
      } else {
        const fieldMap = {
          'Email already registered': 'email',
          'Username already taken': 'username',
        };
        const targetField = fieldMap[err.message];
        if (targetField) {
          setFieldErrors({ [targetField]: err.message });
        } else {
          setError(err.message || 'Registration failed');
        }
      }
    } finally {
      setLoading(false);
    }
  };

  function FieldError({ message }) {
    if (!message) return null;
    return (
      <p className="mt-1 text-[11px] text-[var(--negative)]" role="alert">
        {message}
      </p>
    );
  }

  return (
    <AuthLayout page="register">
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">
        Create your account
      </h2>

      <form onSubmit={handleSubmit}>
        <AuthAlert message={error} />

        <div className="space-y-4">
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
              onChange={(e) => {
                setEmail(e.target.value);
                if (fieldErrors.email) {
                  setFieldErrors((prev) => { const { email: _, ...rest } = prev; return rest; });
                }
              }}
              className={`w-full px-3 py-2 text-sm border text-[var(--text-primary)] bg-white placeholder-[var(--text-tertiary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors ${
                fieldErrors.email ? 'border-[var(--negative)]' : 'border-[var(--border-primary)]'
              }`}
              placeholder="you@example.com"
            />
            <FieldError message={fieldErrors.email} />
          </div>

          <div>
            <label htmlFor="username" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
              Username
            </label>
            <input
              id="username"
              name="username"
              type="text"
              autoComplete="username"
              required
              minLength={3}
              maxLength={30}
              pattern="[A-Za-z0-9_]+"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (fieldErrors.username) {
                  setFieldErrors((prev) => { const { username: _, ...rest } = prev; return rest; });
                }
              }}
              className={`w-full px-3 py-2 text-sm border text-[var(--text-primary)] bg-white placeholder-[var(--text-tertiary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors ${
                fieldErrors.username ? 'border-[var(--negative)]' : 'border-[var(--border-primary)]'
              }`}
              placeholder="your_username"
            />
            <p className="mt-1 text-[11px] text-[var(--text-tertiary)]">
              3-30 characters: letters, numbers, and underscores
            </p>
            <FieldError message={fieldErrors.username} />
          </div>

          <div>
            <label htmlFor="password" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (fieldErrors.password) {
                  setFieldErrors((prev) => { const { password: _, ...rest } = prev; return rest; });
                }
              }}
              className={`w-full px-3 py-2 text-sm border text-[var(--text-primary)] bg-white placeholder-[var(--text-tertiary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors ${
                fieldErrors.password ? 'border-[var(--negative)]' : 'border-[var(--border-primary)]'
              }`}
              placeholder="At least 8 characters"
            />
            <p className="mt-1 text-[11px] text-[var(--text-tertiary)]">
              Must contain uppercase, lowercase, and a number
            </p>
            <FieldError message={fieldErrors.password} />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-[13px] font-medium text-[var(--text-primary)] mb-1">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-[var(--border-primary)] text-[var(--text-primary)] bg-white placeholder-[var(--text-tertiary)] rounded-md focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-colors"
              placeholder="Confirm your password"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-2.5 mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Creating account...' : 'Create account'}
        </button>
      </form>

      <p className="text-center text-[13px] text-[var(--text-tertiary)] mt-5">
        Already have an account?{' '}
        <Link to="/login" className="text-accent hover:text-accent-hover font-medium">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
