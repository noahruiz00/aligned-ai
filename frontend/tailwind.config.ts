import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#141311", soft: "#3A3833", muted: "#77716A" },
        gold: { DEFAULT: "#A9824A", light: "#C9A873", pale: "#EFE4D0", deep: "#8A6A3A" },
        paper: "#FAF8F3",
        cream: "#F3EFE6",
        line: "#E5DFD3",
        sage: "#6F8A6E",
        amber: "#B7833A",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      letterSpacing: { eyebrow: "0.28em" },
      boxShadow: {
        card: "0 1px 2px rgba(20,19,17,0.04), 0 8px 32px -12px rgba(20,19,17,0.10)",
      },
    },
  },
  plugins: [],
};

export default config;
