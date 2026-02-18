import { usePortfolioPage } from '../../contexts/PortfolioPageContext';
import { PlusIcon } from './icons';
import { PortfolioCard } from './PortfolioCard';

export function PortfolioGridView({ onCreateNew }) {
  const { portfolios } = usePortfolioPage();

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))' }}>
      {portfolios.map((portfolio) => (
        <PortfolioCard key={portfolio.id} portfolio={portfolio} />
      ))}

      <button
        onClick={onCreateNew}
        className="min-h-[180px] bg-transparent border-2 border-dashed border-[var(--border-primary)] rounded-xl flex flex-col items-center justify-center gap-2.5 text-[var(--text-tertiary)] text-[13px] font-medium hover:border-accent hover:text-accent hover:bg-accent/[0.04] transition-all cursor-pointer"
      >
        <PlusIcon className="w-5 h-5" />
        Create New Portfolio
      </button>
    </div>
  );
}
