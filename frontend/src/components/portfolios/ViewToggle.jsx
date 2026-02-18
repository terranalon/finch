import { cn } from '../../lib';

function GridIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
    </svg>
  );
}

function ListIcon({ className }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
    </svg>
  );
}

export function ViewToggle({ view, onViewChange }) {
  return (
    <div className="inline-flex w-fit rounded-lg border border-[var(--border-primary)] overflow-hidden bg-[var(--bg-secondary)]">
      <button
        onClick={() => onViewChange('grid')}
        className={cn(
          'flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer',
          view === 'grid'
            ? 'bg-accent text-white'
            : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
        )}
        aria-label="Grid view"
      >
        <GridIcon className="w-3.5 h-3.5" />
        Grid
      </button>
      <button
        onClick={() => onViewChange('list')}
        className={cn(
          'flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium border-l border-[var(--border-primary)] transition-all cursor-pointer',
          view === 'list'
            ? 'bg-accent text-white'
            : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
        )}
        aria-label="List view"
      >
        <ListIcon className="w-3.5 h-3.5" />
        List
      </button>
    </div>
  );
}
