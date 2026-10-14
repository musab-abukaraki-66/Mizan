import { monthIndex } from "./format";

/** Choose month ticks (as month indices) so that at most `maxTicks` fit. Aligned to calendar boundaries. */
export function monthTicks(minT: number, maxT: number, maxTicks: number): { ticks: number[]; step: number } {
  const steps = [1, 2, 3, 6, 12, 24, 36, 60];
  const span = maxT - minT;
  let step = steps[steps.length - 1] as number;
  for (const s of steps) {
    if (span / s + 1 <= maxTicks) {
      step = s;
      break;
    }
  }
  const ticks: number[] = [];
  let t = Math.ceil(minT / step) * step; // multiples of `step` start in January of year 0 -> calendar aligned
  for (; t <= maxT; t += step) ticks.push(t);
  return { ticks, step };
}

export interface Pt {
  t: number;
  v: number;
}

export function toPoints(periods: string[], values: (number | null)[]): Pt[] {
  const out: Pt[] = [];
  periods.forEach((p, i) => {
    const v = values[i];
    if (v !== null && v !== undefined && Number.isFinite(v)) out.push({ t: monthIndex(p), v });
  });
  return out;
}

export function extent(values: number[], pad = 0.06): [number, number] {
  if (!values.length) return [0, 1];
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (lo === hi) {
    lo -= 1;
    hi += 1;
  }
  const p = (hi - lo) * pad;
  return [lo - p, hi + p];
}
