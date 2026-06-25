import type { Config } from "tailwindcss";

/**
 * Design system. Colors are driven by the CSS variables defined in globals.css so the
 * practical dark palette (--bg/--surface/--card/--border) is the single source of truth —
 * Tailwind utilities (bg-surface, border-border, …) and the .glass class now agree.
 */
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "var(--primary)",
        secondary: "var(--secondary)",
        accent: "var(--accent)",
        success: "var(--success)",
        danger: "var(--danger)",
        background: "var(--bg)",
        surface: "var(--surface)",
        card: "var(--card)",
        border: "var(--border)",
        "text-primary": "var(--text-primary)",
        "text-secondary": "var(--text-secondary)",
      },
      fontFamily: {
        brand: ["var(--font-jakarta)", "system-ui", "sans-serif"],
        heading: ["var(--font-jakarta)", "system-ui", "sans-serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "monospace"],
      },
      fontSize: {
        hero: ["64px", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        h1: ["48px", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        h2: ["36px", { lineHeight: "1.15" }],
        h3: ["28px", { lineHeight: "1.2" }],
        "body-lg": ["18px", { lineHeight: "1.6" }],
        body: ["16px", { lineHeight: "1.6" }],
        small: ["14px", { lineHeight: "1.5" }],
        caption: ["12px", { lineHeight: "1.4" }],
      },
      borderRadius: { xl: "14px", "2xl": "20px" },
    },
  },
  plugins: [],
};
export default config;
