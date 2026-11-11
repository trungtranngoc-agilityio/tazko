import { defineConfig, devices } from "@playwright/test";

// e2e runs against the real binary. Sign-in uses a fake OIDC provider (M1-04).
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: "http://127.0.0.1:8791",
    viewport: { width: 1280, height: 800 },
    trace: "retain-on-failure",
  },
  projects: [
    { name: "light", use: { ...devices["Desktop Chrome"], colorScheme: "light" } },
    { name: "dark", use: { ...devices["Desktop Chrome"], colorScheme: "dark" } },
  ],
  webServer: {
    command: "cargo run -- serve",
    url: "http://127.0.0.1:8791/health",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
