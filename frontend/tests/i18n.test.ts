import { describe, expect, it } from "vitest";
import { ar } from "../src/i18n/ar";
import { en } from "../src/i18n/en";
import { makeT } from "../src/i18n";

describe("i18n", () => {
  it("has identical keys in both languages and no empty strings", () => {
    expect(Object.keys(ar).sort()).toEqual(Object.keys(en).sort());
    for (const [k, v] of [...Object.entries(en), ...Object.entries(ar)]) expect(v.trim(), k).not.toBe("");
  });
  it("uses the same placeholders in both languages", () => {
    const ph = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
    for (const k of Object.keys(en) as (keyof typeof en)[]) expect(ph(ar[k]), k).toEqual(ph(en[k]));
  });
  it("interpolates and isolates numeric tokens in Arabic", () => {
    expect(makeT("en")("tour.step", { n: 2, total: 5 })).toBe("Step 2 of 5");
    expect(makeT("ar")("tour.step", { n: "2", total: "5" })).toContain("⁦2⁩");
    expect(makeT("ar")("ov.fcLegend", { model: "SARIMA" })).not.toContain("⁦");
  });
  it("never ships demo/placeholder text", () => {
    for (const v of [...Object.values(en), ...Object.values(ar)]) expect(v).not.toMatch(/lorem|TODO|placeholder/i);
  });
});
