import { defineConfig, devices } from "@playwright/test";
import { SUPER_ADMIN } from "./tests/e2e/accounts";

// e2e runs the real API and the web app (D13): the browser talks to the Vite
// server, which proxies API paths to the Python server. Sign-in goes through a
// stand-in Google (tests/e2e/fake-google.mjs, D32) that the API reaches through
// TAZKO_GOOGLE_URL; Google's address is the callback's, so cookies land on the
// web origin as they do behind the tunnel.
// Test values shared with fake-google.mjs. Not secrets.
const api = {
  TAZKO_ENV: "development",
  TAZKO_DATA_DIR: ".e2e-data",
  TAZKO_PUBLIC_URL: "http://localhost:5173",
  TAZKO_GOOGLE_URL: "http://127.0.0.1:8792",
  TAZKO_GOOGLE_CLIENT_ID: "e2e-client",
  TAZKO_GOOGLE_CLIENT_SECRET: "e2e-secret",
};

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
    {
      name: "light",
      use: { ...devices["Desktop Chrome"], colorScheme: "light" },
    },
    {
      name: "dark",
      use: { ...devices["Desktop Chrome"], colorScheme: "dark" },
    },
  ],
  webServer: [
    {
      command: "node tests/e2e/fake-google.mjs",
      url: "http://127.0.0.1:8792/health",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      // `tazko admin` is the documented way to make the first super admin.
      command: [
        `node -e "require('fs').mkdirSync('.e2e-data', { recursive: true })"`,
        `uv run --project backend tazko admin --email ${SUPER_ADMIN}`,
        "uv run --project backend tazko serve",
      ].join(" && "),
      env: api,
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
