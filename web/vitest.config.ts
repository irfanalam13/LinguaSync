import { defineConfig, configDefaults } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()], // handles automatic JSX runtime (no `import React`)
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    exclude: [...configDefaults.exclude, "e2e/**"], // Playwright owns e2e/
  },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
