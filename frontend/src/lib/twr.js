/**
 * Calculate Time-Weighted Return using Modified Dietz method.
 * Excludes the effect of cash flows (deposits/withdrawals) from returns.
 *
 * @param {Array} snapshots - Array of {date, value}, sorted ascending
 * @param {Array} cashFlows - Array of {date, amount} (positive=deposit)
 * @returns {Array} Array of {date, value, performance}
 */
export function calculateTWR(snapshots, cashFlows) {
  if (!snapshots || snapshots.length === 0) return [];

  const result = [];
  const startDate = new Date(snapshots[0].date);
  const startValue = snapshots[0].value;

  const cashFlowMap = new Map();
  if (cashFlows && cashFlows.length > 0) {
    cashFlows.forEach((cf) => {
      const dateKey = cf.date.split('T')[0];
      const existing = cashFlowMap.get(dateKey) || 0;
      cashFlowMap.set(dateKey, existing + cf.amount);
    });
  }

  snapshots.forEach((snapshot, index) => {
    const currentDate = new Date(snapshot.date);
    const currentValue = snapshot.value;

    if (index === 0) {
      result.push({ ...snapshot, performance: 0 });
      return;
    }

    const totalDays = Math.max(1, (currentDate - startDate) / (1000 * 60 * 60 * 24));

    let totalCashFlow = 0;
    let weightedCashFlow = 0;

    cashFlowMap.forEach((amount, dateStr) => {
      const cfDate = new Date(dateStr);
      if (cfDate > startDate && cfDate <= currentDate) {
        totalCashFlow += amount;
        const daysFromStart = (cfDate - startDate) / (1000 * 60 * 60 * 24);
        const weight = (totalDays - daysFromStart) / totalDays;
        weightedCashFlow += amount * weight;
      }
    });

    const denominator = startValue + weightedCashFlow;
    let performance = 0;

    if (denominator > 0) {
      performance = ((currentValue - startValue - totalCashFlow) / denominator) * 100;
    }

    result.push({ ...snapshot, performance });
  });

  return result;
}
