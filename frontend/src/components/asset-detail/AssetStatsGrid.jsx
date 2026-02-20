import { formatCurrency, formatNumber, formatPercent, formatDate, cn } from '../../lib';

const fmt = (v, formatter) => (v != null ? formatter(v) : '--');

function getStatsItems(asset) {
  const m = asset.daily_metrics || {};

  if (asset.asset_class === 'ETF') {
    return [
      { label: 'NAV', value: fmt(asset.nav, (v) => formatCurrency(v, asset.currency)) },
      { label: 'Expense Ratio', value: fmt(asset.expense_ratio, (v) => formatPercent(v * 100)) },
      { label: 'Fund Family', value: asset.fund_family || '--' },
      { label: 'Day Range', value: m.low != null && m.high != null ? `${formatCurrency(m.low, asset.currency)} – ${formatCurrency(m.high, asset.currency)}` : '--' },
      { label: '52W Range', value: asset.week_52_low != null && asset.week_52_high != null ? `${formatCurrency(asset.week_52_low, asset.currency)} – ${formatCurrency(asset.week_52_high, asset.currency)}` : '--' },
      { label: 'Volume', value: fmt(m.volume, (v) => formatNumber(v, { compact: true })) },
      { label: 'Avg Volume', value: fmt(asset.avg_volume, (v) => formatNumber(v, { compact: true })) },
      { label: 'Div Yield', value: fmt(m.dividend_yield, (v) => formatPercent(v * 100)) },
    ];
  }

  if (asset.asset_class === 'Crypto') {
    return [
      { label: 'Market Cap', value: fmt(m.market_cap, (v) => formatCurrency(v, asset.currency, { compact: true })) },
      { label: 'Rank', value: fmt(m.market_cap_rank, (v) => `#${v}`) },
      { label: '24h Volume', value: fmt(m.volume, (v) => formatCurrency(v, asset.currency, { compact: true })) },
      { label: 'Circulating Supply', value: fmt(m.circulating_supply, (v) => formatNumber(v, { compact: true, decimals: 0 })) },
      { label: 'Max Supply', value: fmt(asset.max_supply, (v) => formatNumber(v, { compact: true, decimals: 0 })) },
      { label: 'Dominance', value: fmt(m.dominance, (v) => formatPercent(v)) },
      { label: 'ATH', value: fmt(asset.ath, (v) => formatCurrency(v, asset.currency)) },
      { label: 'ATH Date', value: fmt(asset.ath_date, formatDate) },
      { label: 'ATL', value: fmt(asset.atl, (v) => formatCurrency(v, asset.currency)) },
      { label: 'ATL Date', value: fmt(asset.atl_date, formatDate) },
    ];
  }

  // Stock (default)
  return [
    { label: 'Prev Close', value: fmt(m.open, (v) => formatCurrency(v, asset.currency)) },
    { label: 'Open', value: fmt(m.open, (v) => formatCurrency(v, asset.currency)) },
    { label: 'Day Range', value: m.low != null && m.high != null ? `${formatCurrency(m.low, asset.currency)} – ${formatCurrency(m.high, asset.currency)}` : '--' },
    { label: '52W Range', value: asset.week_52_low != null && asset.week_52_high != null ? `${formatCurrency(asset.week_52_low, asset.currency)} – ${formatCurrency(asset.week_52_high, asset.currency)}` : '--' },
    { label: 'Market Cap', value: fmt(m.market_cap, (v) => formatCurrency(v, asset.currency, { compact: true })) },
    { label: 'Volume', value: fmt(m.volume, (v) => formatNumber(v, { compact: true })) },
    { label: 'Avg Volume', value: fmt(asset.avg_volume, (v) => formatNumber(v, { compact: true })) },
    { label: 'Beta', value: fmt(asset.beta, (v) => v.toFixed(2)) },
    { label: 'P/E (TTM)', value: fmt(m.pe_ratio, (v) => v.toFixed(2)) },
    { label: 'Forward P/E', value: fmt(m.forward_pe, (v) => v.toFixed(2)) },
    { label: 'EPS (TTM)', value: fmt(m.eps, (v) => formatCurrency(v, asset.currency)) },
    { label: 'Earnings Date', value: fmt(asset.earnings_date, formatDate) },
    { label: 'Div Yield', value: fmt(m.dividend_yield, (v) => formatPercent(v * 100)) },
    { label: 'Ex-Div Date', value: fmt(asset.ex_dividend_date, formatDate) },
    { label: '1Y Target Est', value: fmt(asset.target_est, (v) => formatCurrency(v, asset.currency)) },
    { label: 'PEG Ratio', value: fmt(asset.peg_ratio, (v) => v.toFixed(2)) },
  ];
}

export default function AssetStatsGrid({ asset }) {
  const items = getStatsItems(asset);

  return (
    <div className="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg mb-6">
      <div className="px-4 py-3 border-b border-[var(--border-primary)]">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">Key Statistics</h3>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {items.map(({ label, value }, i) => (
          <div
            key={label}
            className={cn(
              'px-4 py-3 border-b border-[var(--border-primary)]',
              (i + 1) % 4 !== 0 && 'lg:border-r',
              (i + 1) % 3 !== 0 && 'md:border-r',
              (i + 1) % 2 !== 0 && 'border-r md:border-r-0',
            )}
          >
            <p className="text-xs text-[var(--text-secondary)] mb-0.5">{label}</p>
            <p className="text-sm font-medium text-[var(--text-primary)]">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
