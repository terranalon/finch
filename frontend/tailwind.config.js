/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Primary accent - Deep Blue
        accent: {
          DEFAULT: '#2563EB',
          light: '#DBEAFE',
          hover: '#1D4ED8',
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
          900: '#1E3A8A',
        },
        // Semantic colors
        positive: {
          DEFAULT: '#059669',
          light: '#D1FAE5',
          dark: '#10B981',
          bg: '#D1FAE5',
          'bg-dark': '#064E3B',
        },
        negative: {
          DEFAULT: '#DC2626',
          light: '#FEE2E2',
          dark: '#EF4444',
          bg: '#FEE2E2',
          'bg-dark': '#7F1D1D',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Menlo', 'monospace'],
      },
      borderRadius: {
        sm: '6px',
        DEFAULT: '8px',
        md: '8px',
        lg: '12px',
        xl: '16px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
        DEFAULT: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
      },
      fontSize: {
        '4xl': ['2.25rem', { lineHeight: '2.5rem', fontWeight: '700' }],
        '2xl': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
        xl: ['1.25rem', { lineHeight: '1.75rem', fontWeight: '600' }],
        lg: ['1.125rem', { lineHeight: '1.75rem', fontWeight: '500' }],
      },
    },
  },
  plugins: [],
}