function AuthAlert({ message, variant = 'error' }) {
  if (!message) return null;

  const isError = variant === 'error';

  return (
    <div
      className={`rounded-md p-4 mb-4 ${isError ? 'bg-[var(--negative-bg)]' : 'bg-[var(--positive-bg)]'}`}
      role={isError ? 'alert' : 'status'}
    >
      <p className={`text-sm ${isError ? 'text-[var(--negative)]' : 'text-[var(--positive)]'}`}>
        {message}
      </p>
    </div>
  );
}

export default AuthAlert;
