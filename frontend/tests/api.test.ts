import { describe, expect, it } from "vitest";
import { resolveApiPath } from "../src/lib/api";

describe("static API path mapping", () => {
  it("is the identity when serving from the Python API", () => {
    expect(resolveApiPath("/api/forecast?horizon=3", false)).toBe("/api/forecast?horizon=3");
  });
  it("maps plain endpoints", () => {
    expect(resolveApiPath("/api/series", true)).toBe("api/series.json");
    expect(resolveApiPath("/api/overview", true)).toBe("api/overview.json");
  });
  it("maps forecast queries (champion by default)", () => {
    expect(resolveApiPath("/api/forecast?horizon=6", true)).toBe("api/forecast/6/champion/calibrated.json");
    expect(resolveApiPath("/api/forecast?horizon=3&interval=model&model=sarima", true)).toBe("api/forecast/3/sarima/model.json");
  });
  it("maps backtest queries", () => {
    expect(resolveApiPath("/api/backtest?model=ets&horizon=1", true)).toBe("api/backtest/ets/1.json");
  });
});
