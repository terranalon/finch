/**
 * Calculate Time-Weighted Return using daily-linked sub-period chaining.
 *
 * For each consecutive pair of snapshots, computes the sub-period return
 * by removing the effect of any cash flows (deposits/withdrawals) that
 * occurred on that date. The sub-period returns are then geometrically
 * linked to produce a cumulative TWR curve.
 *
 * Formula per sub-period:
 *   (1 + r_i) = (V_i - CF_i) / V_{i-1}
 *
 * Guards:
 *   - Account scope changes (account_count differs) reset the cumulative
 *     return, because adding/removing accounts changes the portfolio
 *     composition fundamentally (comparing across compositions is meaningless)
 *   - Extreme daily ratios (>300% gain or >90% loss) are skipped as data anomalies
 *   - Zero/negative values are skipped
 *
 * @param {Array} snapshots - Array of {date, value, account_count?}, sorted ascending
 * @param {Array} cashFlows - Array of {date, amount} (positive=deposit)
 * @returns {Array} Array of {date, value, performance}
 */
export function calculateTWR(snapshots, cashFlows) {
  if (!snapshots || snapshots.length === 0) return [];

  // Index cash flows by date
  const cfMap = new Map();
  if (cashFlows && cashFlows.length > 0) {
    cashFlows.forEach((cf) => {
      const dateKey = cf.date.split('T')[0];
      cfMap.set(dateKey, (cfMap.get(dateKey) || 0) + cf.amount);
    });
  }

  let cumulative = 1;
  const result = [{ ...snapshots[0], performance: 0 }];

  for (let i = 1; i < snapshots.length; i++) {
    const prev = snapshots[i - 1];
    const curr = snapshots[i];
    const cf = cfMap.get(curr.date.split('T')[0]) || 0;

    const scopeChanged =
      prev.account_count != null &&
      curr.account_count != null &&
      prev.account_count !== curr.account_count;

    if (scopeChanged) {
      const ratio = curr.account_count / prev.account_count;
      if (ratio > 2 || ratio < 0.5) {
        // Fundamental composition change (account count more than doubled/halved).
        // Chaining returns across radically different portfolios is meaningless,
        // so reset the measurement baseline.
        cumulative = 1;
      }
      // Small scope changes: skip this sub-period (neutral return) but keep chain.
    } else if (prev.value > 0 && curr.value > 0) {
      const ratio = (curr.value - cf) / prev.value;
      // Only apply if the daily return is within reasonable bounds.
      // Extreme ratios indicate data quality issues, not real returns.
      if (ratio > 0.1 && ratio < 4) {
        cumulative *= ratio;
      }
    }

    result.push({
      ...curr,
      performance: Math.round((cumulative - 1) * 10000) / 100,
    });
  }

  return result;
}
