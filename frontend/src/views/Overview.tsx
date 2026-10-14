import { useMemo } from "react";
import { HistoryForecastChart } from "../components/charts";
import { Badge, Callout, ErrorBox, Loading, Num, PageHead, Segmented } from "../components/ui";
import { useApp } from "../context";
import { useApi } from "../lib/api";
import { monthLabel, num, pct, spct } from "../lib/format";
import { HORIZONS, MODEL_IDS, type Arena, type ForecastPayload, type Horizon, type ModelId, type Overview as OverviewData, type SeriesPayload } from "../lib/types";

/** The model with the lowest RMSE on the untouched test window (reported, never used for selection). */
export function testLeader(arena: Arena, h: Horizon): ModelId | null {
  let best: ModelId | null = null;
  let bestV = Infinity;
  for (const m of MODEL_IDS) {
    const v = arena.accuracy[m]?.[String(h)]?.test?.rmse;
    if (v !== undefined && v < bestV) {
      bestV = v;
      best = m;
    }
  }
  return best;
}

/** True when some statistical model is significantly better than naive (DM, 5%) on the development window. */
export function anySignificantWin(arena: Arena): boolean {
  return HORIZONS.some((h) =>
    MODEL_IDS.some((m) => {
      if (m === "naive") return false;
      const dm = arena.accuracy[m]?.[String(h)]?.dev?.dm_vs_naive;
      return !!dm && dm.p_value < 0.05 && dm.stat < 0;
    }),
  );
}

export function Overview() {
  const { t, lang, overview, setOverview, presenting, navigate } = useApp();
  const series = useApi<SeriesPayload>("/api/series");
  const ov = useApi<OverviewData>("/api/overview");
  const arena = useApi<Arena>("/api/arena");
  const fc = useApi<ForecastPayload>("/api/forecast?horizon=6");

  const latest = series.data?.latest;
  const chartHeight = presenting ? Math.min(560, Math.max(420, Math.round(window.innerHeight * 0.52))) : window.innerWidth < 760 ? 300 : 380;

  const modelName = (id: ModelId) => t(`model.${id}` as const);
  const msg = useMemo(() => (arena.data ? (anySignificantWin(arena.data) ? "ov.msgSig" : "ov.msgNoSig") : null), [arena.data]);

  return (
    <div className="page">
      <PageHead eyebrow={t("ov.eyebrow")} title={t("ov.title")} lead={t("ov.lead")} />

      <section id="headline" aria-label={t("ov.eyebrow")}>
        {series.error && <ErrorBox error={series.error} onRetry={series.reload} />}
        {!latest && !series.error && <Loading height={150} />}
        {latest && (
          <div className="headline">
            <div className="stat">
              <span className="stat__label">{t("ov.cpi")}</span>
              <span className="stat__value">
                <Num>{num(latest.cpi, lang, 2)}</Num>
              </span>
              <span className="stat__sub">{t("ov.cpiSub", { month: monthLabel(latest.period, lang) })}</span>
            </div>
            <div className="stat">
              <span className="stat__label">{t("ov.yoy")}</span>
              <span className="stat__value">
                <Num>
                  {num(latest.yoy, lang, 2)}
                  <small>%</small>
                </Num>
              </span>
              <span className="stat__sub">
                {latest.avg_to_date !== null
                  ? t("ov.yoySub", { prev: num(latest.yoy_prev, lang, 2), avg: num(latest.avg_to_date, lang, 2) })
                  : t("ov.yoySub2", { prev: num(latest.yoy_prev, lang, 2) })}
              </span>
            </div>
            <div className="stat">
              <span className="stat__label">{t("ov.mom")}</span>
              <span className="stat__value">
                <Num>
                  {spct(latest.mom, lang, 2).replace("%", "")}
                  <small>%</small>
                </Num>
              </span>
              <span className="stat__sub">{t("ov.momSub", { month: monthLabel(latest.prev_period, lang) })}</span>
            </div>
          </div>
        )}
      </section>

      <section className="panel" id="main-chart" aria-labelledby="main-chart-title">
        <div className="panel__head">
          <div>
            <h2 className="panel__title" id="main-chart-title">
              {t("ov.chartTitle")}
            </h2>
            <p className="panel__sub">{t("ov.chartSub")}</p>
          </div>
          <div className="controls">
            <Segmented
              label={t("common.measure")}
              value={overview.measure}
              onChange={(measure) => setOverview({ measure })}
              options={[
                { value: "index", label: t("common.index") },
                { value: "yoy", label: t("common.yoy") },
              ]}
            />
            <Segmented
              label={t("ov.range")}
              value={overview.years}
              onChange={(years) => setOverview({ years })}
              options={[
                { value: 3, label: t("ov.range.3") },
                { value: 5, label: t("ov.range.5") },
                { value: 10, label: t("ov.range.10") },
                { value: 0, label: t("ov.range.all") },
              ]}
            />
          </div>
        </div>
        {series.data ? (
          <HistoryForecastChart
            rows={series.data.rows}
            forecast={fc.data}
            measure={overview.measure}
            years={overview.years}
            height={chartHeight}
            modelLabel={fc.data ? t(`model.short.${fc.data.model}` as const) : ""}
          />
        ) : (
          <Loading height={chartHeight} />
        )}
      </section>

      <section id="forecast-cards" aria-labelledby="fc-title" className="stack">
        <div>
          <h2 className="section-title" id="fc-title">
            {t("ov.fcTitle")}
          </h2>
          <p className="panel__sub">{t("ov.fcSub")}</p>
        </div>
        {ov.error && <ErrorBox error={ov.error} onRetry={ov.reload} />}
        {!ov.data && !ov.error && <Loading height={200} />}
        {ov.data && (
          <div className="fcards">
            {HORIZONS.map((h) => {
              const f = ov.data!.forecast_summary[String(h)];
              if (!f) return null;
              const leader = arena.data ? testLeader(arena.data, h) : null;
              return (
                <article className="fcard" key={h} aria-label={t(`horizon.ahead.${h}` as const)}>
                  <span className="fcard__h">{t(`horizon.ahead.${h}` as const)}</span>
                  <span className="fcard__period">{monthLabel(f.period, lang)}</span>
                  <span className="fcard__value">
                    <Num>{num(f.point, lang, 2)}</Num>
                  </span>
                  <div className="fcard__row">
                    <span>{t("ov.fcYoy")}</span>
                    <b>
                      <Num>{pct(f.yoy, lang, 2)}</Num>
                    </b>
                  </div>
                  <div className="fcard__row">
                    <span>{t("ov.fcRange")}</span>
                    <b>
                      <Num>
                        {num(f.lower, lang, 1)} – {num(f.upper, lang, 1)}
                      </Num>
                    </b>
                  </div>
                  <div className="fcard__row">
                    <span>{t("ov.fcModel")}</span>
                    <b>{t(`model.short.${f.model}` as const)}</b>
                  </div>
                  <div className="fcard__foot">
                    <Badge tone={f.champion.statistical_model_wins_dev ? "ok" : "muted"}>
                      {f.champion.statistical_model_wins_dev ? t("ov.ev.statWins") : t("ov.ev.baselineWins")}
                    </Badge>
                    {leader && (
                      <span className="small muted">
                        {leader === f.model ? t("ov.ev.testSame") : t("ov.ev.testLeader", { model: modelName(leader) })}
                      </span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="panel" id="evidence" aria-labelledby="ev-title">
        <div className="panel__head">
          <div>
            <h2 className="panel__title" id="ev-title">
              {t("ov.evTitle")}
            </h2>
            <p className="panel__sub">{t("ov.evSub")}</p>
          </div>
          <button type="button" className="btn" onClick={() => navigate("arena")}>
            {t("common.openArena")}
          </button>
        </div>
        {ov.data && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">{t("ov.evCols.h")}</th>
                  <th scope="col">{t("ov.evCols.model")}</th>
                  <th scope="col" className="is-num">{t("ov.evCols.dev")}</th>
                  <th scope="col" className="is-num">{t("ov.evCols.devNaive")}</th>
                  <th scope="col" className="is-num">{t("ov.evCols.test")}</th>
                  <th scope="col" className="is-num">{t("ov.evCols.testNaive")}</th>
                </tr>
              </thead>
              <tbody>
                {HORIZONS.map((h) => {
                  const c = ov.data!.forecast_summary[String(h)]?.champion;
                  if (!c) return null;
                  return (
                    <tr key={h}>
                      <th scope="row">{t(`horizon.${h}` as const)}</th>
                      <td>{modelName(c.model)}</td>
                      <td className="is-num"><Num>{num(c.dev_rmse, lang, 3)}</Num></td>
                      <td className="is-num"><Num>{num(c.naive_dev_rmse, lang, 3)}</Num></td>
                      <td className="is-num"><Num>{num(c.test_rmse, lang, 3)}</Num></td>
                      <td className="is-num"><Num>{num(c.naive_test_rmse, lang, 3)}</Num></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {msg && <Callout tone="info">{t(msg)}</Callout>}
      </section>

      <Callout tone="warn" title={t("ov.caveatTitle")} id="caveats">
        {t("ov.caveat")}
      </Callout>
    </div>
  );
}
