import { expect, type Page } from "@playwright/test";

export function trackConsole(page: Page): string[] {
  const issues: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") issues.push(`${m.type()}: ${m.text()}`);
  });
  page.on("pageerror", (e) => issues.push(`pageerror: ${e.message}`));
  return issues;
}

export async function open(page: Page, hash = "overview", lang: "ar" | "en" = "ar", extra = ""): Promise<void> {
  await page.goto(`/?lang=${lang}${extra}#/${hash}`);
  await expect(page.locator("#prov-strip")).toContainText(/\d{4}/);
}

export async function noOverflow(page: Page): Promise<void> {
  const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
  expect(o.sw, `page scrollWidth ${o.sw} > viewport ${o.cw}`).toBeLessThanOrEqual(o.cw + 1);
}
