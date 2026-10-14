import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";

// Use the system Chromium when present (offline / CI sandboxes); otherwise Playwright's own browser.
const candidates = [process.env.CHROMIUM_PATH, "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome"];
const executablePath = candidates.find((p) => p && existsSync(p));

export default defineConfig({
  testDir: "e2e",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.MIZAN_URL ?? "http://127.0.0.1:8765",
    ...devices["Desktop Chrome"],
    launchOptions: { executablePath, args: ["--no-sandbox"] },
    trace: "off",
  },
});
