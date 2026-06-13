import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn, formatCurrency, formatPercent, api, transformTrade, transformDividend, transformForex, transformCash } from '../../lib';
import { ASSET_COLORS } from '../../lib/constants';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { useSlideover } from '../../hooks/useSlideover';
import { ExternalLinkIcon, XMarkIcon, PencilSquareIcon, TrashIcon } from './icons';
import { TYPE_LABELS } from './constants';

const HOLDINGS_PREVIEW = 5;

function pnlColor(value) {
  if (value > 0) return 'text-[var(--positive)]';
  if (value < 0) return 'text-[var(--negative)]';
  return 'text-[var(--text-tertiary)]';
}

function formatPnl(value, currency) {
  if (value === null || value === undefined) return '-';
  const sign = value >= 0 ? '+' : '-';
  return `${sign}${formatCurrency(Math.abs(value), currency, { decimals: 0 })}`;
}

function HoldingIcon({ symbol, assetClass }) {
  const color = ASSET_COLORS[assetClass] || '#64748B';
  return (
    <div
      className="w-7 h-7 rounded-md shrink-0 flex items-center justify-center text-[9px] font-bold text-white"
      style={{ backgroundColor: color }}
    >
      {(symbol || '??').slice(0, 2)}
    </div>
  );
}

const TX_STYLES = {
  trade:    { label: 'Trade',    bg: 'bg-[var(--accent-primary)]/10', text: 'text-[var(--accent-primary)]' },
  dividend: { label: 'Div',      bg: 'bg-[var(--positive)]/10',       text: 'text-[var(--positive)]' },
  forex:    { label: 'FX',       bg: 'bg-[var(--warning)]/10',        text: 'text-[var(--warning)]' },
  cash:     { label: 'Cash',     bg: 'bg-[var(--text-faint)]/10',     text: 'text-[var(--text-faint)]' },
};

function formatDateShort(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function txDescription(tx) {
  if (tx.type === 'trade') return `${tx.side === 'BUY' ? 'Buy' : 'Sell'} ${tx.symbol}`;
  if (tx.type === 'dividend') return `${tx.symbol} dividend`;
  if (tx.type === 'forex') return 'FX conversion';
  return tx.subtype || tx.type;
}

function txAmount(tx, currency) {
  const value = tx.type === 'trade' ? tx.total : tx.amount;
  if (value == null) return '-';
  const prefix = tx.type === 'trade' && tx.side === 'BUY' ? '-' : '+';
  return `${prefix}${formatCurrency(Math.abs(value), tx.currency || currency, { decimals: 0 })}`;
}

async function fetchRecentActivity(accountId, currency) {
  const q = `?account_id=${accountId}&limit=5&display_currency=${currency}`;
  const [trades, dividends, forex, cash] = await Promise.all([
    api(`/transactions/trades${q}`).then((r) => r.ok ? r.json() : { items: [] }),
    api(`/transactions/dividends${q}`).then((r) => r.ok ? r.json() : { items: [] }),
    api(`/transactions/forex${q}`).then((r) => r.ok ? r.json() : { items: [] }),
    api(`/transactions/cash${q}`).then((r) => r.ok ? r.json() : { items: [] }),
  ]);
  const all = [
    ...trades.items.map(transformTrade),
    ...dividends.items.map(transformDividend),
    ...forex.items.map(transformForex),
    ...cash.items.map(transformCash),
  ];
  all.sort((a, b) => new Date(b.date) - new Date(a.date));
  return all.slice(0, 5);
}

export function AccountSidebar({ account, holdings, currency, onClose, onDelete, onRename }) {
  const isOpen = !!account;
  const navigate = useNavigate();
  useSlideover(isOpen, onClose);

  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState('');
  const [renameError, setRenameError] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [activityLoading, setActivityLoading] = useState(false);

  // Keep the last non-null account in a ref so the sidebar content remains
  // visible during the CSS slide-out animation (200ms) after account becomes null.
  const prevAccountRef = useRef(account);
  if (account) prevAccountRef.current = account;
  const renderAccount = account ?? prevAccountRef.current;

  // Set to true when Escape is pressed so the blur handler skips commitRename.
  const cancelRenameRef = useRef(false);

  // Reset all local state when switching to a different account.
  // The null guard prevents resetting during the close animation.
  useEffect(() => {
    if (!account) return;
    setEditingName(false);
    setNameValue('');
    setRenameError(null);
    setShowDeleteConfirm(false);
    setIsDeleting(false);
    setDeleteError(null);
    setRecentActivity([]);
  }, [account?.id]);

  // Fetch recent activity lazily when an account is selected.
  useEffect(() => {
    if (!account?.id) return;
    let cancelled = false;
    setActivityLoading(true);
    fetchRecentActivity(account.id, currency)
      .then((txs) => { if (!cancelled) setRecentActivity(txs); })
      .catch(() => { if (!cancelled) setRecentActivity([]); })
      .finally(() => { if (!cancelled) setActivityLoading(false); });
    return () => { cancelled = true; };
  }, [account?.id, currency]);

  if (!renderAccount) return null;

  const isShared = (renderAccount.portfolio_ids?.length ?? 0) > 1;
  const totalCost = (holdings || []).reduce((s, h) => s + (h.costBasis || 0), 0);
  const totalPnl = (holdings || []).reduce((s, h) => s + (h.pnl || 0), 0);
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;
  const visibleHoldings = (holdings || []).slice(0, HOLDINGS_PREVIEW);
  const hiddenCount = (holdings || []).length - visibleHoldings.length;

  const startRename = () => {
    setNameValue(renderAccount.name);
    setRenameError(null);
    setEditingName(true);
  };

  const commitRename = async () => {
    if (cancelRenameRef.current) {
      cancelRenameRef.current = false;
      return;
    }
    const trimmed = nameValue.trim();
    setEditingName(false);
    if (trimmed && trimmed !== renderAccount.name) {
      try {
        await onRename?.(renderAccount.id, trimmed);
      } catch (err) {
        setRenameError(err.message || 'Failed to rename account');
      }
    }
  };

  // Only resets spinner/error on the failure path — success closes the sidebar
  // naturally via liveSelectedAccount becoming null in the parent.
  const handleDeleteConfirm = async () => {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await onDelete?.(renderAccount.id);
    } catch (err) {
      setIsDeleting(false);
      setDeleteError(err.message || 'Failed to delete account');
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/50 z-[200] transition-opacity',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={cn(
          'fixed right-0 top-0 h-dvh w-[440px] max-w-[90vw] bg-[var(--bg-primary)]',
          'border-l border-[var(--border-primary)] z-[201]',
          'flex flex-col transition-transform duration-200 ease-out',
          isOpen ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-[var(--border-primary)] sticky top-0 bg-[var(--bg-primary)] z-10">
          {/* Close button — absolute so it doesn't compete with the account name */}
          <button
            onClick={onClose}
            className="absolute top-4 right-5 w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)] transition-all cursor-pointer"
          >
            <XMarkIcon className="w-[18px] h-[18px]" />
          </button>

          {/* Name row — full width minus space for close button */}
          <div className="pr-10">
            <div className="flex items-center gap-2.5 mb-1">
              <BrokerLogo type={renderAccount.broker_type} className="w-9 h-9 rounded-[9px] shrink-0" />
              {editingName ? (
                <input
                  autoFocus
                  value={nameValue}
                  onChange={(e) => setNameValue(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') commitRename();
                    if (e.key === 'Escape') {
                      cancelRenameRef.current = true;
                      setEditingName(false);
                    }
                  }}
                  className="text-xl font-semibold bg-transparent border-b border-[var(--accent-primary)] outline-none w-full"
                />
              ) : (
                <div className="flex items-center gap-1.5 min-w-0">
                  <h2 className="text-xl font-semibold truncate">{renderAccount.name}</h2>
                  <button
                    onClick={startRename}
                    className="shrink-0 w-6 h-6 flex items-center justify-center rounded text-[var(--text-faint)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] transition-all cursor-pointer"
                    title="Rename account"
                  >
                    <PencilSquareIcon className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
            <p className="text-[13px] text-[var(--text-faint)]">
              {TYPE_LABELS[renderAccount.account_type] || renderAccount.account_type} Account
              {' \u00B7 '}
              {renderAccount.allocationPct.toFixed(1)}% of portfolio
            </p>
            {renameError && (
              <p className="text-[11px] text-[var(--negative)] mt-0.5">{renameError}</p>
            )}
          </div>

          {/* Value block + View Details */}
          <div className="mt-3.5 flex items-end justify-between gap-3">
            <div>
              <span className="text-[28px] font-bold font-mono tabular-nums tracking-tight">
                {formatCurrency(renderAccount.value, currency, { decimals: 0 })}
              </span>
              <span className={cn('text-sm font-medium font-mono tabular-nums ml-2.5', pnlColor(totalPnl))}>
                {formatPnl(totalPnl, currency)} ({formatPercent(totalPnlPct)})
              </span>
            </div>
            <button
              onClick={() => navigate(`/accounts/${renderAccount.id}`)}
              className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-[var(--accent-primary)] text-white rounded-lg text-xs font-semibold hover:bg-[var(--accent-hover)] transition-colors cursor-pointer whitespace-nowrap"
            >
              View Details
              <ExternalLinkIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-[18px]">
          {/* Summary card */}
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4">
            <h3 className="text-[13px] font-semibold text-[var(--text-secondary)] mb-3">Summary</h3>
            <DetailRow label="Total Cost" value={formatCurrency(totalCost, currency, { decimals: 0 })} />
            <DetailRow
              label="Unrealized P&L"
              value={`${formatPnl(totalPnl, currency)} (${formatPercent(totalPnlPct)})`}
              valueClass={pnlColor(totalPnl)}
            />
            <DetailRow label="Positions" value={String((holdings || []).length)} />
            <DetailRow
              label="Sync Status"
              value={
                <span className="flex items-center gap-1.5">
                  <span className={cn('w-1.5 h-1.5 rounded-full inline-block', renderAccount.syncStatus.color)} />
                  {renderAccount.lastSyncFormatted}
                </span>
              }
              isLast
            />
          </div>

          {/* Holdings card — top 5 */}
          {visibleHoldings.length > 0 && (
            <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4">
              <h3 className="text-[13px] font-semibold text-[var(--text-secondary)] mb-3">Top Holdings</h3>
              {visibleHoldings.map((h) => (
                <div
                  key={h.symbol}
                  className="flex items-center justify-between py-2.5 border-b border-[var(--border-subtle)] last:border-b-0"
                >
                  <div className="flex items-center gap-2.5">
                    <HoldingIcon symbol={h.symbol} assetClass={h.assetClass} />
                    <div>
                      <div className="text-[13px] font-semibold text-[var(--text-primary)]">{h.symbol}</div>
                      <div className="text-[11px] text-[var(--text-faint)]">
                        {formatQuantity(h.quantity, h.assetClass)} units
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[13px] font-semibold font-mono tabular-nums text-[var(--text-primary)]">
                      {formatCurrency(h.marketValue, currency, { decimals: 0 })}
                    </div>
                    <div className={cn('text-[11px] font-mono tabular-nums', pnlColor(h.pnl))}>
                      {formatPnl(h.pnl, currency)}
                    </div>
                  </div>
                </div>
              ))}
              <button
                onClick={() => navigate(`/accounts/${renderAccount.id}?tab=holdings`)}
                className="mt-2 pt-2 border-t border-[var(--border-subtle)] w-full flex items-center justify-center gap-1.5 text-[12px] text-[var(--text-faint)] hover:text-[var(--accent-primary)] transition-colors cursor-pointer"
              >
                View all holdings
                <ExternalLinkIcon className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* Recent activity card */}
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4">
            <h3 className="text-[13px] font-semibold text-[var(--text-secondary)] mb-3">Recent Activity</h3>
            {activityLoading ? (
              <div className="flex flex-col gap-2.5">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-2.5 py-1">
                    <div className="w-7 h-7 rounded-md bg-[var(--bg-tertiary)] animate-pulse shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <div className="h-3 w-32 rounded bg-[var(--bg-tertiary)] animate-pulse" />
                      <div className="h-2.5 w-16 rounded bg-[var(--bg-tertiary)] animate-pulse" />
                    </div>
                    <div className="h-3 w-16 rounded bg-[var(--bg-tertiary)] animate-pulse" />
                  </div>
                ))}
              </div>
            ) : recentActivity.length === 0 ? (
              <p className="text-[12px] text-[var(--text-faint)]">No recent transactions.</p>
            ) : (
              <>
                {recentActivity.map((tx) => {
                  const style = TX_STYLES[tx.type] || TX_STYLES.cash;
                  return (
                    <div
                      key={tx.id}
                      className="flex items-center justify-between py-2.5 border-b border-[var(--border-subtle)] last:border-b-0"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={cn('w-7 h-7 rounded-md shrink-0 flex items-center justify-center text-[9px] font-bold', style.bg, style.text)}>
                          {style.label}
                        </div>
                        <div>
                          <div className="text-[13px] font-medium text-[var(--text-primary)]">{txDescription(tx)}</div>
                          <div className="text-[11px] text-[var(--text-faint)]">{formatDateShort(tx.date)}</div>
                        </div>
                      </div>
                      <div className="text-[13px] font-mono tabular-nums text-[var(--text-secondary)]">
                        {txAmount(tx, currency)}
                      </div>
                    </div>
                  );
                })}
                <button
                  onClick={() => navigate(`/accounts/${renderAccount.id}?tab=transactions`)}
                  className="mt-2 pt-2 border-t border-[var(--border-subtle)] w-full flex items-center justify-center gap-1.5 text-[12px] text-[var(--text-faint)] hover:text-[var(--accent-primary)] transition-colors cursor-pointer"
                >
                  View all activity
                  <ExternalLinkIcon className="w-3 h-3" />
                </button>
              </>
            )}
          </div>

          {/* Management actions */}
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4">
            <h3 className="text-[13px] font-semibold text-[var(--text-secondary)] mb-3">Manage</h3>
            <div className="flex flex-col gap-2">
              {!showDeleteConfirm ? (
                <ActionButton
                  icon={<TrashIcon className="w-4 h-4" />}
                  label={isShared ? 'Remove from Portfolio' : 'Delete Account'}
                  variant="danger"
                  onClick={() => setShowDeleteConfirm(true)}
                />
              ) : (
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--negative)]/30">
                  <p className="text-[12px] text-[var(--text-secondary)] mb-2.5">
                    {isShared
                      ? 'Remove this account from the current portfolio? It will remain in other portfolios.'
                      : 'Permanently delete this account and all its data?'}
                  </p>
                  {deleteError && (
                    <p className="text-[11px] text-[var(--negative)] mb-2">{deleteError}</p>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setShowDeleteConfirm(false); setDeleteError(null); }}
                      className="flex-1 px-3 py-1.5 rounded-md text-xs font-medium bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleDeleteConfirm}
                      disabled={isDeleting}
                      className="flex-1 px-3 py-1.5 rounded-md text-xs font-semibold bg-[var(--negative)] text-white hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
                    >
                      {isDeleting ? 'Deleting...' : isShared ? 'Remove' : 'Delete'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function DetailRow({ label, value, valueClass, isLast }) {
  return (
    <div className={cn(
      'flex items-center justify-between py-2',
      !isLast && 'border-b border-[var(--border-subtle)]'
    )}>
      <span className="text-[13px] text-[var(--text-faint)]">{label}</span>
      <span className={cn('text-[13px] font-medium text-[var(--text-primary)]', valueClass)}>
        {value}
      </span>
    </div>
  );
}

function ActionButton({ icon, label, onClick, variant = 'default' }) {
  const isDefault = variant === 'default';
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors cursor-pointer text-left',
        isDefault
          ? 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'
          : 'text-[var(--negative)] hover:bg-[var(--negative)]/10'
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function formatQuantity(qty, assetClass) {
  if (qty === null || qty === undefined) return '0';
  if (assetClass === 'Crypto') {
    return Number(qty).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  }
  return Number(qty).toLocaleString('en-US', { maximumFractionDigits: 0 });
}
