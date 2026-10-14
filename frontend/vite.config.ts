import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The production bundle is written straight into the Python package (mizan/web) and served by FastAPI,
// so the demo laptop needs only Python at runtime - no Node.
export default defineConfig({
  base: process.env.VITE_STATIC === "1" ? "./" : "/", // static site may live under a sub-path (GitHub Pages)
  plugins: [react()],
  build: { outDir: process.env.VITE_STATIC === "1" ? "../site" : "../mizan/web", emptyOutDir: true, sourcemap: false, target: "es2022", chunkSizeWarningLimit: 700 },
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8765" } },
  test: { environment: "jsdom", globals: true, setupFiles: ["tests/setup.ts"], include: ["tests/**/*.test.{ts,tsx}"] },
});
