/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        wpr: {
          teal: "#0d7377",
          "teal-dark": "#095456",
          "teal-light": "#e6f3f3",
          cream: "#f5f0e8",
          "cream-dark": "#ebe4d8",
          ink: "#1c1917",
          "ink-light": "#44403c",
          "ink-muted": "#78716c",
          rule: "#d6d0c4",
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', "Georgia", "serif"],
        body: ['"Source Sans 3"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
    },
  },
  plugins: [],
};
