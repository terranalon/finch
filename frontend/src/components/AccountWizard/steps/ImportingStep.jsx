export function ImportingStep({ message = 'Importing your data...' }) {
  return (
    <div className="max-w-lg mx-auto text-center py-16">
      <div className="size-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-6" />
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
        {message}
      </h2>
      <p className="text-gray-500 dark:text-gray-400">
        Please don't close this window.
      </p>
    </div>
  );
}
