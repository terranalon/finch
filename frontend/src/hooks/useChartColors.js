import { useMemo } from 'react'
import { useTheme } from '../contexts/ThemeContext'

/**
 * Returns resolved CSS variable colors for use in Recharts SVG props.
 * Re-computes whenever the theme toggles so charts re-render with correct colors.
 */
export function useChartColors() {
  const { theme } = useTheme()

  return useMemo(() => {
    const style = getComputedStyle(document.documentElement)
    const get = (varName) => style.getPropertyValue(varName).trim()

    return {
      accent: get('--accent-primary'),
      textSecondary: get('--text-secondary'),
      textTertiary: get('--text-tertiary'),
      borderPrimary: get('--border-primary'),
      positive: get('--positive'),
      negative: get('--negative'),
      bgSecondary: get('--bg-secondary'),
      bgTertiary: get('--bg-tertiary'),
    }
  }, [theme])
}
