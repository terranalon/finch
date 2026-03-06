import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatPercent, getChangeColor } from '../../lib';
import api from '../../lib/api';
import { Skeleton } from '../ui';

function MiniSparkline({ data, positive }) {
  if (!data || data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 48;
  const h = 20;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 2) - 1;
    return `${x},${y}`;
  });
  const color = positive ? 'var(--positive)' : 'var(--negative)';

  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-12 h-5 flex-shrink-0">
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function MarketPulseCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPulse();
    const interval = setInterval(fetchPulse, 300_000);
    return () => clearInterval(interval);
  }, []);

  async function fetchPulse() {
    try {
      const res = await api('/api/dashboard/market-pulse');
      setData(res.items);
    } catch {
      // Silently fail - market pulse is non-critical
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card flex-1 min-h-0 overflow-y-auto">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-semibold">Markets</span>
        <Link to="/assets" className="text-[12px] text-accent hover:text-accent-hover font-medium">
          All assets &rarr;
        </Link>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-10 w-full rounded" />)}
        </div>
      ) : !data || data.length === 0 ? (
        <div className="text-center py-6 text-[var(--text-tertiary)] text-xs">No market data available</div>
      ) : (
        <div className="flex flex-col">
          {data.map((item) => {
            const isPositive = (item.day_change_pct || 0) >= 0;
            return (
              <div
                key={item.symbol}
                className="flex items-center gap-2 py-2.5 border-b border-[var(--border-primary)] last:border-b-0"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-[12px] font-semibold text-[var(--text-primary)] truncate">
                    {item.name}
                  </div>
                  <div className="text-[10px] text-[var(--text-tertiary)]">{item.symbol}</div>
                </div>
                <MiniSparkline data={item.sparkline} positive={isPositive} />
                <div className="text-right flex-shrink-0 min-w-[60px]">
                  <div className="text-[12px] font-mono tabular-nums font-medium">
                    {item.price != null ? `$${item.price.toLocaleString()}` : '--'}
                  </div>
                  <div className={cn('text-[10px] font-mono tabular-nums font-medium', getChangeColor(item.day_change_pct))}>
                    {item.day_change_pct != null ? formatPercent(item.day_change_pct) : '--'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
