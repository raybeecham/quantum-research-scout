import { defineConfig } from "vitest/config";
// The Worker only calls fetch, so plain Node tests with a stub are enough.
export default defineConfig({ test: { include: ["test/**/*.test.ts"] } });
