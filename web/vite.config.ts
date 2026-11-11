/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

// Dev: Vite on :5173 proxies server routes to `cargo run -- serve` on :8791.
const server = "http://127.0.0.1:8791";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    // design/tokens.css lives outside web/
    fs: { allow: [".."] },
    proxy: {
      "/health": server,
      "/auth": server,
      "/api": { target: server, ws: true },
      "/admin/api": server,
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
