import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "node",
    include: ["tests-ts/**/*.test.ts"],
    // Avoid pulling Next runtime into unit tests; modules under test are pure
    // helpers (timing-safe compare, signature verify, redirect resolver).
    globals: false,
  },
});
