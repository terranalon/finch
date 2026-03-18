import { useId } from 'react';

/**
 * Tiny SVG sparkline for inline use in tables and cards.
 *
 * Accepts either:
 *   - `data` as an array of numbers (raw values)
 *   - `data` as an array of objects with a `value` property
 *
 * The viewBox is always 100x40 (internal coordinate space).
 * Rendered size is controlled via `width` and `height` props (in pixels).
 *
 * @param {Object} props
 * @param {Array} props.data - Sparkline data points
 * @param {boolean} props.positive - Whether to use positive (green) or negative (red) color
 * @param {number} [props.width=48] - Display width in pixels
 * @param {number} [props.height=20] - Display height in pixels
 * @param {boolean} [props.filled=false] - Whether to render a gradient fill beneath the line
 * @param {string} [props.className] - Additional CSS classes
 */
const VB_W = 100;
const VB_H = 40;

export function MiniSparkline({ data, positive, width = 48, height = 20, filled = false, className = '' }) {
  const gradId = useId();
  if (!data || data.length < 2) return null;

  const values = typeof data[0] === 'number' ? data : data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * VB_W;
    const y = VB_H - ((v - min) / range) * (VB_H - 4) - 2;
    return `${x},${y}`;
  });
  const color = positive ? 'var(--positive)' : 'var(--negative)';
  const lineD = `M${points.join(' L')}`;
  const fillD = filled ? `${lineD} L${VB_W},${VB_H} L0,${VB_H} Z` : null;

  return (
    <svg
      viewBox={`0 0 ${VB_W} ${VB_H}`}
      preserveAspectRatio="none"
      className={`flex-shrink-0 block ${className}`}
      style={{ width, height }}
    >
      {filled && (
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" style={{ stopColor: color, stopOpacity: 0.18 }} />
            <stop offset="100%" style={{ stopColor: color, stopOpacity: 0 }} />
          </linearGradient>
        </defs>
      )}
      {filled && <path d={fillD} fill={`url(#${gradId})`} />}
      {filled ? (
        <path d={lineD} fill="none" style={{ stroke: color }} strokeWidth="2" strokeLinecap="round" />
      ) : (
        <polyline
          points={points.join(' ')}
          fill="none"
          style={{ stroke: color }}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}
