import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";
export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        bindings: {
          BACKEND_ORIGIN: "https://lab.example.com",
          LAB_ENABLED: "true",
          ALLOWED_GITHUB_IDS: "123,456",
          GITHUB_CLIENT_ID: "test-client",
          GITHUB_CLIENT_SECRET: "fixture-not-a-secret",
          GEMINI_API_KEY: "fixture-gemini",
          GROQ_API_KEY: "fixture-groq",
        },
      },
    }),
  ],
  test: { include: ["test/**/*.test.ts"] },
});
