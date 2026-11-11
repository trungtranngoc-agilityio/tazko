import { defineConfig, devices } from "@playwright/test";

// e2e runs the real API and the web app (D13): the browser talks to the Vite
// server, which proxies API paths to the Python server. Sign-in uses a fake OIDC
// provider (M1-04).
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: "http://localhost:5173",
    viewport: { width: 1280, height: 800 },
    trace: "retain-on-failure",
  },
  projects: [
    { name: "light", use: { ...devices["Desktop Chrome"], colorScheme: "light" } },
    { name: "dark", use: { ...devices["Desktop Chrome"], colorScheme: "dark" } },
  ],
  webServer: [
    {
      command: "uv run --project backend tazko serve",
      url: "http://127.0.0.1:8791/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npm --prefix frontend run dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
