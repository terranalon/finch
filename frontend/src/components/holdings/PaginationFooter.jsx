import { cn } from '../../lib';

function NavIcon({ d }) {
  return (
    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d={d} />
    </svg>
  );
}

const NAV_PATHS = {
  first: 'm18.75 4.5-7.5 7.5 7.5 7.5m-6-15L5.25 12l7.5 7.5',
  prev: 'M15.75 19.5 8.25 12l7.5-7.5',
  next: 'm8.25 4.5 7.5 7.5-7.5 7.5',
  last: 'm5.25 4.5 7.5 7.5-7.5 7.5m6-15 7.5 7.5-7.5 7.5',
};

function PageButton({ onClick, disabled, children, title }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'w-7 h-7 flex items-center justify-center rounded-md transition-colors',
        'bg-[var(--bg-secondary)] text-[var(--text-secondary)]',
        disabled
          ? 'opacity-30 cursor-not-allowed'
          : 'cursor-pointer hover:bg-[var(--border-primary)]'
      )}
    >
      {children}
    </button>
  );
}

export function PaginationFooter({ currentPage, totalItems, pageSize, onPageChange, onPageSizeChange }) {
  const totalPages = Math.ceil(totalItems / pageSize);
  const rangeStart = (currentPage - 1) * pageSize + 1;
  const rangeEnd = Math.min(currentPage * pageSize, totalItems);

  const goTo = (page) => {
    onPageChange(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border-primary)] bg-[var(--bg-tertiary)]">
      <div className="flex items-center gap-4">
        {/* Page size */}
        <div className="flex items-center gap-1.5 text-xs text-[var(--text-tertiary)]">
          Show:
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className={cn(
              'px-2 py-1 rounded text-xs',
              'bg-[var(--bg-secondary)] border border-[var(--border-primary)]',
              'text-[var(--text-primary)] cursor-pointer',
              'focus:outline-none'
            )}
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>

        {/* Range */}
        <span className="text-xs text-[var(--text-faint)]">
          Showing {rangeStart}-{rangeEnd} of {totalItems}
        </span>

        {/* Navigation */}
        {totalPages > 1 && (
          <div className="flex items-center gap-0.5">
            <PageButton onClick={() => goTo(1)} disabled={currentPage === 1} title="First page">
              <NavIcon d={NAV_PATHS.first} />
            </PageButton>
            <PageButton onClick={() => goTo(currentPage - 1)} disabled={currentPage === 1} title="Previous page">
              <NavIcon d={NAV_PATHS.prev} />
            </PageButton>
            <span className="text-xs text-[var(--text-tertiary)] px-2">
              {currentPage} / {totalPages}
            </span>
            <PageButton onClick={() => goTo(currentPage + 1)} disabled={currentPage >= totalPages} title="Next page">
              <NavIcon d={NAV_PATHS.next} />
            </PageButton>
            <PageButton onClick={() => goTo(totalPages)} disabled={currentPage >= totalPages} title="Last page">
              <NavIcon d={NAV_PATHS.last} />
            </PageButton>
          </div>
        )}
      </div>
    </div>
  );
}
