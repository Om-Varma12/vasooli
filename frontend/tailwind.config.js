/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        blue: 'var(--blue)',
        navy: 'var(--navy)',
        bg: 'var(--bg)',
        ink: 'var(--ink)',
        muted: 'var(--muted)',
        line: 'var(--line)',
        green: 'var(--green)',
        orange: 'var(--orange)',
        red: 'var(--red)',
        gray: 'var(--gray)',
        mint: 'var(--mint)',
        lav: 'var(--lav)',
      },
    },
  },
  plugins: [],
}
