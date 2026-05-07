import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn, formatCurrency, formatPercent } from '../../lib';
import { ASSET_COLORS } from '../../lib/constants';
import { BrokerLogo } from '../AccountWizard/BrokerLogo';
import { getBrokerConfig } from '../AccountWizard/constants/brokerConfig';
import { useSlideover } from '../../hooks/useSlideover';
import { ExternalLinkIcon, XMarkIcon, PencilSquareIcon, TrashIcon, CloudArrowUpIcon, KeyIcon } from './icons';
import { TYPE_LABELS } from './constants';

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

export function AccountSidebar({ account, holdings, currency, onClose, onDelete, onRename, onUpload, onApiCredentials, positionsTruncated }) {
  const isOpen = !!account;
  const navigate = useNavigate();
  useSlideover(isOpen, onClose);

  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  if (!account) return null;

  const brokerConfig = getBrokerConfig(account.broker_type);
  const totalCost = (holdings || []).reduce((s, h) => s + (h.costBasis || 0), 0);
  const totalPnl = (holdings || []).reduce((s, h) => s + (h.pnl || 0), 0);
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

  const startRename = () => {
    setNameValue(account.name);
    setEditingName(true);
  };

  const commitRename = () => {
    const trimmed = nameValue.trim();
    setEditingName(false);
    if (trimmed && trimmed !== account.name) {
      onRename?.(account.id, trimmed);
    }
  };

  const handleDeleteConfirm = async () => {
    setIsDeleting(true);
    await onDelete?.(account.id);
    setIsDeleting(false);
    setShowDeleteConfirm(false);
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
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2.5 mb-1">
                <BrokerLogo type={account.broker_type} className="w-9 h-9 rounded-[9px] shrink-0" />
                {editingName ? (
                  <input
                    autoFocus
                    value={nameValue}
                    onChange={(e) => setNameValue(e.target.value)}
                    onBlur={commitRename}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitRename();
                      if (e.key === 'Escape') setEditingName(false);
                    }}
                    className="text-xl font-semibold bg-transparent border-b border-[var(--accent-primary)] outline-none w-full"
                  />
                ) : (
                  <div className="flex items-center gap-1.5 min-w-0">
                    <h2 className="text-xl font-semibold truncate">{account.name}</h2>
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
                {TYPE_LABELS[account.account_type] || account.account_type} Account
                {' \u00B7 '}
                {account.allocationPct.toFixed(1)}% of portfolio
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => navigate(`/accounts/${account.id}`)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--accent-primary)] text-white rounded-lg text-xs font-semibold hover:bg-[var(--accent-hover)] transition-colors cursor-pointer whitespace-nowrap"
              >
                View Details
                <ExternalLinkIcon className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-secondary)] transition-all cursor-pointer"
              >
                <XMarkIcon className="w-[18px] h-[18px]" />
              </button>
            </div>
          </div>

          {/* Value block */}
          <div className="mt-3.5">
            <span className="text-[28px] font-bold font-mono tabular-nums tracking-tight">
              {formatCurrency(account.value, currency, { decimals: 0 })}
            </span>
            <span className={cn('text-sm font-medium font-mono tabular-nums ml-2.5', pnlColor(totalPnl))}>
              {formatPnl(totalPnl, currency)} ({formatPercent(totalPnlPct)})
            </span>
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
                  <span className={cn('w-1.5 h-1.5 rounded-full inline-block', account.syncStatus.color)} />
                  {account.lastSyncFormatted}
                </span>
              }
              isLast
            />
          </div>

          {/* Holdings card */}
          {(holdings || []).length > 0 && (
            <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4">
              <h3 className="text-[13px] font-semibold text-[var(--text-secondary)] mb-3">
                Holdings ({holdings.length})
              </h3>
              {holdings.map((h) => (
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
              {positionsTruncated && (
                <p className="text-[11px] text-[var(--text-faint)] mt-2 pt-2 border-t border-[var(--border-subtle)]">
                  Portfolio has more than 100 positions. View full list in account details.
                </p>
              )}
            </div>
          )}

          {/* Management actions */}
          <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl p-4">
            <h3 className="text-[13px] font-semibold text-[var(--text-secondary)] mb-3">Manage</h3>
            <div className="flex flex-col gap-2">
              {brokerConfig?.supportedFormats?.length > 0 && (
                <ActionButton
                  icon={<CloudArrowUpIcon className="w-4 h-4" />}
                  label="Upload Data"
                  onClick={() => onUpload?.(account)}
                />
              )}
              {brokerConfig?.hasApi && (
                <ActionButton
                  icon={<KeyIcon className="w-4 h-4" />}
                  label="API Credentials"
                  onClick={() => onApiCredentials?.(account)}
                />
              )}
              {!showDeleteConfirm ? (
                <ActionButton
                  icon={<TrashIcon className="w-4 h-4" />}
                  label="Delete Account"
                  variant="danger"
                  onClick={() => setShowDeleteConfirm(true)}
                />
              ) : (
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--negative)]/30">
                  <p className="text-[12px] text-[var(--text-secondary)] mb-2.5">
                    Permanently delete this account and all its data?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setShowDeleteConfirm(false)}
                      className="flex-1 px-3 py-1.5 rounded-md text-xs font-medium bg-[var(--bg-primary)] border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleDeleteConfirm}
                      disabled={isDeleting}
                      className="flex-1 px-3 py-1.5 rounded-md text-xs font-semibold bg-[var(--negative)] text-white hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
                    >
                      {isDeleting ? 'Deleting...' : 'Delete'}
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
