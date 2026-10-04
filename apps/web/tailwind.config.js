/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // por si luego quieres usar 'dark:' para temas automáticos
  theme: {
    extend: {
      colors: {
        neon: '#39FF14',
        fuchsia: '#ff00cc',
        ocean: '#3333ff',
        midnight: '#0a0a0a',
        glass: 'rgba(255, 255, 255, 0.05)',
      },
      boxShadow: {
        neon: '0 0 15px #39FF14',
        glow: '0 0 15px #ff00cc, 0 0 25px #3333ff',
      },
      fontFamily: {
        futuristic: ['"Segoe UI"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
