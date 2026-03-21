import { cn } from '../../lib';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from './icons';

export function PaginationFooter({
  currentPage,
  totalPages,
  pageSize,
  filteredCount,
  totalCount,
  onPageChange,
  onPageSizeChange,
}) {
  const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' });

  const handlePageChange = (page) => {
    onPageChange(page);
    scrollToTop();
  };

  return (
    <div className="flex items-center gap-4 py-4 mt-2">
      <div className="flex items-center gap-2">
        <span className="text-xs text-[var(--text-muted)]">Show:</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="px-2 py-1 bg-[var(--bg-elevated)] border border-[var(--border)] rounded-md text-xs text-[var(--text-primary)] cursor-pointer focus:outline-none focus:border-accent"
        >
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>

      <p className="text-xs text-[var(--text-faint)]">
        Showing {Math.min((currentPage - 1) * pageSize + 1, filteredCount)}-{Math.min(currentPage * pageSize, filteredCount)} of {filteredCount}
        {filteredCount !== totalCount && (
          <span> ({totalCount} total)</span>
        )}
      </p>

      {totalPages > 1 && (
        <div className="flex items-center gap-1 ml-auto">
          <button
            onClick={() => handlePageChange(1)}
            disabled={currentPage === 1}
            className={cn(
              'w-7 h-7 flex items-center justify-center bg-[var(--bg-elevated)] rounded-md',
              'hover:bg-[var(--border)] transition-colors',
              currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
            )}
            title="First page"
          >
            <ChevronDoubleLeftIcon className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className={cn(
              'w-7 h-7 flex items-center justify-center bg-[var(--bg-elevated)] rounded-md',
              'hover:bg-[var(--border)] transition-colors',
              currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
            )}
            title="Previous page"
          >
            <ChevronLeftIcon className="w-3.5 h-3.5" />
          </button>
          <span className="text-xs text-[var(--text-muted)] px-2">
            {currentPage} / {totalPages}
          </span>
          <button
            onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            className={cn(
              'w-7 h-7 flex items-center justify-center bg-[var(--bg-elevated)] rounded-md',
              'hover:bg-[var(--border)] transition-colors',
              currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
            )}
            title="Next page"
          >
            <ChevronRightIcon className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => handlePageChange(totalPages)}
            disabled={currentPage >= totalPages}
            className={cn(
              'w-7 h-7 flex items-center justify-center bg-[var(--bg-elevated)] rounded-md',
              'hover:bg-[var(--border)] transition-colors',
              currentPage >= totalPages ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
            )}
            title="Last page"
          >
            <ChevronDoubleRightIcon className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
