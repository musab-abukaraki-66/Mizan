import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { scaleLinear } from "d3-scale";
import { area as d3area, line as d3line } from "d3-shape";
import { extent, monthTicks, type Pt } from "../lib/chart";

export interface LineSeries {
  id: string;
  label: string;
  points: Pt[];
  color: string; // CSS color / var()
  dashed?: boolean;
  width?: number;
  dots?: boolean;
  /** hide from legend (still drawn) */
  hideLegend?: boolean;
  /** month index of a connector point that is drawn but not reported in tooltips / dots */
  anchorT?: number;
}
export interface BandPoint {
  t: number;
  lo: number;
  hi: number;
}
export interface BandSeries {
  id: string;
  label: string;
  points: BandPoint[];
  color: string;
  opacity: number;
  anchorT?: number;
}
export interface ChartProps {
  rtl: boolean;
  height: number;
  lines: LineSeries[];
  bands?: BandSeries[];
  yFormat: (v: number) => string;
  /** precise value format used in tooltips / aria text (defaults to yFormat) */
  tipFormat?: (v: number) => string;
  /** axis tick label; `withMonth` is true when ticks are finer than a year */
  tFormat: (t: number, withMonth: boolean) => string;
  /** tooltip title (defaults to tFormat(t, true)) */
  tipTitle?: (t: number) => string;
  ariaLabel: string;
  marker?: { t: number; label: string };
  shade?: { from: number; to: number; label: string };
  xDomain?: [number, number];
  yDomain?: [number, number];
  yBaseline?: number; // draws an emphasised horizontal rule (e.g. 0 %)
  /** localised "{lo} to {hi}" for band rows in the tooltip */
  rangeLabel: (lo: string, hi: string) => string;
  hint?: string;
}

const MARGIN = { top: 14, bottom: 30, inline: 12, axis: 48 };

function useWidth(ref: React.RefObject<HTMLDivElement | null>): number {
  const [w, setW] = useState(640);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => setW(Math.max(260, Math.floor(el.getBoundingClientRect().width)));
    update();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

export function TimeSeriesChart(p: ChartProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const width = useWidth(wrapRef);
  const uid = useId();
  const [hover, setHover] = useState<number | null>(null);
  const [focused, setFocused] = useState(false);
  const bands = useMemo(() => p.bands ?? [], [p.bands]);
  const innerH = p.height - MARGIN.top - MARGIN.bottom;
  const left = p.rtl ? MARGIN.inline : MARGIN.axis;
  const right = p.rtl ? MARGIN.axis : MARGIN.inline;
  const innerW = Math.max(120, width - left - right);

  const allT = useMemo(() => {
    const ts = new Set<number>();
    p.lines.forEach((l) => l.points.forEach((pt) => ts.add(pt.t)));
    return [...ts].sort((a, b) => a - b);
  }, [p.lines]);

  const [t0, t1] = useMemo<[number, number]>(() => p.xDomain ?? [allT[0] ?? 0, allT[allT.length - 1] ?? 1], [p.xDomain, allT]);

  const [y0, y1] = useMemo<[number, number]>(() => {
    if (p.yDomain) return p.yDomain;
    const vals: number[] = [];
    p.lines.forEach((l) => l.points.forEach((pt) => pt.t >= t0 && pt.t <= t1 && vals.push(pt.v)));
    bands.forEach((b) => b.points.forEach((pt) => pt.t >= t0 && pt.t <= t1 && vals.push(pt.lo, pt.hi)));
    if (p.yBaseline !== undefined) vals.push(p.yBaseline);
    return extent(vals, 0.08);
  }, [p.yDomain, p.lines, bands, t0, t1, p.yBaseline]);

  const xs = useMemo(() => scaleLinear().domain([t0, t1]).range(p.rtl ? [left + innerW, left] : [left, left + innerW]), [t0, t1, p.rtl, left, innerW]);
  const ys = useMemo(() => scaleLinear().domain([y0, y1]).range([MARGIN.top + innerH, MARGIN.top]).nice(5), [y0, y1, innerH]);
  const yTicks = ys.ticks(5);
  const { ticks: xTicks, step } = useMemo(() => monthTicks(t0, t1, Math.max(2, Math.floor(innerW / 92))), [t0, t1, innerW]);

  const lineGen = useMemo(
    () => d3line<Pt>().x((d) => xs(d.t)).y((d) => ys(d.v)).defined((d) => d.t >= t0 && d.t <= t1),
    [xs, ys, t0, t1],
  );
  const areaGen = useMemo(
    () => d3area<BandPoint>().x((d) => xs(d.t)).y0((d) => ys(d.lo)).y1((d) => ys(d.hi)).defined((d) => d.t >= t0 && d.t <= t1),
    [xs, ys, t0, t1],
  );

  const tFromX = useCallback(
    (clientX: number): number => {
      const rect = wrapRef.current?.getBoundingClientRect();
      if (!rect) return t0;
      const x = clientX - rect.left;
      const t = Math.round(xs.invert(x));
      let best = allT[0] ?? t0;
      for (const c of allT) if (Math.abs(c - t) < Math.abs(best - t)) best = c;
      return Math.max(t0, Math.min(t1, best));
    },
    [xs, allT, t0, t1],
  );

  const onKey = (e: React.KeyboardEvent) => {
    const dirSign = p.rtl ? -1 : 1;
    const idx = hover === null ? -1 : allT.indexOf(hover);
    let next: number | null = null;
    if (e.key === "ArrowRight") next = idx + dirSign;
    else if (e.key === "ArrowLeft") next = idx - dirSign;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = allT.length - 1;
    else if (e.key === "Escape") {
      setHover(null);
      return;
    } else return;
    e.preventDefault();
    if (hover === null && (e.key === "ArrowRight" || e.key === "ArrowLeft")) next = allT.length - 1;
    const clamped = Math.max(0, Math.min(allT.length - 1, next));
    setHover(allT[clamped] ?? null);
  };

  const fmtTip = p.tipFormat ?? p.yFormat;
  const tip = useMemo(() => {
    if (hover === null) return null;
    const rows: { label: string; value: string; color: string; dashed?: boolean }[] = [];
    p.lines.forEach((l) => {
      const pt = l.points.find((q) => q.t === hover);
      if (pt && pt.t !== l.anchorT) rows.push({ label: l.label, value: fmtTip(pt.v), color: l.color, dashed: l.dashed });
    });
    bands.forEach((b) => {
      const pt = b.points.find((q) => q.t === hover);
      if (pt && pt.t !== b.anchorT) rows.push({ label: b.label, value: p.rangeLabel(fmtTip(pt.lo), fmtTip(pt.hi)), color: b.color });
    });
    return { rows, title: p.tipTitle ? p.tipTitle(hover) : p.tFormat(hover, true) };
  }, [hover, p, bands, fmtTip]);

  const hx = hover === null ? null : xs(hover);
  // keep the tooltip on the side of the plot away from the cursor
  const tipOnStart = hx !== null && (p.rtl ? hx > left + innerW / 2 : hx < left + innerW / 2);

  const clipId = `clip-${uid}`;
  const legendItems = [
    ...p.lines.filter((l) => !l.hideLegend).map((l) => ({ id: l.id, label: l.label, color: l.color, kind: l.dashed ? "dash" : "line" })),
    ...bands.map((b) => ({ id: b.id, label: b.label, color: b.color, kind: "band" })),
  ];

  const summaryText = (() => {
    const first = p.lines[0];
    if (!first || !first.points.length) return p.ariaLabel;
    const a = first.points[0] as Pt;
    const b = first.points[first.points.length - 1] as Pt;
    return `${p.ariaLabel}. ${p.tFormat(a.t, true)}: ${p.yFormat(a.v)} → ${p.tFormat(b.t, true)}: ${p.yFormat(b.v)}`;
  })();

  return (
    <figure className="chart" data-testid="chart">
      <div
        ref={wrapRef}
        className="chart__frame"
        role="group"
        aria-label={summaryText}
        aria-describedby={`${uid}-hint`}
        tabIndex={0}
        onKeyDown={onKey}
        onFocus={() => setFocused(true)}
        onBlur={() => {
          setFocused(false);
          setHover(null);
        }}
        onPointerMove={(e) => setHover(tFromX(e.clientX))}
        onPointerLeave={() => !focused && setHover(null)}
      >
        <svg width={width} height={p.height} viewBox={`0 0 ${width} ${p.height}`} role="presentation" aria-hidden="true" className="chart__svg">
          <defs>
            <clipPath id={clipId}>
              <rect x={left} y={MARGIN.top - 4} width={innerW} height={innerH + 8} />
            </clipPath>
          </defs>

          {p.shade && (
            <g>
              <rect
                x={Math.min(xs(p.shade.from), xs(p.shade.to))}
                width={Math.abs(xs(p.shade.to) - xs(p.shade.from))}
                y={MARGIN.top}
                height={innerH}
                className="chart__shade"
              />
              <text x={(xs(p.shade.from) + xs(p.shade.to)) / 2} y={MARGIN.top + 13} textAnchor="middle" className="chart__shade-label">
                {p.shade.label}
              </text>
            </g>
          )}

          {yTicks.map((v) => (
            <g key={v}>
              <line x1={left} x2={left + innerW} y1={ys(v)} y2={ys(v)} className="chart__grid" />
              <text
                x={p.rtl ? left + innerW + 8 : left - 8}
                y={ys(v)}
                dy="0.32em"
                textAnchor={p.rtl ? "start" : "end"}
                className="chart__tick"
              >
                {p.yFormat(v)}
              </text>
            </g>
          ))}
          {p.yBaseline !== undefined && y0 <= p.yBaseline && p.yBaseline <= y1 && (
            <line x1={left} x2={left + innerW} y1={ys(p.yBaseline)} y2={ys(p.yBaseline)} className="chart__baseline" />
          )}
          <line x1={left} x2={left + innerW} y1={MARGIN.top + innerH} y2={MARGIN.top + innerH} className="chart__axis" />
          {xTicks.map((t) => (
            <g key={t}>
              <line x1={xs(t)} x2={xs(t)} y1={MARGIN.top + innerH} y2={MARGIN.top + innerH + 4} className="chart__axis" />
              <text x={xs(t)} y={MARGIN.top + innerH + 19} textAnchor="middle" className="chart__tick">
                {p.tFormat(t, step < 12)}
              </text>
            </g>
          ))}

          <g clipPath={`url(#${clipId})`}>
            <g className={`chart__reveal ${p.rtl ? "is-rtl" : ""}`} key={`${p.lines.length}-${t0}-${t1}-${p.lines[0]?.points.length}`}>
              {bands.map((b) => (
                <path key={b.id} d={areaGen(b.points) ?? ""} style={{ fill: b.color, opacity: b.opacity }} />
              ))}
              {p.lines.map((l) => (
                <g key={l.id}>
                  <path
                    d={lineGen(l.points) ?? ""}
                    fill="none"
                    style={{ stroke: l.color }}
                    strokeWidth={l.width ?? 2}
                    strokeDasharray={l.dashed ? "6 4" : undefined}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                  {l.dots &&
                    l.points
                      .filter((pt) => pt.t >= t0 && pt.t <= t1 && pt.t !== l.anchorT)
                      .map((pt) => <circle key={pt.t} cx={xs(pt.t)} cy={ys(pt.v)} r={3} style={{ fill: "var(--surface)", stroke: l.color }} strokeWidth={1.6} />)}
                </g>
              ))}
            </g>
          </g>

          {p.marker && p.marker.t >= t0 && p.marker.t <= t1 && (
            <g>
              <line x1={xs(p.marker.t)} x2={xs(p.marker.t)} y1={MARGIN.top} y2={MARGIN.top + innerH} className="chart__marker" />
              <text
                x={xs(p.marker.t) + (p.rtl ? 6 : -6)}
                y={MARGIN.top + 12}
                textAnchor={p.rtl ? "start" : "end"}
                className="chart__marker-label"
              >
                {p.marker.label}
              </text>
            </g>
          )}

          {hover !== null && hx !== null && (
            <g>
              <line x1={hx} x2={hx} y1={MARGIN.top} y2={MARGIN.top + innerH} className="chart__cursor" />
              {p.lines.map((l) => {
                const pt = l.points.find((q) => q.t === hover);
                return pt && pt.t !== l.anchorT ? <circle key={l.id} cx={hx} cy={ys(pt.v)} r={4.5} style={{ fill: l.color, stroke: "var(--surface)" }} strokeWidth={2} /> : null;
              })}
            </g>
          )}
        </svg>

        {tip && hx !== null && (
          <div
            className="chart__tip"
            role="status"
            style={{ top: 8, [tipOnStart ? "insetInlineEnd" : "insetInlineStart"]: 8 } as React.CSSProperties}
          >
            <div className="chart__tip-title">{tip.title}</div>
            {tip.rows.map((r) => (
              <div className="chart__tip-row" key={r.label}>
                <span className="chart__tip-key">
                  <i className="chart__tip-swatch" style={{ background: r.color }} />
                  {r.label}
                </span>
                <bdi dir="ltr" className="num">
                  {r.value}
                </bdi>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="chart__legend" aria-hidden="true">
        {legendItems.map((it) => (
          <span key={it.id} className="chart__legend-item">
            <i
              className={`chart__legend-swatch chart__legend-swatch--${it.kind}`}
              style={it.kind === "band" ? { background: it.color } : { borderColor: it.color }}
            />
            {it.label}
          </span>
        ))}
      </div>
      <figcaption id={`${uid}-hint`} className="sr-only">
        {p.hint}
      </figcaption>
    </figure>
  );
}
