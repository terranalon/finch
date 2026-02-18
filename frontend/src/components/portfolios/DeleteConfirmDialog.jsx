import { useState, useEffect } from 'react';
import { usePortfolioPage } from '../../contexts/PortfolioPageContext';

export function DeleteConfirmDialog({ isOpen, onClose, portfolio }) {
  const { deletePortfolio, fetchDeletionPreview } = usePortfolioPage();
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!isOpen || !portfolio) return;

    setPreview(null);
    setPreviewError(null);

    if (portfolio.is_default) return;

    setPreviewLoading(true);
    fetchDeletionPreview(portfolio.id)
      .then(setPreview)
      .catch((err) => setPreviewError(err.message))
      .finally(() => setPreviewLoading(false));
  }, [isOpen, portfolio, fetchDeletionPreview]);

  const handleConfirm = async () => {
    setDeleting(true);
    const ok = await deletePortfolio(portfolio.id);
    setDeleting(false);
    if (ok) onClose();
  };

  if (!isOpen || !portfolio) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-xl p-6 max-w-md w-full shadow-xl">
          <h3 className="text-base font-semibold text-[var(--text-primary)] mb-2">
            Delete Portfolio
          </h3>

          {portfolio.is_default ? (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm mb-5">
              Please set another portfolio as default before deleting this one.
            </div>
          ) : previewLoading ? (
            <p className="text-sm text-[var(--text-secondary)] mb-5">Loading preview...</p>
          ) : previewError ? (
            <p className="text-sm text-[var(--negative)] mb-5">{previewError}</p>
          ) : preview ? (
            <div className="space-y-3 mb-5">
              {preview.exclusive_accounts?.length > 0 && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                  <p className="text-xs font-semibold text-[var(--negative)] uppercase tracking-wide mb-1.5">
                    Will be permanently deleted
                  </p>
                  {preview.exclusive_accounts.map((acc) => (
                    <p key={acc.id} className="text-sm text-[var(--text-secondary)]">
                      {acc.name} — {acc.institution}
                    </p>
                  ))}
                </div>
              )}
              {preview.shared_accounts?.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <p className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-1.5">
                    Will be unlinked only
                  </p>
                  {preview.shared_accounts.map((acc) => (
                    <p key={acc.id} className="text-sm text-[var(--text-secondary)]">
                      {acc.name}
                    </p>
                  ))}
                </div>
              )}
              {!preview.exclusive_accounts?.length && !preview.shared_accounts?.length && (
                <p className="text-sm text-[var(--text-secondary)]">
                  This portfolio has no accounts and will be permanently deleted.
                </p>
              )}
            </div>
          ) : null}

          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              disabled={deleting}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--border-primary)] transition-colors cursor-pointer disabled:opacity-50"
            >
              Cancel
            </button>
            {!portfolio.is_default && (
              <button
                onClick={handleConfirm}
                disabled={deleting || previewLoading}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--negative)] text-white hover:bg-red-600 transition-colors cursor-pointer disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete Portfolio'}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
