/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: { 50: '#f1f4f9', 100: '#e1e7f1', 200: '#c3cfe3', 300: '#9bb0d0', 400: '#6f8bb8', 500: '#4a6a9b', 600: '#35537f', 700: '#25416a', 800: '#1b3157', 900: '#122443' },
        paper: '#f7f8fa',
        ok: { 50: '#ecf8f1', 100: '#d3f0e0', 600: '#1f8a54', 700: '#176c42' },
      },
      fontFamily: { sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'] },
      boxShadow: { card: '0 1px 2px rgba(18,36,67,0.06)' },
    },
  },
  plugins: [],
};
