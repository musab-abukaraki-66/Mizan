import type { Lang } from "./types";

export const MINUS = "−";
export const localeOf = (lang: Lang): string => (lang === "ar" ? "ar-JO-u-nu-latn" : "en-US");

export function num(v: number | null | undefined, lang: Lang, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const s = new Intl.NumberFormat(localeOf(lang), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    useGrouping: false,
  }).format(Math.abs(v));
  return v < 0 && Number(s) !== 0 ? MINUS + s : s;
}

export function signed(v: number | null | undefined, lang: Lang, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const s = num(v, lang, digits);
  return v > 0 && Number(s) !== 0 ? "+" + s : s;
}

export const pct = (v: number | null | undefined, lang: Lang, digits = 2): string =>
  v === null || v === undefined ? "–" : num(v, lang, digits) + "%";
export const spct = (v: number | null | undefined, lang: Lang, digits = 2): string =>
  v === null || v === undefined ? "–" : signed(v, lang, digits) + "%";
export const ratioPct = (v: number | null | undefined, lang: Lang, digits = 0): string =>
  v === null || v === undefined ? "–" : num(100 * v, lang, digits) + "%";

/** Month index (months since year 0) from "YYYY-MM". */
export function monthIndex(period: string): number {
  const [y, m] = period.split("-");
  return Number(y) * 12 + Number(m) - 1;
}
export function periodOf(t: number): string {
  const y = Math.floor(t / 12);
  return `${y}-${String(t - y * 12 + 1).padStart(2, "0")}`;
}
export function addMonths(period: string, k: number): string {
  return periodOf(monthIndex(period) + k);
}

export function monthLabel(period: string, lang: Lang, style: "long" | "short" | "year" = "long"): string {
  const [y, m] = period.split("-").map(Number) as [number, number];
  if (style === "year") return String(y);
  const d = new Date(Date.UTC(y, m - 1, 1));
  return new Intl.DateTimeFormat(localeOf(lang), {
    month: style === "long" ? "long" : "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

export function dateTimeLabel(iso: string, lang: Lang): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(localeOf(lang), {
    dateStyle: "long",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(d) + " UTC";
}

export function pValue(p: number | null | undefined, lang: Lang): string {
  if (p === null || p === undefined) return "–";
  if (p < 0.001) return "<0.001";
  return num(p, lang, 3);
}

export function bytesLabel(n: number, lang: Lang): string {
  return num(n / 1024, lang, 1) + " KB";
}
