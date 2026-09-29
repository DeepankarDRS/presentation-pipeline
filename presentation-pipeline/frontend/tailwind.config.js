/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#EEF5FF',
          100: '#D9E8FF',
          200: '#BBD6FE',
          300: '#8CBBFD',
          400: '#5696FA',
          500: '#2F77F3',
          600: '#1E6FE8',
          700: '#1753C4',
          800: '#18459E',
          900: '#193D7D',
        },
      },
      boxShadow: {
        soft: '0 1px 2px rgba(16, 24, 40, 0.04), 0 4px 16px rgba(16, 24, 40, 0.06)',
        lift: '0 4px 12px rgba(16, 24, 40, 0.08), 0 12px 32px rgba(16, 24, 40, 0.08)',
      },
    },
  },
  plugins: [],
};
