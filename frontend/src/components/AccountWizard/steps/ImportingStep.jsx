export function ImportingStep({ message = 'Importing your data...' }) {
  return (
    <div className="max-w-lg mx-auto text-center py-16">
      <div className="size-16 border-4 border-accent-200 border-t-accent rounded-full animate-spin mx-auto mb-6" />
      <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
        {message}
      </h2>
      <p className="text-[var(--text-tertiary)]">
        Please don't close this window.
      </p>
    </div>
  );
}
