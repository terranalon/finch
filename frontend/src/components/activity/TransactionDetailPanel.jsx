import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn, formatCurrency, hasConversion } from '../../lib';
import { useSlideover } from '../../hooks/useSlideover';
import {
  XMarkIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  BanknotesIcon,
  ArrowsRightLeftIcon,
  PlusCircleIcon,
  MinusCircleIcon,
  ReceiptPercentIcon,
  ExternalLinkIcon,
} from './icons';

const getCurrencySymbol = (code) => {
  const symbols = { USD: '$', EUR: '\u20AC', GBP: '\u00A3', ILS: '\u20AA', JPY: '\u00A5', CHF: 'CHF ' };
  return symbols[code] || code + ' ';
};

const formatRate = (rate) => {
  return parseFloat(rate.toFixed(4)).toString();
};

const formatShortDate = (dateStr) => {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-[var(--border-subtle,var(--border))]">
      <span className="text-xs text-[var(--text-muted)]">{label}</span>
      <span className="text-[13px] font-medium font-mono text-[var(--text-primary)]">{value}</span>
    </div>
  );
}

function ViewAssetButton({ symbol, onClose }) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => { onClose(); navigate(`/assets/${encodeURIComponent(symbol)}`); }}
      className={cn(
        'flex items-center justify-center gap-1.5 w-full py-2.5 mt-5',
        'bg-[var(--accent-muted,rgba(59,130,246,0.15))] text-accent border border-accent',
        'rounded-lg text-[13px] font-semibold cursor-pointer',
        'hover:bg-accent hover:text-white transition-colors'
      )}
    >
      <ExternalLinkIcon className="w-4 h-4" />
      View {symbol} Details
    </button>
  );
}

export function TransactionDetailPanel({ transaction: tx, currency, onClose }) {
  const isOpen = !!tx;
  const [visible, setVisible] = useState(false);

  useSlideover(isOpen, onClose);

  useEffect(() => {
    if (isOpen) {
      requestAnimationFrame(() => setVisible(true));
    } else {
      setVisible(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const hasOriginal = hasConversion(tx);

  const renderTradeDetails = () => {
    const isBuy = tx.side === 'BUY';
    const primaryTotal = hasOriginal ? Math.abs(tx.original_amount) : Math.abs(tx.total);
    const primaryCurrency = hasOriginal ? tx.original_currency : tx.currency;
    const subtotal = tx.total - (tx.fee || 0);

    return (
      <>
        <div className="flex items-center gap-3 mb-6">
          <div className={cn(
            'w-[44px] h-[44px] rounded-xl flex items-center justify-center',
            isBuy ? 'bg-emerald-50 dark:bg-emerald-950/40' : 'bg-red-50 dark:bg-red-950/40'
          )}>
            {isBuy ? (
              <ArrowDownIcon className="w-[22px] h-[22px] text-emerald-600 dark:text-emerald-400" />
            ) : (
              <ArrowUpIcon className="w-[22px] h-[22px] text-red-600 dark:text-red-400" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{tx.symbol}</h2>
            <p className="text-sm text-[var(--text-secondary)]">{tx.name}</p>
          </div>
        </div>

        <div className="bg-[var(--bg-elevated)] rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-sm text-[var(--text-secondary)]">Total {isBuy ? 'Cost' : 'Proceeds'}</span>
            <div className="text-right">
              <span className={cn(
                'text-[22px] font-bold font-mono tabular-nums',
                isBuy ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
              )}>
                {isBuy ? '-' : '+'}{formatCurrency(primaryTotal, primaryCurrency)}
              </span>
              {hasOriginal && (
                <p className="text-sm text-[var(--text-muted)] font-mono">
                  {formatCurrency(Math.abs(tx.total), tx.currency)}
                </p>
              )}
            </div>
          </div>
        </div>

        <div>
          <DetailRow label="Transaction Type" value={isBuy ? 'Buy' : 'Sell'} />
          <DetailRow label="Quantity" value={`${tx.quantity} shares`} />
          <DetailRow label="Price per Share" value={formatCurrency(tx.price, tx.currency)} />
          <DetailRow label="Subtotal" value={formatCurrency(subtotal, tx.currency)} />
          {tx.fee > 0 && (
            <DetailRow label="Commission/Fee" value={formatCurrency(tx.fee, tx.currency)} />
          )}
          <DetailRow label="Date" value={formatShortDate(tx.date)} />
          <DetailRow label="Account" value={tx.account_name} />
          {tx.notes && (
            <div className="pt-3">
              <p className="text-xs text-[var(--text-muted)] mb-1">Notes</p>
              <p className="text-sm text-[var(--text-secondary)]">{tx.notes}</p>
            </div>
          )}
        </div>

        <ViewAssetButton symbol={tx.symbol} onClose={onClose} />
      </>
    );
  };

  const renderDividendDetails = () => {
    const primaryAmount = hasOriginal ? Math.abs(tx.original_amount) : Math.abs(tx.amount);
    const primaryCurrency = hasOriginal ? tx.original_currency : tx.currency;

    return (
      <>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-[44px] h-[44px] rounded-xl flex items-center justify-center bg-teal-50 dark:bg-teal-950/40">
            <BanknotesIcon className="w-[22px] h-[22px] text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{tx.symbol}</h2>
            <p className="text-sm text-[var(--text-secondary)]">{tx.name}</p>
          </div>
        </div>

        <div className="bg-[var(--bg-elevated)] rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-sm text-[var(--text-secondary)]">Dividend Received</span>
            <div className="text-right">
              <span className="text-[22px] font-bold font-mono tabular-nums text-teal-600 dark:text-teal-400">
                +{formatCurrency(primaryAmount, primaryCurrency)}
              </span>
              {hasOriginal && (
                <p className="text-sm text-[var(--text-muted)] font-mono">
                  {formatCurrency(Math.abs(tx.amount), tx.currency)}
                </p>
              )}
            </div>
          </div>
        </div>

        <div>
          <DetailRow label="Description" value={tx.description} />
          {tx.shares_held && (
            <DetailRow label="Shares Held" value={`${tx.shares_held} shares`} />
          )}
          {tx.dividend_per_share && (
            <DetailRow label="Per Share" value={formatCurrency(tx.dividend_per_share, tx.currency)} />
          )}
          <DetailRow label="Payment Date" value={formatShortDate(tx.date)} />
          {tx.ex_date && (
            <DetailRow label="Ex-Dividend Date" value={formatShortDate(tx.ex_date)} />
          )}
          <DetailRow label="Account" value={tx.account_name} />
        </div>

        <ViewAssetButton symbol={tx.symbol} onClose={onClose} />
      </>
    );
  };

  const renderForexDetails = () => (
    <>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-[44px] h-[44px] rounded-xl flex items-center justify-center bg-violet-50 dark:bg-violet-950/40">
          <ArrowsRightLeftIcon className="w-[22px] h-[22px] text-violet-600 dark:text-violet-400" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">
            {tx.from_currency} {'\u2192'} {tx.to_currency}
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">Currency Exchange</p>
        </div>
      </div>

      <div className="bg-[var(--bg-elevated)] rounded-lg p-4 mb-6">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm text-[var(--text-secondary)]">You Received</span>
          <span className="text-[22px] font-bold font-mono tabular-nums text-violet-600 dark:text-violet-400">
            {getCurrencySymbol(tx.to_currency)}{tx.to_amount.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between items-center text-sm">
          <span className="text-[var(--text-muted)]">You Converted</span>
          <span className="font-mono tabular-nums text-[var(--text-secondary)]">
            {getCurrencySymbol(tx.from_currency)}{tx.from_amount.toLocaleString()}
          </span>
        </div>
      </div>

      <div>
        <DetailRow label="Exchange Rate" value={`1 ${tx.from_currency} = ${formatRate(tx.exchange_rate)} ${tx.to_currency}`} />
        {tx.fee > 0 && (
          <DetailRow label="Fee" value={`${getCurrencySymbol(tx.from_currency)}${tx.fee}`} />
        )}
        <DetailRow label="Date" value={formatShortDate(tx.date)} />
        <DetailRow label="Account" value={tx.account_name} />
      </div>
    </>
  );

  const renderCashDetails = () => {
    const isDeposit = tx.activity_type === 'DEPOSIT';
    const isFee = tx.activity_type === 'FEE';
    const isInterest = tx.activity_type === 'INTEREST';
    const displayType = tx.cash_type || (isDeposit ? 'Deposit' : 'Withdrawal');
    const primaryAmount = hasOriginal ? Math.abs(tx.original_amount) : Math.abs(tx.amount);
    const primaryCurrency = hasOriginal ? tx.original_currency : tx.currency;

    const getStyleConfig = () => {
      if (isDeposit) {
        return {
          bgColor: 'bg-blue-50 dark:bg-blue-950/40',
          textColor: 'text-blue-600 dark:text-blue-400',
          icon: <PlusCircleIcon className="w-[22px] h-[22px] text-blue-600 dark:text-blue-400" />,
          sign: '+',
        };
      } else if (isInterest) {
        return {
          bgColor: 'bg-green-50 dark:bg-green-950/40',
          textColor: 'text-green-600 dark:text-green-400',
          icon: <BanknotesIcon className="w-[22px] h-[22px] text-green-600 dark:text-green-400" />,
          sign: '+',
        };
      } else if (isFee) {
        return {
          bgColor: 'bg-red-50 dark:bg-red-950/40',
          textColor: 'text-red-600 dark:text-red-400',
          icon: <ReceiptPercentIcon className="w-[22px] h-[22px] text-red-600 dark:text-red-400" />,
          sign: '-',
        };
      } else {
        return {
          bgColor: 'bg-amber-50 dark:bg-amber-950/40',
          textColor: 'text-amber-600 dark:text-amber-400',
          icon: <MinusCircleIcon className="w-[22px] h-[22px] text-amber-600 dark:text-amber-400" />,
          sign: '-',
        };
      }
    };

    const style = getStyleConfig();

    return (
      <>
        <div className="flex items-center gap-3 mb-6">
          <div className={cn('w-[44px] h-[44px] rounded-xl flex items-center justify-center', style.bgColor)}>
            {style.icon}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">{displayType}</h2>
            <p className="text-sm text-[var(--text-secondary)]">{tx.description}</p>
          </div>
        </div>

        <div className="bg-[var(--bg-elevated)] rounded-lg p-4 mb-6">
          <div className="flex justify-between items-center">
            <span className="text-sm text-[var(--text-secondary)]">Amount</span>
            <div className="text-right">
              <span className={cn('text-[22px] font-bold font-mono tabular-nums', style.textColor)}>
                {style.sign}{formatCurrency(primaryAmount, primaryCurrency)}
              </span>
              {hasOriginal && (
                <p className="text-sm text-[var(--text-muted)] font-mono">
                  {formatCurrency(Math.abs(tx.amount), tx.currency)}
                </p>
              )}
            </div>
          </div>
        </div>

        <div>
          <DetailRow label="Type" value={displayType} />
          {tx.fee > 0 && (
            <DetailRow label="Commission/Fee" value={formatCurrency(tx.fee, tx.currency)} />
          )}
          {tx.reference && (
            <DetailRow label="Reference" value={tx.reference} />
          )}
          <DetailRow label="Date" value={formatShortDate(tx.date)} />
          <DetailRow label="Account" value={tx.account_name} />
        </div>
      </>
    );
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 bg-black/50 z-40 transition-opacity',
          visible ? 'opacity-100' : 'opacity-0'
        )}
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="fixed top-0 h-full w-[420px] bg-[var(--bg-card,var(--bg-primary))] z-50 shadow-xl overflow-y-auto transition-[right] duration-[250ms] ease-out"
        style={{ right: visible ? 0 : -420 }}
      >
        {/* Close button */}
        <div className="sticky top-0 bg-[var(--bg-card,var(--bg-primary))] p-4 border-b border-[var(--border)] flex justify-between items-center">
          <span className="text-sm text-[var(--text-muted)]">Transaction Details</span>
          <button
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-md bg-[var(--bg-elevated)] hover:bg-[var(--border)] transition-colors cursor-pointer"
          >
            <XMarkIcon className="w-4 h-4 text-[var(--text-secondary)]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {tx.type === 'trade' && renderTradeDetails()}
          {tx.type === 'dividend' && renderDividendDetails()}
          {tx.type === 'forex' && renderForexDetails()}
          {tx.type === 'cash' && renderCashDetails()}
        </div>
      </div>
    </>
  );
}
