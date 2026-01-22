/**
 * Format a number as currency
 * @param {number} value - The value to format
 * @param {string} currency - Currency code (USD, ILS, etc.)
 * @param {object} options - Additional options
 * @returns {string} Formatted currency string
 */
export function formatCurrency(value, currency = 'USD', options = {}) {
  if (value === null || value === undefined) return '-';

  const { compact = false, decimals = 2 } = options;

  // Handle compact notation for large numbers
  if (compact && Math.abs(value) >= 1000) {
    return formatCompactCurrency(value, currency);
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format large currency values in compact notation (1.2M, 45.3K)
 */
function formatCompactCurrency(value, currency = 'USD') {
  const symbols = { USD: '$', ILS: '\u20AA', EUR: '\u20AC', GBP: '\u00A3', CAD: 'CA$', AUD: 'A$', CHF: 'CHF ', JPY: '\u00A5' };
  const symbol = symbols[currency] || currency + ' ';

  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (absValue >= 1_000_000_000) {
    return `${sign}${symbol}${(absValue / 1_000_000_000).toFixed(1)}B`;
  }
  if (absValue >= 1_000_000) {
    return `${sign}${symbol}${(absValue / 1_000_000).toFixed(1)}M`;
  }
  if (absValue >= 1_000) {
    return `${sign}${symbol}${(absValue / 1_000).toFixed(1)}K`;
  }
  return formatCurrency(value, currency);
}

/**
 * Format a number as a percentage
 * @param {number} value - The percentage value
 * @param {object} options - Additional options
 * @returns {string} Formatted percentage string
 */
export function formatPercent(value, options = {}) {
  if (value === null || value === undefined) return '-';

  const { decimals = 2, showSign = true } = options;
  const sign = showSign && value > 0 ? '+' : '';

  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format a number with proper separators
 * @param {number} value - The value to format
 * @param {object} options - Additional options
 * @returns {string} Formatted number string
 */
export function formatNumber(value, options = {}) {
  if (value === null || value === undefined) return '-';

  const { decimals = 2, compact = false } = options;

  if (compact && Math.abs(value) >= 1000) {
    return formatCompactNumber(value);
  }

  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format large numbers in compact notation
 */
function formatCompactNumber(value) {
  const absValue = Math.abs(value);
  const sign = value < 0 ? '-' : '';

  if (absValue >= 1_000_000_000) {
    return `${sign}${(absValue / 1_000_000_000).toFixed(1)}B`;
  }
  if (absValue >= 1_000_000) {
    return `${sign}${(absValue / 1_000_000).toFixed(1)}M`;
  }
  if (absValue >= 1_000) {
    return `${sign}${(absValue / 1_000).toFixed(1)}K`;
  }
  return value.toFixed(2);
}

/**
 * Format a date string
 * @param {string|Date} dateValue - The date to format
 * @param {object} options - Additional options
 * @returns {string} Formatted date string
 */
export function formatDate(dateValue, options = {}) {
  if (!dateValue) return '-';

  const { format = 'short', relative = false } = options;

  const date = typeof dateValue === 'string' ? new Date(dateValue) : dateValue;

  if (relative) {
    return formatRelativeDate(date);
  }

  const formatOptions = {
    short: { month: 'short', day: 'numeric' },
    medium: { month: 'short', day: 'numeric', year: 'numeric' },
    long: { month: 'long', day: 'numeric', year: 'numeric' },
    full: { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' },
  };

  return new Intl.DateTimeFormat('en-US', formatOptions[format] || formatOptions.short).format(date);
}

/**
 * Format a date as relative time (e.g., "2h ago", "3 days ago")
 */
function formatRelativeDate(date) {
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return formatDate(date, { format: 'short' });
}

/**
 * Get color class for a value change (positive/negative)
 * @param {number} value - The value to check
 * @returns {string} Tailwind color class
 */
export function getChangeColor(value) {
  if (value === null || value === undefined || value === 0) {
    return 'text-slate-500';
  }
  return value > 0 ? 'text-positive dark:text-positive-dark' : 'text-negative dark:text-negative-dark';
}

/**
 * Get directional indicator for a value change
 * @param {number} value - The value to check
 * @returns {string} Arrow indicator
 */
export function getChangeIndicator(value) {
  if (value === null || value === undefined || value === 0) return '';
  return value > 0 ? '\u25B2' : '\u25BC'; // ▲ or ▼
}

/**
 * Format a price change with indicator and color info
 * @param {number} change - The change amount
 * @param {number} changePercent - The percentage change
 * @param {string} currency - Currency code
 * @returns {object} Formatted change info
 */
export function formatPriceChange(change, changePercent, currency = 'USD') {
  const indicator = getChangeIndicator(change);
  const colorClass = getChangeColor(change);
  const formattedChange = formatCurrency(Math.abs(change), currency, { compact: true });
  const formattedPercent = formatPercent(changePercent);

  return {
    indicator,
    colorClass,
    change: formattedChange,
    percent: formattedPercent,
    display: `${indicator} ${formattedChange} (${formattedPercent})`,
  };
}
