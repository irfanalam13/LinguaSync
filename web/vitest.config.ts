import { defineConfig, configDefaults } from "vitest/config";
import path from "node:path";

export default defineConfig({
  esbuild: { jsx: "automatic" }, // React 17+ automatic JSX runtime (no `import React`)
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    exclude: [...configDefaults.exclude, "e2e/**"], // Playwright owns e2e/
  },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
});
