import { test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { open } from "./helpers";

const OUT = "../docs/screenshots";
test.beforeAll(() => mkdirSync(OUT, { recursive: true }));

for (const lang of ["en", "ar"] as const) {
  for (const v of ["overview", "studio", "arena", "quality", "methods"]) {
    test(`shot ${v} ${lang}`, async ({ page }) => {
      await page.addInitScript(() => localStorage.clear());
      await page.setViewportSize({ width: 1440, height: 900 });
      await open(page, v, lang);
      await page.waitForTimeout(1400);
      await page.screenshot({ path: `${OUT}/${v}-${lang}.png`, fullPage: v !== "overview" ? false : false });
    });
  }
}

test("shot presentation ar", async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, "overview", "ar", "&present=1");
  await page.waitForTimeout(1400);
  await page.screenshot({ path: `${OUT}/presentation-ar.png` });
});

test("shot mobile", async ({ page }) => {
  await page.addInitScript(() => localStorage.clear());
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, "overview", "en");
  await page.waitForTimeout(1400);
  await page.screenshot({ path: `${OUT}/mobile-en.png` });
});
