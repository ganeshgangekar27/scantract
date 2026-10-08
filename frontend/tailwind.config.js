/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: 'var(--color-primary)',
          dark: 'var(--color-primary-dark)',
        },
        accent: 'var(--color-accent)',
        background: 'var(--color-background)',
        surface: 'var(--color-surface)',
        border: 'var(--color-border)',
        text: {
          primary: 'var(--color-text-primary)',
          secondary: 'var(--color-text-secondary)',
        },
        severity: {
          high: {
            DEFAULT: 'var(--color-severity-high)',
            bg: 'var(--color-severity-high-bg)',
            border: 'var(--color-severity-high-border)',
          },
          medium: {
            DEFAULT: 'var(--color-severity-medium)',
            bg: 'var(--color-severity-medium-bg)',
            border: 'var(--color-severity-medium-border)',
          },
          low: {
            DEFAULT: 'var(--color-severity-low)',
            bg: 'var(--color-severity-low-bg)',
            border: 'var(--color-severity-low-border)',
          },
          safe: {
            DEFAULT: 'var(--color-severity-safe)',
            bg: 'var(--color-severity-safe-bg)',
            border: 'var(--color-severity-safe-border)',
          },
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      borderRadius: {
        'DEFAULT': '14px',
        'md': '14px',
        'lg': '16px',
        'xl': '16px',
      },
      boxShadow: {
        'sm': '0 1px 2px 0 rgba(15, 23, 42, 0.05)',
        'DEFAULT': '0 2px 4px 0 rgba(15, 23, 42, 0.06)',
        'md': '0 4px 8px -2px rgba(15, 23, 42, 0.08)',
        'lg': '0 12px 16px -4px rgba(15, 23, 42, 0.10)',
      },
      transitionDuration: {
        DEFAULT: '200ms',
      },
      transitionTimingFunction: {
        DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
    },
  },
  plugins: [],
}