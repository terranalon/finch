import { useState } from 'react';
import { cn } from '../../lib';

function MetaRow({ label, children }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[var(--border-primary)] last:border-b-0">
      <span className="text-sm text-[var(--text-secondary)]">{label}</span>
      <span className="text-sm text-[var(--text-primary)] font-medium text-right">{children}</span>
    </div>
  );
}

function getMetaRows(asset) {
  const rows = [];

  if (asset.asset_class === 'Stock') {
    if (asset.sector) rows.push({ label: 'Sector', value: asset.sector });
    if (asset.industry) rows.push({ label: 'Industry', value: asset.industry });
    if (asset.ceo) rows.push({ label: 'CEO', value: asset.ceo });
    if (asset.employees) rows.push({ label: 'Employees', value: asset.employees.toLocaleString() });
  } else if (asset.asset_class === 'ETF') {
    if (asset.sector) rows.push({ label: 'Sector', value: asset.sector });
    if (asset.fund_family) rows.push({ label: 'Fund Family', value: asset.fund_family });
  }

  return rows;
}

export default function AssetAbout({ asset }) {
  const [expanded, setExpanded] = useState(true);
  const metaRows = getMetaRows(asset);

  let hostname = '';
  if (asset.website) {
    try { hostname = new URL(asset.website).hostname.replace(/^www\./, ''); } catch { hostname = asset.website; }
  }

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg mb-6">
      <button
        onClick={() => setExpanded((prev) => !prev)}
        aria-label={expanded ? 'Collapse About' : 'Expand About'}
        className="w-full flex items-center justify-between px-4 py-3 border-b border-[var(--border-primary)]"
      >
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">About</h3>
        <svg
          className={cn('size-4 text-[var(--text-secondary)] transition-transform', !expanded && '-rotate-90')}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-4 py-4">
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed mb-4">
            {asset.description || 'No description available.'}
          </p>
          <div className="divide-y divide-[var(--border-primary)]">
            {metaRows.map(({ label, value }) => (
              <MetaRow key={label} label={label}>{value}</MetaRow>
            ))}
            {asset.website && (
              <MetaRow label="Website">
                <a
                  href={asset.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent hover:underline flex items-center gap-1"
                >
                  {hostname}
                  <svg className="size-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </MetaRow>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
