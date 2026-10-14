import { BacktestChart, HistoryForecastChart } from "../components/charts";
import { Badge, Callout, ErrorBox, Loading, Num, PageHead, SelectField, Segmented } from "../components/ui";
import { useApp } from "../context";
import { useApi } from "../lib/api";
import { monthLabel, num, pct, spct } from "../lib/format";
import { HORIZONS, MODEL_IDS, type Arena, type BacktestPayload, type ForecastPayload, type Horizon, type Metrics, type ModelId, type SeriesPayload, type WindowId } from "../lib/types";

function vsNaive(model: Metrics | undefined, naive: Metrics | undefined): number | null {
  if (!model?.rmse || !naive?.rmse) return null;
  return 100 * (model.rmse / naive.rmse - 1);
}

export function Studio() {
  const { t, lang, studio, setStudio, presenting } = useApp();
  const h = studio.horizon;
  const series = useApi<SeriesPayload>("/api/series");
  const arena = useApi<Arena>("/api/arena");
  const fcPath = `/api/forecast?horizon=${h}&interval=${studio.interval}${studio.model ? `&model=${studio.model}` : ""}`;
  const fc = useApi<ForecastPayload>(fcPath);
  const champion = arena.data?.champions[String(h)]?.model ?? fc.data?.champion.model ?? null;
  const model: ModelId | null = studio.model ?? champion;
  const bt = useApi<BacktestPayload>(model ? `/api/backtest?model=${model}&horizon=${h}` : null);

  const chartHeight = presenting ? 460 : window.innerWidth < 760 ? 300 : 380;
  const f = fc.data;

  const windows: WindowId[] = ["dev", "test", "all"];
  return (
    <div className="page">
      <PageHead eyebrow={t("st.eyebrow")} title={t("st.title")} lead={t("st.lead")} />

      <section className="panel" aria-labelledby="st-chart-title">
        <div className="panel__head">
          <h2 className="panel__title" id="st-chart-title">
            {t("st.chartTitle")}
          </h2>
        </div>
        <div className="controls">
          <Segmented
            label={t("common.horizon")}
            value={h}
            onChange={(horizon: Horizon) => setStudio({ horizon, model: null })}
            options={HORIZONS.map((x) => ({ value: x, label: t(`horizon.${x}` as const) }))}
          />
          <SelectField
            label={t("common.model")}
            value={(model ?? "naive") as ModelId}
            onChange={(m) => setStudio({ model: m === champion ? null : m })}
            options={MODEL_IDS.map((m) => ({
              value: m,
              label: `${t(`model.${m}` as const)}${m === champion ? ` – ${t("ar.selected")}` : ""}`,
            }))}
          />
          <Segmented
            label={t("common.measure")}
            value={studio.measure}
            onChange={(measure) => setStudio({ measure })}
            options={[
              { value: "index", label: t("common.index") },
              { value: "yoy", label: t("common.yoy") },
            ]}
          />
          <Segmented
            label={t("common.interval")}
            value={studio.interval}
            onChange={(interval) => setStudio({ interval })}
            options={[
              { value: "calibrated", label: t("st.interval.calibrated") },
              { value: "model", label: t("st.interval.model") },
            ]}
          />
        </div>
        <p className="small muted">{studio.interval === "calibrated" ? t("st.interval.calibratedHelp") : t("st.interval.modelHelp")}</p>
        {fc.error && <ErrorBox error={fc.error} onRetry={fc.reload} />}
        {series.data && f ? (
          <HistoryForecastChart
            rows={series.data.rows}
            forecast={f}
            measure={studio.measure}
            years={0}
            historyMonths={30}
            height={chartHeight}
            modelLabel={t(`model.short.${f.model}` as const)}
          />
        ) : (
          !fc.error && <Loading height={chartHeight} />
        )}
      </section>

      {f && (
        <div className="split">
          <section className="panel" aria-labelledby="st-table-title">
            <h2 className="panel__title" id="st-table-title">
              {t("st.table")}
            </h2>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">{t("common.month")}</th>
                    <th scope="col" className="is-num">{t("st.col.point")}</th>
                    <th scope="col" className="is-num">{t("st.col.i80")}</th>
                    <th scope="col" className="is-num">{t("st.col.i95")}</th>
                    <th scope="col" className="is-num">{t("st.col.yoy")}</th>
                  </tr>
                </thead>
                <tbody>
                  {f.periods.map((per, i) => (
                    <tr key={per}>
                      <th scope="row">{monthLabel(per, lang)}</th>
                      <td className="is-num"><Num>{num(f.mean[i], lang, 2)}</Num></td>
                      <td className="is-num"><Num>{num(f.bands["80"]?.lower[i], lang, 2)} – {num(f.bands["80"]?.upper[i], lang, 2)}</Num></td>
                      <td className="is-num"><Num>{num(f.bands["95"]?.lower[i], lang, 2)} – {num(f.bands["95"]?.upper[i], lang, 2)}</Num></td>
                      <td className="is-num"><Num>{pct(f.yoy[i], lang, 2)}</Num></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel dev-only-keep" aria-labelledby="st-model-title">
            <h2 className="panel__title" id="st-model-title">
              {t("st.modelPanel")}
            </h2>
            <div className="stack">
              <div>
                <strong>{t(`model.${f.model}` as const)}</strong>
              </div>
              <Badge tone={f.model === "naive" || f.model === "seasonal_naive" || f.model === "drift" ? "muted" : undefined}>
                {f.model === "naive" || f.model === "seasonal_naive" || f.model === "drift" ? t("model.baselineTag") : t("model.statTag")}
              </Badge>
              <p className="small">{t(`model.desc.${f.model}` as const)}</p>
              <dl className="kv">
                <dt>{t("st.spec")}</dt>
                <dd><Num>{f.spec}</Num></dd>
              </dl>
              {f.is_champion ? (
                <Badge tone="ok">{t("st.selected")}</Badge>
              ) : (
                <Badge tone="warn">{t("st.notSelected", { model: t(`model.short.${f.champion.model}` as const) })}</Badge>
              )}
            </div>
          </section>
        </div>
      )}

      {f && (
        <section className="panel" aria-labelledby="st-eval-title">
          <div className="panel__head">
            <div>
              <h2 className="panel__title" id="st-eval-title">
                {t("st.evalTitle")}
              </h2>
              <p className="panel__sub">{t("st.evalSub", { h: t(`horizon.${h}` as const) })}</p>
            </div>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">{t("common.window")}</th>
                  <th scope="col" className="is-num">{t("common.n")}</th>
                  <th scope="col" className="is-num">{t("ar.col.mae")}</th>
                  <th scope="col" className="is-num">{t("ar.col.rmse")}</th>
                  <th scope="col" className="is-num">{t("ar.col.mase")}</th>
                  <th scope="col" className="is-num">{t("ar.col.yoy")}</th>
                  <th scope="col" className="is-num">{t("st.eval.vsNaive")}</th>
                </tr>
              </thead>
              <tbody>
                {windows.map((w) => {
                  const m = f.evaluation[w];
                  const d = vsNaive(m, f.baseline_evaluation[w]);
                  return (
                    <tr key={w}>
                      <th scope="row">{t(`st.eval.${w}` as const)}</th>
                      <td className="is-num"><Num>{num(m.n, lang, 0)}</Num></td>
                      <td className="is-num"><Num>{num(m.mae, lang, 3)}</Num></td>
                      <td className="is-num"><Num>{num(m.rmse, lang, 3)}</Num></td>
                      <td className="is-num"><Num>{num(m.mase, lang, 2)}</Num></td>
                      <td className="is-num"><Num>{num(m.yoy_mae_pp, lang, 2)}</Num></td>
                      <td className="is-num"><Num>{d === null ? "–" : spct(d, lang, 1)}</Num></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div>
            <h3 className="panel__title" style={{ fontSize: "1rem" }}>{t("st.btTitle")}</h3>
            <p className="panel__sub">{t("st.btSub", { h: t(`horizon.${h}` as const) })}</p>
          </div>
          {bt.data ? <BacktestChart data={bt.data} interval={studio.interval} height={presenting ? 340 : 300} model={bt.data.model} /> : bt.error ? <ErrorBox error={bt.error} onRetry={bt.reload} /> : <Loading height={300} />}
        </section>
      )}

      <Callout tone="warn">{t("st.caveat")}</Callout>
    </div>
  );
}
