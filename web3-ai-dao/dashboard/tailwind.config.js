/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        icarus: {
          bg: '#0a0a1a',
          card: '#12122a',
          border: '#1e1e4a',
          accent: '#6c5ce7',
          'accent-light': '#a29bfe',
          green: '#00cec9',
          red: '#ff7675',
          text: '#dfe6e9',
          muted: '#636e72',
        },
      },
    },
  },
  plugins: [],
};
