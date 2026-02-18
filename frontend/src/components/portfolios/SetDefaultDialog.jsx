export function SetDefaultDialog({ isOpen, onClose, portfolio, onConfirm }) {
  if (!isOpen || !portfolio) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-xl p-6 max-w-sm w-full shadow-xl">
          <h3 className="text-base font-semibold text-[var(--text-primary)] mb-2">
            Set as Default Portfolio
          </h3>
          <p className="text-sm text-[var(--text-secondary)] mb-5 leading-relaxed">
            Make <strong className="text-[var(--text-primary)]">{portfolio.name}</strong> your default
            portfolio? It will be selected automatically when you log in.
          </p>
          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={() => { onConfirm(portfolio.id); onClose(); }}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-accent text-white hover:bg-accent/90 transition-colors cursor-pointer"
            >
              Set as Default
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
