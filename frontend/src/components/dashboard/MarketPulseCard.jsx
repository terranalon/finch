import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { cn, formatPercent, getChangeColor } from '../../lib';
import api from '../../lib/api';
import { Skeleton, MiniSparkline } from '../ui';

export function MarketPulseCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPulse();
    let interval = setInterval(fetchPulse, 300_000);

    // Pause polling when tab is hidden to avoid wasted requests
    function handleVisibility() {
      if (document.hidden) {
        clearInterval(interval);
      } else {
        clearInterval(interval);
        fetchPulse();
        interval = setInterval(fetchPulse, 300_000);
      }
    }
    document.addEventListener('visibilitychange', handleVisibility);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);

  async function fetchPulse() {
    try {
      const resp = await api('/dashboard/market-pulse');
      const res = await resp.json();
      setData(res.items);
    } catch {
      // Silently fail - market pulse is non-critical
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
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
                <div className="w-12 h-5 flex-shrink-0">
                  <MiniSparkline data={item.sparkline} positive={isPositive} />
                </div>
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
