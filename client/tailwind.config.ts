import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#f4f2ec',
        ink: '#1a2330',
        slate: '#43546a',
        line: '#d6dce3',
        panel: '#fcfbf8',
        accent: '#146356',
        warm: '#b16a2b',
      },
      boxShadow: {
        panel: '0 18px 40px -26px rgba(22, 33, 51, 0.45)',
      },
      fontFamily: {
        sans: ['IBM Plex Sans', 'Segoe UI', 'sans-serif'],
        display: ['Space Grotesk', 'Segoe UI', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config
