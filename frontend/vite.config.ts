/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

// Production: the web app is a static site (Cloudflare Pages) that calls the
// API at VITE_API_URL. Dev: VITE_API_URL is empty and Vite proxies the API
// paths to `uv run --project backend tazko serve` on :8791, so the browser sees one origin.
const server = "http://127.0.0.1:8791";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    // design/tokens.css lives outside frontend/
    fs: { allow: [".."] },
    proxy: {
      "/health": server,
      "/auth": server,
      "/api": server,
      "/admin/api": server,
      "/ws": { target: server, ws: true },
      "/cli": server,
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Budget: initial JS under 200 KB gzip (checked in M2-09).
    chunkSizeWarningLimit: 600,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
