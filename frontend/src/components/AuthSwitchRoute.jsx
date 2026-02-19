import { useAuth } from "../contexts";

export default function AuthSwitchRoute({ authenticated, unauthenticated }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    );
  }

  return isAuthenticated ? authenticated : unauthenticated;
}
