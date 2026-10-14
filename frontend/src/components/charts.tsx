import { useMemo } from "react";
import { TimeSeriesChart, type BandSeries, type LineSeries } from "./Chart";
import { monthIndex, monthLabel, num, periodOf, spct } from "../lib/format";
import { toPoints } from "../lib/chart";
import { useApp, type Measure } from "../context";
import type { BacktestPayload, ForecastPayload, ModelId, SeriesRow } from "../lib/types";

export function useChartFormats(measure: Measure) {
  const { lang, t } = useApp();
  return useMemo(
    () => ({
      yFormat: (v: number) => (measure === "index" ? num(v, lang, 0) : spct(v, lang, 1)),
      tipFormat: (v: number) => (measure === "index" ? num(v, lang, 2) : spct(v, lang, 2)),
      tFormat: (tt: number, withMonth: boolean) => monthLabel(periodOf(tt), lang, withMonth ? "short" : "year"),
      tipTitle: (tt: number) => monthLabel(periodOf(tt), lang, "long"),
      rangeLabel: (lo: string, hi: string) => t("chart.range", { lo, hi }),
    }),
    [measure, lang, t],
  );
}

export interface HistoryForecastProps {
  rows: SeriesRow[];
  forecast: ForecastPayload | null;
  measure: Measure;
  /** 0 = all history */
  years: number;
  height: number;
  modelLabel: string;
  showBand95?: boolean;
  /** limit history window to the last N months (Studio) */
  historyMonths?: number;
}

export function HistoryForecastChart(p: HistoryForecastProps) {
  const { rtl, t } = useApp();
  const fmt = useChartFormats(p.measure);
  const { lines, bands, xDomain, marker } = useMemo(() => {
    const key = p.measure === "index" ? "cpi" : "yoy";
    const obsAll = toPoints(
      p.rows.map((r) => r.period),
      p.rows.map((r) => r[key]),
    );
    const lastObs = obsAll[obsAll.length - 1];
    const lastT = lastObs?.t ?? 0;
    const span = p.historyMonths ?? (p.years === 0 ? Infinity : p.years * 12);
    const firstT = Math.max(obsAll[0]?.t ?? 0, lastT - span);
    const obs = obsAll.filter((pt) => pt.t >= firstT);
    const ls: LineSeries[] = [{ id: "obs", label: t("common.observed"), points: obs, color: "var(--observed)", width: 2.2 }];
    const bs: BandSeries[] = [];
    let hi = lastT;
    if (p.forecast && lastObs) {
      const f = p.forecast;
      const fv = p.measure === "index" ? f.mean : f.yoy;
      const fpts = [{ t: lastT, v: lastObs.v }, ...toPoints(f.periods, fv)];
      hi = fpts[fpts.length - 1]?.t ?? lastT;
      ls.push({
        id: "fc",
        label: t("ov.fcLegend", { model: p.modelLabel }),
        points: fpts,
        color: "var(--forecast)",
        dashed: true,
        width: 2.4,
        dots: true,
        anchorT: lastT,
      });
      const src = p.measure === "index" ? f.bands : f.yoy_bands;
      const mk = (tag: string, opacity: number, label: string) => {
        const b = src[tag];
        if (!b) return;
        const pts = [
          { t: lastT, lo: lastObs.v, hi: lastObs.v },
          ...f.periods.map((per, i) => ({ t: monthIndex(per), lo: b.lower[i] as number, hi: b.upper[i] as number })),
        ];
        bs.push({ id: `b${tag}`, label, points: pts, color: "var(--forecast)", opacity, anchorT: lastT });
      };
      if (p.showBand95 !== false) mk("95", 0.16, t("ov.band95"));
      mk("80", 0.3, t("ov.band80"));
    }
    return {
      lines: ls,
      bands: bs,
      xDomain: [firstT, hi] as [number, number],
      marker: lastObs ? { t: lastT, label: t("ov.lastObs") } : undefined,
    };
  }, [p.rows, p.forecast, p.measure, p.years, p.modelLabel, p.showBand95, p.historyMonths, t]);

  return (
    <TimeSeriesChart
      rtl={rtl}
      height={p.height}
      lines={lines}
      bands={bands}
      xDomain={xDomain}
      marker={marker}
      yBaseline={p.measure === "yoy" ? 0 : undefined}
      ariaLabel={p.measure === "index" ? t("ov.chartAria") : t("ov.chartAriaYoy")}
      hint={t("ov.chartHint")}
      {...fmt}
    />
  );
}

export function BacktestChart(p: { data: BacktestPayload; interval: "calibrated" | "model"; height: number; model: ModelId }) {
  const { rtl, t, lang } = useApp();
  const fmt = useChartFormats("index");
  const { lines, bands, shade, xDomain } = useMemo(() => {
    const s = p.data.series;
    const idx = s.window.map((w, i) => (w === "test" ? i : -1)).filter((i) => i >= 0);
    const pick = <T,>(arr: T[]) => idx.map((i) => arr[i] as T);
    const targets = pick(s.target);
    const actual = toPoints(targets, pick(s.actual));
    const fc = toPoints(targets, pick(s.forecast));
    const calibrated = p.interval === "calibrated" && pick(s.lo80c).every((v) => v !== null);
    const lo = toPoints(targets, pick(calibrated ? s.lo80c : s.lo80));
    const hi = toPoints(targets, pick(calibrated ? s.hi80c : s.hi80));
    const band: BandSeries = {
      id: "b80",
      label: t("ov.band80"),
      color: "var(--forecast)",
      opacity: 0.22,
      points: lo.map((pt, i) => ({ t: pt.t, lo: pt.v, hi: (hi[i] as { v: number }).v })),
    };
    const t0 = actual[0]?.t ?? 0;
    const t1 = actual[actual.length - 1]?.t ?? 1;
    return {
      lines: [
        { id: "act", label: t("st.actual"), points: actual, color: "var(--observed)", width: 2.4 },
        { id: "fc", label: t("st.fcMade", { h: t(`horizon.${p.data.horizon}` as const) }), points: fc, color: "var(--forecast)", dashed: true, width: 2.2 },
      ] as LineSeries[],
      bands: [band],
      shade: undefined,
      xDomain: [t0, t1] as [number, number],
    };
  }, [p.data, p.interval, t]);
  void lang;
  return (
    <TimeSeriesChart
      rtl={rtl}
      height={p.height}
      lines={lines}
      bands={bands}
      shade={shade}
      xDomain={xDomain}
      ariaLabel={`${t("st.btTitle")} – ${t(`model.short.${p.model}` as const)}`}
      hint={t("ov.chartHint")}
      {...fmt}
    />
  );
}
