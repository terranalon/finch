import { useState } from 'react';
import { PageContainer } from '../components/layout';
import { PortfolioPageProvider } from '../contexts/PortfolioPageContext';
import { usePortfolioManagement } from '../hooks/usePortfolioManagement';
import { PlusIcon } from '../components/portfolios/icons';
import { ViewToggle } from '../components/portfolios/ViewToggle';
import { PortfolioGridView } from '../components/portfolios/PortfolioGridView';
import { PortfolioListView } from '../components/portfolios/PortfolioListView';
import { PortfolioModal } from '../components/portfolios/PortfolioModal';

function SkeletonCards() {
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))' }}>
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl h-[340px] animate-pulse"
        />
      ))}
    </div>
  );
}

export default function Portfolios() {
  const hookData = usePortfolioManagement();
  const { loading, createPortfolio } = hookData;

  const [view, setView] = useState(
    () => localStorage.getItem('finch-portfolio-view') || 'grid'
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleViewChange = (newView) => {
    setView(newView);
    localStorage.setItem('finch-portfolio-view', newView);
  };

  const handleCreateNew = () => setModalOpen(true);

  const handleSaveNew = async (data) => {
    setSaving(true);
    const ok = await createPortfolio(data);
    setSaving(false);
    if (ok) setModalOpen(false);
  };

  return (
    <PortfolioPageProvider value={hookData}>
      <PageContainer width="wide">
        <div className="flex items-start justify-between mb-5 max-w-[1100px] mx-auto">
          <div className="flex flex-col gap-3">
            <div>
              <h1 className="text-[22px] font-semibold text-[var(--text-primary)]">
                Manage Portfolios
              </h1>
              <p className="text-[13px] text-[var(--text-secondary)] mt-0.5">
                Organize your accounts into portfolios
              </p>
            </div>
            <ViewToggle view={view} onViewChange={handleViewChange} />
          </div>

          <button
            onClick={handleCreateNew}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] font-medium bg-accent text-white hover:brightness-110 transition-all cursor-pointer"
          >
            <PlusIcon className="w-4 h-4" />
            New Portfolio
          </button>
        </div>

        {loading && <SkeletonCards />}

        {!loading && view === 'grid' && (
          <PortfolioGridView onCreateNew={handleCreateNew} />
        )}
        {!loading && view === 'list' && (
          <PortfolioListView onCreateNew={handleCreateNew} />
        )}

        <PortfolioModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          portfolio={null}
          onSave={handleSaveNew}
          loading={saving}
        />
      </PageContainer>
    </PortfolioPageProvider>
  );
}
