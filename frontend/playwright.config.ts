import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — drives the running dev stack (docker compose) by
 * default. To target a different host set E2E_BASE_URL.
 *
 *   pnpm e2e:install   # once: download chromium + deps
 *   pnpm e2e           # run all specs against http://localhost:3001
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // tests share a single DB; serialise for determinism
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3001",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
