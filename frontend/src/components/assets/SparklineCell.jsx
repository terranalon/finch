const PERIOD_INDEX = { '1d': 0, '1w': 1, '1m': 2 };

function seededRand(seed) {
  let s = seed;
  return function next() {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

function generateSparkPath(assetId, periodIdx, changePct) {
  const rand = seededRand(assetId * 17 + periodIdx * 31 + 7);
  const w = 80;
  const h = 28;
  const pts = 12;
  const step = w / (pts - 1);
  const magnitude = Math.min(Math.abs(changePct) / 20, 1);
  const dir = -Math.sign(changePct);

  const points = [];
  for (let i = 0; i < pts; i++) {
    const t = i / (pts - 1);
    const trend = dir * magnitude * t * (h * 0.6);
    const noise = (rand() - 0.5) * h * 0.35;
    const y = h / 2 + trend + noise;
    points.push([i * step, Math.max(2, Math.min(h - 2, y))]);
  }

  let d = `M${points[0][0].toFixed(1)},${points[0][1].toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev[0] + curr[0]) / 2;
    d += ` C${cpx.toFixed(1)},${prev[1].toFixed(1)} ${cpx.toFixed(1)},${curr[1].toFixed(1)} ${curr[0].toFixed(1)},${curr[1].toFixed(1)}`;
  }
  return d;
}

export function SparklineCell({ assetId, changePct, period }) {
  const periodIdx = PERIOD_INDEX[period] ?? 0;
  const pct = changePct ?? 0;
  const path = generateSparkPath(assetId, periodIdx, pct);
  let color = 'var(--text-tertiary)';
  if (pct > 0) color = 'var(--positive)';
  else if (pct < 0) color = 'var(--negative)';

  return (
    <svg width="80" height="28" viewBox="0 0 80 28" className="block">
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
