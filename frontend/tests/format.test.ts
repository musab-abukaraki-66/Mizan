import { describe, expect, it } from "vitest";
import { addMonths, monthIndex, monthLabel, num, periodOf, pValue, signed, spct } from "../src/lib/format";
import { monthTicks, toPoints } from "../src/lib/chart";

describe("formatting", () => {
  it("formats numbers with Latin digits in both languages", () => {
    expect(num(115.8155, "en", 2)).toBe("115.82");
    expect(num(115.8155, "ar", 2)).toBe("115.82");
    expect(num(null, "en")).toBe("–");
  });
  it("uses a true minus sign and explicit plus", () => {
    expect(num(-0.5, "en", 1)).toBe("−0.5");
    expect(signed(0.164, "en", 2)).toBe("+0.16");
    expect(spct(-1.234, "en", 1)).toBe("−1.2%");
    expect(num(-0.001, "en", 1)).toBe("0.0"); // no "-0.0"
  });
  it("round-trips month indices", () => {
    expect(periodOf(monthIndex("2026-09"))).toBe("2026-09");
    expect(addMonths("2026-11", 3)).toBe("2027-02");
  });
  it("localises month names (Levantine Arabic for Jordan)", () => {
    expect(monthLabel("2026-09", "en")).toBe("September 2026");
    expect(monthLabel("2026-09", "ar")).toContain("أيلول");
    expect(monthLabel("2026-01", "ar")).toContain("كانون الثاني");
  });
  it("formats p-values", () => {
    expect(pValue(0.0001, "en")).toBe("<0.001");
    expect(pValue(0.1234, "en")).toBe("0.123");
    expect(pValue(null, "en")).toBe("–");
  });
});

describe("chart helpers", () => {
  it("chooses calendar-aligned ticks within the budget", () => {
    const { ticks, step } = monthTicks(monthIndex("2022-01"), monthIndex("2027-03"), 8);
    expect(ticks.length).toBeLessThanOrEqual(8);
    expect(ticks.every((t) => t % step === 0)).toBe(true);
    const yearly = monthTicks(monthIndex("2006-01"), monthIndex("2026-09"), 10);
    expect(yearly.step).toBeGreaterThanOrEqual(24);
  });
  it("drops null points", () => {
    expect(toPoints(["2026-01", "2026-02"], [null, 2])).toEqual([{ t: monthIndex("2026-02"), v: 2 }]);
  });
});
