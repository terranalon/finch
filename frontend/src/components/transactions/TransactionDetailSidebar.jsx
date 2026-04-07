import { useNavigate } from 'react-router-dom';
import { cn, formatCurrency, hasConversion } from '../../lib';
import { useSlideover } from '../../hooks/useSlideover';
import {
  ArrowUpIcon,
  ArrowDownIcon,
  BanknotesIcon,
  ArrowsRightLeftIcon,
  PlusCircleIcon,
  MinusCircleIcon,
  ReceiptPercentIcon,
  ExternalLinkIcon,
  XMarkIcon,
} from '../activity/icons';

const CURRENCY_SYMBOLS = { USD: '$', EUR: '\u20AC', GBP: '\u00A3', ILS: '\u20AA', JPY: '\u00A5', CHF: 'CHF ' };

function getCurrencySymbol(code) {
  return CURRENCY_SYMBOLS[code] || code + ' ';
}

function formatRate(rate) {
  return parseFloat(rate.toFixed(4)).toString();
}

function formatDateShort(dateStr) {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const STYLE_CONFIG = {
  trade: {
    BUY: { bg: 'bg-[var(--positive-muted)]', text: 'text-[var(--positive)]', icon: ArrowDownIcon, sign: '-' },
    SELL: { bg: 'bg-[var(--negative-muted)]', text: 'text-[var(--negative)]', icon: ArrowUpIcon, sign: '+' },
  },
  dividend: { bg: 'bg-[var(--teal-muted)]', text: 'text-[var(--teal)]', icon: BanknotesIcon, sign: '+' },
  forex: { bg: 'bg-[var(--violet-muted)]', text: 'text-[var(--violet)]', icon: ArrowsRightLeftIcon },
  cash: {
    DEPOSIT: { bg: 'bg-[var(--blue-muted)]', text: 'text-[var(--blue)]', icon: PlusCircleIcon, sign: '+' },
    INTEREST: { bg: 'bg-[var(--positive-muted)]', text: 'text-[var(--positive)]', icon: BanknotesIcon, sign: '+' },
    FEE: { bg: 'bg-[var(--negative-muted)]', text: 'text-[var(--negative)]', icon: ReceiptPercentIcon, sign: '-' },
    WITHDRAWAL: { bg: 'bg-[var(--amber-muted)]', text: 'text-[var(--amber)]', icon: MinusCircleIcon, sign: '-' },
    TRANSFER: { bg: 'bg-[var(--slate-muted)]', text: 'text-[var(--slate-clr)]', icon: ArrowsRightLeftIcon, sign: '' },
  },
};

function getStyle(tx) {
  switch (tx.type) {
    case 'trade':
      return STYLE_CONFIG.trade[tx.side] || STYLE_CONFIG.trade.BUY;
    case 'dividend':
      return STYLE_CONFIG.dividend;
    case 'forex':
      return STYLE_CONFIG.forex;
    case 'cash':
      return STYLE_CONFIG.cash[tx.activity_type] || STYLE_CONFIG.cash.WITHDRAWAL;
    default:
      return STYLE_CONFIG.cash.DEPOSIT;
  }
}

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between items-center py-3 border-b border-[var(--border-primary)] last:border-b-0">
      <span className="text-[12px] text-[var(--text-tertiary)]">{label}</span>
      <span className="text-[12px] font-medium text-[var(--text-primary)] text-right max-w-[60%] truncate">{value}</span>
    </div>
  );
}

function DetailHeader({ icon: Icon, style, title, subtitle }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className={cn('w-[44px] h-[44px] rounded-xl flex items-center justify-center', style.bg)}>
        <Icon className={cn('w-[22px] h-[22px]', style.text)} />
      </div>
      <div className="min-w-0">
        <h2 className="text-lg font-bold text-[var(--text-primary)] truncate">{title}</h2>
        <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{subtitle}</p>
      </div>
    </div>
  );
}

function SummaryCard({ label, sign, amount, currency, style, convertedAmount, convertedCurrency }) {
  return (
    <div className="bg-[var(--bg-tertiary)] rounded-lg p-4 mb-5">
      <div className="flex justify-between items-center">
        <span className="text-xs text-[var(--text-tertiary)]">{label}</span>
        <div className="text-right">
          <span className={cn('text-[22px] font-bold font-mono tabular-nums', style.text)}>
            {sign}{formatCurrency(amount, currency)}
          </span>
          {convertedAmount != null && (
            <p className="text-xs text-[var(--text-faint)] font-mono mt-1">
              {formatCurrency(convertedAmount, convertedCurrency)}
            </p>
          )}
        </div>
      </div>
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
        'bg-accent/15 text-accent border border-accent',
        'rounded-lg text-[13px] font-semibold cursor-pointer',
        'hover:bg-accent hover:text-white transition-colors'
      )}
    >
      <ExternalLinkIcon className="w-4 h-4" />
      View {symbol} Details
    </button>
  );
}

function getPrimaryDisplay(tx, converted, amountField) {
  const amount = Math.abs(converted ? tx.original_amount : tx[amountField]);
  const currency = converted ? tx.original_currency : tx.currency;
  const convertedAmount = converted ? Math.abs(tx[amountField]) : null;
  return { amount, currency, convertedAmount };
}

function TradeDetails({ tx, style, converted, onClose }) {
  const isBuy = tx.side === 'BUY';
  const { amount, currency, convertedAmount } = getPrimaryDisplay(tx, converted, 'total');
  const subtotal = tx.total - (tx.fee || 0);

  return (
    <>
      <DetailHeader icon={style.icon} style={style} title={tx.symbol} subtitle={tx.name} />
      <SummaryCard
        label={`Total ${isBuy ? 'Cost' : 'Proceeds'}`}
        sign={style.sign}
        amount={amount}
        currency={currency}
        style={style}
        convertedAmount={convertedAmount}
        convertedCurrency={tx.currency}
      />
      <div>
        <DetailRow label="Transaction Type" value={isBuy ? 'Buy' : 'Sell'} />
        <DetailRow label="Quantity" value={`${tx.quantity} ${tx.asset_class === 'Crypto' ? 'units' : 'shares'}`} />
        <DetailRow label="Price per Share" value={formatCurrency(tx.price, tx.currency)} />
        <DetailRow label="Subtotal" value={formatCurrency(subtotal, tx.currency)} />
        {tx.fee > 0 && <DetailRow label="Commission/Fee" value={formatCurrency(tx.fee, tx.currency)} />}
        <DetailRow label="Date" value={formatDateShort(tx.date)} />
        <DetailRow label="Account" value={tx.account_name} />
        {tx.notes && (
          <div className="pt-3">
            <p className="text-xs text-[var(--text-tertiary)] mb-1">Notes</p>
            <p className="text-[12px] text-[var(--text-secondary)]">{tx.notes}</p>
          </div>
        )}
      </div>
      <ViewAssetButton symbol={tx.symbol} onClose={onClose} />
    </>
  );
}

function DividendDetails({ tx, style, converted, onClose }) {
  const { amount, currency, convertedAmount } = getPrimaryDisplay(tx, converted, 'amount');

  return (
    <>
      <DetailHeader icon={style.icon} style={style} title={tx.symbol} subtitle={tx.name} />
      <SummaryCard
        label="Dividend Received"
        sign="+"
        amount={amount}
        currency={currency}
        style={style}
        convertedAmount={convertedAmount}
        convertedCurrency={tx.currency}
      />
      <div>
        <DetailRow label="Description" value={tx.description} />
        {tx.shares_held && <DetailRow label="Shares Held" value={`${tx.shares_held} shares`} />}
        {tx.dividend_per_share && <DetailRow label="Per Share" value={formatCurrency(tx.dividend_per_share, tx.currency)} />}
        <DetailRow label="Payment Date" value={formatDateShort(tx.date)} />
        {tx.ex_date && <DetailRow label="Ex-Dividend Date" value={formatDateShort(tx.ex_date)} />}
        <DetailRow label="Account" value={tx.account_name} />
      </div>
      <ViewAssetButton symbol={tx.symbol} onClose={onClose} />
    </>
  );
}

function ForexDetails({ tx, style }) {
  return (
    <>
      <DetailHeader
        icon={style.icon}
        style={style}
        title={`${tx.from_currency} \u2192 ${tx.to_currency}`}
        subtitle="Currency Exchange"
      />
      <div className="bg-[var(--bg-tertiary)] rounded-lg p-4 mb-5">
        <div className="flex justify-between items-center mb-3">
          <span className="text-xs text-[var(--text-tertiary)]">You Received</span>
          <span className={cn('text-[22px] font-bold font-mono tabular-nums', style.text)}>
            {getCurrencySymbol(tx.to_currency)}{tx.to_amount.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between items-center text-[12px]">
          <span className="text-[var(--text-tertiary)]">You Converted</span>
          <span className="font-mono tabular-nums text-[var(--text-secondary)]">
            {getCurrencySymbol(tx.from_currency)}{tx.from_amount.toLocaleString()}
          </span>
        </div>
      </div>
      <div>
        <DetailRow label="Exchange Rate" value={`1 ${tx.from_currency} = ${formatRate(tx.exchange_rate)} ${tx.to_currency}`} />
        {tx.fee > 0 && <DetailRow label="Fee" value={`${getCurrencySymbol(tx.from_currency)}${tx.fee}`} />}
        <DetailRow label="Date" value={formatDateShort(tx.date)} />
        <DetailRow label="Account" value={tx.account_name} />
      </div>
    </>
  );
}

function CashDetails({ tx, style, converted }) {
  const displayType = tx.cash_type || (tx.activity_type === 'DEPOSIT' ? 'Deposit' : 'Withdrawal');
  const { amount, currency, convertedAmount } = getPrimaryDisplay(tx, converted, 'amount');

  return (
    <>
      <DetailHeader icon={style.icon} style={style} title={displayType} subtitle={tx.description} />
      <SummaryCard
        label="Amount"
        sign={style.sign}
        amount={amount}
        currency={currency}
        style={style}
        convertedAmount={convertedAmount}
        convertedCurrency={tx.currency}
      />
      <div>
        <DetailRow label="Type" value={displayType} />
        {tx.fee > 0 && <DetailRow label="Commission/Fee" value={formatCurrency(tx.fee, tx.currency)} />}
        {tx.reference && <DetailRow label="Reference" value={tx.reference} />}
        <DetailRow label="Date" value={formatDateShort(tx.date)} />
        <DetailRow label="Account" value={tx.account_name} />
      </div>
    </>
  );
}

function renderDetails(tx, style, converted, onClose) {
  switch (tx.type) {
    case 'trade':
      return <TradeDetails tx={tx} style={style} converted={converted} onClose={onClose} />;
    case 'dividend':
      return <DividendDetails tx={tx} style={style} converted={converted} onClose={onClose} />;
    case 'forex':
      return <ForexDetails tx={tx} style={style} />;
    case 'cash':
      return <CashDetails tx={tx} style={style} converted={converted} />;
    default:
      return null;
  }
}

export function TransactionDetailSidebar({ transaction: tx, onClose }) {
  const isOpen = !!tx;
  useSlideover(isOpen, onClose);

  if (!isOpen) return null;

  const style = getStyle(tx);
  const converted = hasConversion(tx);

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 transition-opacity"
        onClick={onClose}
      />
      <div className="fixed top-0 right-0 z-50 h-dvh w-[380px] max-w-[90vw] bg-[var(--bg-secondary)] border-l border-[var(--border-primary)] shadow-2xl flex flex-col animate-slide-in-right">
        <div className="px-6 pt-5 pb-4 border-b border-[var(--border-primary)] flex-shrink-0 flex items-center justify-between">
          <span className="text-sm font-bold text-[var(--text-primary)]">Transaction Details</span>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-[var(--text-tertiary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)] transition-all cursor-pointer flex-shrink-0"
          >
            <XMarkIcon className="w-[18px] h-[18px]" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {renderDetails(tx, style, converted, onClose)}
        </div>
      </div>
    </>
  );
}
