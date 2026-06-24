import type { Config } from "tailwindcss";

/**
 * Design system from PHASE5 spec. Colors are exposed as CSS variables (globals.css)
 * and mapped here. NOTE: the spec's background/surface/card/border values are highly
 * saturated; see FRONTEND_ARCHITECTURE.md for the design note. Implemented as specified.
 */
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#4F46E5",
        secondary: "#7C3AED",
        accent: "#06B6D4",
        success: "#5ba857",
        danger: "#eb1429",
        background: "#00d4ff",
        surface: "#3cacc3",
        card: "#945aa5",
        border: "#c40ff0",
        "text-primary": "#F9FAFB",
        "text-secondary": "#9CA3AF",
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
