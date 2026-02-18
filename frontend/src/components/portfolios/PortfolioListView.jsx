import { usePortfolioPage } from '../../contexts/PortfolioPageContext';
import { PlusIcon } from './icons';
import { PortfolioAccordionItem } from './PortfolioAccordionItem';

export function PortfolioListView({ onCreateNew }) {
  const { portfolios } = usePortfolioPage();

  return (
    <div className="flex flex-col gap-3 max-w-[1100px] mx-auto">
      {portfolios.map((portfolio) => (
        <PortfolioAccordionItem key={portfolio.id} portfolio={portfolio} />
      ))}

      <button
        onClick={onCreateNew}
        className="flex items-center justify-center gap-2.5 px-5 py-5 border-2 border-dashed border-[var(--border-primary)] rounded-xl text-[13px] font-medium text-[var(--text-tertiary)] hover:border-accent hover:text-accent hover:bg-accent/[0.04] transition-all cursor-pointer"
      >
        <PlusIcon className="w-4 h-4" />
        Create New Portfolio
      </button>
    </div>
  );
}
