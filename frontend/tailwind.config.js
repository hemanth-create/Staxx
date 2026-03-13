/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Staxx premium palette
        "staxx-dark": "#09090b",
        "staxx-surface": "rgba(255,255,255,0.03)",
        "staxx-border": "rgba(255,255,255,0.06)",
        "sky": {
          500: "#0ea5e9",
        },
        "green": {
          500: "#22c55e",
        },
        "amber": {
          500: "#f59e0b",
        },
        "red": {
          500: "#ef4444",
        },
      },
      fontFamily: {
        // Inter for body, JetBrains Mono for numbers
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      backdropBlur: {
        md: "20px",
      },
      animation: {
        shimmer: "shimmer 1.5s infinite",
      },
      keyframes: {
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
      },
    },
  },
  plugins: [],
};
