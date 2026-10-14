import { expect, test } from "@playwright/test";
import { noOverflow, open, trackConsole } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem("fresh")) {
      localStorage.clear();
      sessionStorage.setItem("fresh", "1");
    }
  });
});

test("Arabic RTL is the default and shows verified official figures", async ({ page }) => {
  const issues = trackConsole(page);
  await page.goto("/#/overview");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  await expect(page.locator("#headline")).toContainText("115.82");
  await expect(page.locator("#headline")).toContainText("2.73");
  await expect(page.locator("#prov-strip")).toContainText("بيانات المصدر الرسمي");
  await expect(page.locator("#prov-strip")).toContainText("أيلول 2026");
  expect(issues).toEqual([]);
});

test("language switch flips direction, text and persists", async ({ page }) => {
  await open(page);
  await page.getByRole("button", { name: /English|الإنجليزية/ }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("consumer prices");
  await expect(page.locator("#prov-strip")).toContainText("September 2026");
  await page.goto("/#/overview"); // no ?lang= -> the stored preference applies
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.getByRole("button", { name: /Arabic/ }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
});

test("RTL charts mirror time: latest observation sits on the left", async ({ page }) => {
  await open(page, "overview", "ar");
  const frame = page.locator(".chart__frame").first();
  await expect(frame).toBeVisible();
  const marker = await page.locator(".chart__marker").first().boundingBox();
  const box = await frame.boundingBox();
  expect(marker!.x).toBeLessThan(box!.x + box!.width / 2);
  await open(page, "overview", "en");
  const m2 = await page.locator(".chart__marker").first().boundingBox();
  const b2 = await page.locator(".chart__frame").first().boundingBox();
  expect(m2!.x).toBeGreaterThan(b2!.x + b2!.width / 2);
});

test("all five views render without console errors and without horizontal overflow", async ({ page }) => {
  const issues = trackConsole(page);
  for (const size of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(size);
    for (const lang of ["en", "ar"] as const) {
      for (const v of ["overview", "studio", "arena", "quality", "methods"]) {
        await open(page, v, lang);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await expect(page.locator(".errorbox")).toHaveCount(0);
        await page.waitForTimeout(250);
        await noOverflow(page);
      }
    }
  }
  expect(issues).toEqual([]);
});

test("Forecast Studio: horizon, model and measure update real computations", async ({ page }) => {
  await open(page, "studio", "en");
  await expect(page.locator("table").first().locator("tbody tr")).toHaveCount(3);
  await page.getByRole("radio", { name: "6 months" }).first().click();
  await expect(page.locator("table").first().locator("tbody tr")).toHaveCount(6);
  await page.getByRole("combobox", { name: "Model" }).selectOption("sarima");
  await expect(page.getByText("ARIMA(", { exact: false }).first()).toBeVisible();
  const before = await page.locator("table").first().locator("tbody tr").first().innerText();
  await page.getByRole("combobox", { name: "Model" }).selectOption("naive");
  await expect(page.locator("table").first().locator("tbody tr").first()).not.toHaveText(before);
  await page.getByRole("radio", { name: "Annual inflation" }).click();
  await expect(page.locator(".chart__tick").first()).toContainText("%");
});

test("Model Arena marks the selected model only from data and lists coverage", async ({ page }) => {
  await open(page, "arena", "en");
  const rows = page.getByTestId("arena-table").locator("tbody tr");
  await expect(rows).toHaveCount(5);
  await expect(page.getByTestId("arena-table").getByText("Selected")).toHaveCount(1);
  await page.getByRole("radio", { name: "1 month" }).first().click();
  await expect(page.getByTestId("arena-table").locator("tr.is-champion")).toContainText("SARIMA");
  await page.getByRole("radio", { name: /Final test/ }).click();
  await expect(page.getByTestId("arena-table")).toContainText("Test leader");
});

test("chart is keyboard accessible", async ({ page }) => {
  await open(page, "overview", "en");
  const frame = page.locator(".chart__frame").first();
  await frame.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator(".chart__tip")).toBeVisible();
  await expect(page.locator(".chart__tip")).toContainText("Forecast"); // starts at the last (forecast) month
  await page.keyboard.press("Home");
  await expect(page.locator(".chart__tip")).toContainText("Observed");
  await page.keyboard.press("Escape");
  await expect(page.locator(".chart__tip")).toHaveCount(0);
});

test("presentation mode, 2-minute walkthrough and reset", async ({ page }) => {
  await open(page, "studio", "en");
  await page.getByRole("button", { name: "Presentation mode" }).click();
  await expect(page.locator("body")).toHaveClass(/presenting/);
  await expect(page).toHaveURL(/#\/overview/);
  await expect(page.locator("#prov-strip")).toBeVisible(); // attribution stays
  await expect(page.locator("#caveats")).toBeVisible(); // caveats stay
  await page.getByRole("button", { name: "2-minute walkthrough" }).click();
  for (let i = 1; i <= 5; i++) {
    await expect(page.getByRole("dialog")).toContainText(`Step ${i} of 5`);
    await expect(page.locator('[data-spotlight="on"]')).toHaveCount(1);
    await page.getByRole("button", { name: i === 5 ? "Finish" : "Next" }).click();
  }
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Reset demo" }).click();
  await expect(page.locator("body")).not.toHaveClass(/presenting/);
  await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  await expect(page).toHaveURL(/#\/overview/);
});

test("presentation mode hides technical panels but keeps provenance", async ({ page }) => {
  await open(page, "quality", "en");
  await expect(page.getByText("Provenance details (technical)")).toBeVisible();
  await page.getByRole("button", { name: "Presentation mode" }).click();
  await page.getByRole("link", { name: "Data & Quality" }).click();
  await expect(page.getByText("Provenance details (technical)")).toBeHidden();
  await expect(page.getByText("Attribution and reuse")).toBeVisible();
});

test("API failure shows a clear message instead of a blank page", async ({ page }) => {
  await page.route("**/api/series", (r) => r.abort());
  await open(page, "overview", "en").catch(() => undefined);
  await page.goto("/?lang=en#/overview");
  await expect(page.locator(".errorbox").first()).toContainText(/not reachable|START_MIZAN/);
});

test("skip link and landmarks exist", async ({ page }) => {
  await open(page, "overview", "en");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();
  await expect(page.getByRole("main")).toBeVisible();
});
