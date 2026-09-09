import type { Config } from 'tailwindcss';

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        space: {
          950: '#06090E',
          900: '#0A0E14',
          850: '#0D1117',
          800: '#161B22',
          700: '#21262D',
        },
        aurora: {
          50: '#ECFEFF',
          100: '#CFFAFE',
          200: '#A5F3FC',
          300: '#67E8F9',
          400: '#22D3EE',
          500: '#00D4FF',
          600: '#0891B2',
        },
        violet: {
          accent: '#8B5CF6',
          light: '#A78BFA',
        },
        emerald: {
          accent: '#10B981',
          light: '#34D399',
        },
        rose: {
          accent: '#F43F5E',
          light: '#FB7185',
        },
        text: {
          primary: '#F0F6FC',
          secondary: '#8B949E',
          muted: '#484F58',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        sm: '6px',
        md: '10px',
        xl: '16px',
        '2xl': '20px',
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glow-cyan': '0 0 24px -4px rgba(0, 212, 255, 0.3)',
        'glow-emerald': '0 0 24px -4px rgba(16, 185, 129, 0.3)',
        'glow-rose': '0 0 24px -4px rgba(244, 63, 94, 0.3)',
      },
      keyframes: {
        'radar-sweep': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'scan-line': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.6', transform: 'scale(1.05)' },
        },
      },
      animation: {
        'radar-sweep': 'radar-sweep 6s linear infinite',
        'scan-line': 'scan-line 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        shimmer: 'shimmer 2s ease-in-out infinite',
        'pulse-glow': 'pulseGlow 2.5s ease-in-out infinite',
      },
    },
  },
  plugins: [],
} satisfies Config;
