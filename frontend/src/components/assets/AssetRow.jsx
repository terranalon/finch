import { cn, formatCurrency, getChangeIndicator, ASSET_COLORS } from '../../lib';
import { StarOutlineIcon, StarFilledIcon, BriefcaseIcon } from './icons';
import { SparklineCell } from './SparklineCell';
import { PERIOD_KEYS } from './constants';

// Extend shared ASSET_COLORS with the "Stock" alias used in asset data
const ICON_COLORS = { ...ASSET_COLORS, Stock: '#3B82F6' };

function formatCompact(value) {
  if (value == null) return '\u2014';
  if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function formatPrice(value, currency) {
  if (value == null) return '\u2014';
  if (value >= 10000) return formatCurrency(value, currency, { decimals: 0 });
  if (value >= 1) return formatCurrency(value, currency, { decimals: 2 });
  if (value >= 0.01) return formatCurrency(value, currency, { decimals: 4 });
  return formatCurrency(value, currency, { decimals: 6 });
}

export function AssetRow({ asset, position, period, currency, onToggleFavorite, onClick }) {
  const keys = PERIOD_KEYS[period] || PERIOD_KEYS['1d'];
  const changePct = asset[keys.pct];
  const changeAbs = asset[keys.change];
  const isPositive = changePct > 0;
  const isNegative = changePct < 0;
  const iconColor = ICON_COLORS[asset.asset_class] || 'var(--slate-clr)';
  const initials = (asset.symbol || '??').slice(0, 2);

  return (
    <tr
      onClick={() => onClick(asset)}
      className="hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer group"
    >
      {/* Star */}
      <td className="px-4 py-3 w-[40px]">
        <button
          onClick={(e) => { e.stopPropagation(); onToggleFavorite(asset.id); }}
          className={cn(
            'text-[16px] leading-none p-0.5 cursor-pointer transition-colors bg-transparent border-none',
            asset.is_favorite ? 'text-[var(--amber)]' : 'text-[var(--text-faint)] hover:text-[var(--amber)]'
          )}
        >
          {asset.is_favorite ? (
            <StarFilledIcon className="w-4 h-4" />
          ) : (
            <StarOutlineIcon className="w-4 h-4" />
          )}
        </button>
      </td>

      {/* Asset */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center text-[11px] font-bold text-white"
            style={{ backgroundColor: iconColor }}
          >
            {initials}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-[13px] text-[var(--text-primary)]">{asset.symbol}</span>
              {position && (
                <span
                  className="inline-flex items-center justify-center w-[18px] h-[18px] rounded-full bg-[var(--accent-primary)]/15 flex-shrink-0"
                  title="In your portfolio"
                >
                  <BriefcaseIcon className="w-[10px] h-[10px] text-[var(--accent-primary)]" />
                </span>
              )}
            </div>
            <p className="text-[12px] text-[var(--text-faint)] mt-px truncate">
              {asset.name}
            </p>
          </div>
        </div>
      </td>

      {/* Price */}
      <td className="px-4 py-3 text-right w-[120px]">
        <span className="font-mono tabular-nums text-[13px] text-[var(--text-primary)]">
          {formatPrice(asset.last_fetched_price, asset.currency)}
        </span>
      </td>

      {/* Change */}
      <td className="px-4 py-3 text-right w-[140px]">
        <div className="flex flex-col items-end">
          <span
            className={cn(
              'text-[13px] font-semibold font-mono tabular-nums flex items-center gap-[3px]',
              isPositive && 'text-[var(--positive)]',
              isNegative && 'text-[var(--negative)]',
              !isPositive && !isNegative && 'text-[var(--text-tertiary)]'
            )}
          >
            {changePct != null ? (
              <>
                <span className="text-[10px]">
                  {getChangeIndicator(changePct)}
                </span>
                {changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%
              </>
            ) : '\u2014'}
          </span>
          {changeAbs != null && (
            <span
              className={cn(
                'text-[11px] font-mono tabular-nums mt-px',
                isPositive && 'text-[var(--positive)]',
                isNegative && 'text-[var(--negative)]',
                !isPositive && !isNegative && 'text-[var(--text-tertiary)]'
              )}
            >
              {changeAbs >= 0 ? '+' : ''}
              {Math.abs(changeAbs) >= 1
                ? formatCurrency(changeAbs, currency, { decimals: 2 })
                : `${changeAbs < 0 ? '-' : ''}$${Math.abs(changeAbs).toFixed(4)}`}
            </span>
          )}
        </div>
      </td>

      {/* Market Cap */}
      <td className="px-4 py-3 text-right w-[120px]">
        <span className="font-mono tabular-nums text-[13px] text-[var(--text-secondary)]">
          {asset.market_cap != null ? formatCompact(asset.market_cap) : '\u2014'}
        </span>
      </td>

      {/* Volume */}
      <td className="px-4 py-3 text-right w-[100px] font-mono tabular-nums text-[13px] text-[var(--text-secondary)]">
        {'\u2014'}
      </td>

      {/* Sparkline */}
      <td className="px-4 py-3 text-right w-[100px]">
        <SparklineCell
          assetId={asset.id}
          changePct={changePct}
          period={period}
        />
      </td>
    </tr>
  );
}
