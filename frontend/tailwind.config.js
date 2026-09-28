/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep navy/slate primary palette
        navy: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        // Off-white/paper backgrounds
        paper: {
          DEFAULT: '#fafaf9',
          dark: '#f5f5f4',
        },
        // Risk severity accent colors (reserved ONLY for risk indicators)
        risk: {
          low: '#10b981',      // green
          medium: '#f59e0b',   // amber
          high: '#ef4444',     // red
          critical: '#dc2626', // deep red
        },
      },
      fontFamily: {
        // Serif for headings/legal authority
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        // Sans-serif for body/UI
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      spacing: {
        // Consistent spacing scale
        '18': '4.5rem',
        '88': '22rem',
      },
      borderRadius: {
        // Consistent border-radius scale
        'DEFAULT': '0.375rem', // 6px
        'md': '0.5rem',        // 8px
        'lg': '0.75rem',       // 12px
        'xl': '1rem',          // 16px
      },
      boxShadow: {
        // Subtle shadow scale
        'sm': '0 1px 2px 0 rgba(15, 23, 42, 0.05)',
        'DEFAULT': '0 1px 3px 0 rgba(15, 23, 42, 0.08), 0 1px 2px -1px rgba(15, 23, 42, 0.08)',
        'md': '0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.08)',
        'lg': '0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.08)',
        'xl': '0 20px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.08)',
      },
      transitionDuration: {
        // Standard transition durations
        DEFAULT: '200ms',
      },
      transitionTimingFunction: {
        DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
}

