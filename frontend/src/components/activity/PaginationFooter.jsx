import { cn } from '../../lib';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from './icons';

const PAGE_SIZE_OPTIONS = [25, 50, 100];

function PageButton({ onClick, disabled, title, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cn(
        'w-7 h-7 flex items-center justify-center bg-[var(--bg-elevated)] rounded-md',
        'hover:bg-[var(--border)] transition-colors',
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
      )}
    >
      {children}
    </button>
  );
}

export function PaginationFooter({
  currentPage,
  totalPages,
  pageSize,
  filteredCount,
  totalCount,
  onPageChange,
  onPageSizeChange,
}) {
  const handlePageChange = (page) => {
    onPageChange(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isFirstPage = currentPage === 1;
  const isLastPage = currentPage >= totalPages;
  const rangeStart = Math.min((currentPage - 1) * pageSize + 1, filteredCount);
  const rangeEnd = Math.min(currentPage * pageSize, filteredCount);

  return (
    <div className="flex items-center gap-4 py-4 mt-2">
      <div className="flex items-center gap-2">
        <span className="text-xs text-[var(--text-muted)]">Show:</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="px-2 py-1 bg-[var(--bg-elevated)] border border-[var(--border)] rounded-md text-xs text-[var(--text-primary)] cursor-pointer focus:outline-none focus:border-accent"
        >
          {PAGE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>{size}</option>
          ))}
        </select>
      </div>

      <p className="text-xs text-[var(--text-faint)]">
        Showing {rangeStart}-{rangeEnd} of {filteredCount}
        {filteredCount !== totalCount && (
          <span> ({totalCount} total)</span>
        )}
      </p>

      {totalPages > 1 && (
        <div className="flex items-center gap-1 ml-auto">
          <PageButton onClick={() => handlePageChange(1)} disabled={isFirstPage} title="First page">
            <ChevronDoubleLeftIcon className="w-3.5 h-3.5" />
          </PageButton>
          <PageButton onClick={() => handlePageChange(currentPage - 1)} disabled={isFirstPage} title="Previous page">
            <ChevronLeftIcon className="w-3.5 h-3.5" />
          </PageButton>
          <span className="text-xs text-[var(--text-muted)] px-2">
            {currentPage} / {totalPages}
          </span>
          <PageButton onClick={() => handlePageChange(currentPage + 1)} disabled={isLastPage} title="Next page">
            <ChevronRightIcon className="w-3.5 h-3.5" />
          </PageButton>
          <PageButton onClick={() => handlePageChange(totalPages)} disabled={isLastPage} title="Last page">
            <ChevronDoubleRightIcon className="w-3.5 h-3.5" />
          </PageButton>
        </div>
      )}
    </div>
  );
}
