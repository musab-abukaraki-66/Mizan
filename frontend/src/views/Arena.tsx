import { BacktestChart } from "../components/charts";
import { Badge, Callout, ErrorBox, Loading, Num, PageHead, SelectField, Segmented } from "../components/ui";
import { useApp } from "../context";
import { useApi } from "../lib/api";
import { monthLabel, num, pValue, ratioPct, spct } from "../lib/format";
import { HORIZONS, MODEL_IDS, type Arena as ArenaData, type BacktestPayload, type Horizon, type ModelId, type WindowId } from "../lib/types";
import { testLeader } from "./Overview";

const BASELINES: ModelId[] = ["naive", "seasonal_naive", "drift"];

export function Arena() {
  const { t, lang, arena: st, setArena, presenting } = useApp();
  const { data, error, reload } = useApi<ArenaData>("/api/arena");
  const bt = useApi<BacktestPayload>(`/api/backtest?model=${st.model}&horizon=${st.horizon}`);
  const h = st.horizon;
  const hk = String(h);
  const w: WindowId = st.window;

  const name = (m: ModelId) => t(`model.${m}` as const);
  const champ = data?.champions[hk];
  const leader = data ? testLeader(data, h) : null;
  const naiveRmse = data?.accuracy.naive?.[hk]?.[w]?.rmse;

  const skill = (m: ModelId): number | null => {
    const v = data?.accuracy[m]?.[hk]?.[w]?.rmse;
    return v !== undefined && naiveRmse ? 100 * (v / naiveRmse - 1) : null;
  };

  return (
    <div className="page">
      <PageHead eyebrow={t("ar.eyebrow")} title={t("ar.title")} lead={t("ar.lead")} />
      {error && <ErrorBox error={error} onRetry={reload} />}
      {!data && !error && <Loading height={300} />}

      {data && (
        <>
          <section className="panel" aria-labelledby="ar-design">
            <h2 className="panel__title" id="ar-design">
              {t("ar.designTitle")}
            </h2>
            <div className="tiles">
              <div className="tile">
                <div className="tile__v"><Num>{num(data.design.origins, lang, 0)}</Num></div>
                <div className="tile__l">{t("ar.design.origins")}</div>
              </div>
              <div className="tile">
                <div className="tile__v" style={{ fontSize: "1.1rem" }}>{monthLabel(data.design.first_origin, lang)}</div>
                <div className="tile__l">{t("ar.design.first")}</div>
              </div>
              <div className="tile">
                <div className="tile__v"><Num>{num(data.config.min_train, lang, 0)}</Num></div>
                <div className="tile__l">{t("ar.design.minTrain")} ({t("ar.design.months", { n: num(data.config.min_train, lang, 0) })})</div>
              </div>
              <div className="tile">
                <div className="tile__v" style={{ fontSize: "1.1rem" }}>
                  {monthLabel(data.design.dev_window[0], lang, "short")} – {monthLabel(data.design.dev_window[1], lang, "short")}
                </div>
                <div className="tile__l">{t("ar.design.dev")}</div>
              </div>
              <div className="tile">
                <div className="tile__v" style={{ fontSize: "1.1rem" }}>
                  {monthLabel(data.design.test_window[0], lang, "short")} – {monthLabel(data.design.test_window[1], lang, "short")}
                </div>
                <div className="tile__l">{t("ar.design.test")}: {t("ar.design.testN", { n: num(data.config.test_months, lang, 0) })}</div>
              </div>
            </div>
            <p className="small muted dev-only">
              {t("ar.sampleRule")}: {t("ar.sampleRuleText", { a: num(data.comparison_sample.rows_after, lang, 0), b: num(data.comparison_sample.rows_before, lang, 0) })}
            </p>
          </section>

          <section className="panel" aria-labelledby="ar-table">
            <div className="panel__head">
              <div>
                <h2 className="panel__title" id="ar-table">
                  {t("ar.tableTitle")}
                </h2>
                <p className="panel__sub">{t("ar.tableSub")}</p>
              </div>
            </div>
            <div className="controls">
              <Segmented
                label={t("common.horizon")}
                value={h}
                onChange={(horizon: Horizon) => setArena({ horizon })}
                options={HORIZONS.map((x) => ({ value: x, label: t(`horizon.${x}` as const) }))}
              />
              <Segmented
                label={t("common.window")}
                value={w}
                onChange={(window) => setArena({ window })}
                options={(["dev", "test", "all"] as WindowId[]).map((x) => ({ value: x, label: t(`ar.win.${x}` as const) }))}
              />
            </div>
            <div className="table-wrap">
              <table className="table" data-testid="arena-table">
                <thead>
                  <tr>
                    <th scope="col">{t("ar.col.model")}</th>
                    <th scope="col" className="is-num">{t("ar.col.n")}</th>
                    <th scope="col" className="is-num">{t("ar.col.mae")}</th>
                    <th scope="col" className="is-num">{t("ar.col.rmse")}</th>
                    <th scope="col" className="is-num">{t("ar.col.mase")}</th>
                    <th scope="col" className="is-num">{t("ar.col.yoy")}</th>
                    <th scope="col" className="is-num">{t("ar.col.vs")}</th>
                    <th scope="col" className="is-num">{t("ar.col.dm")}</th>
                    <th scope="col" className="is-num">{t("ar.col.covCal")}</th>
                    <th scope="col" className="is-num">{t("ar.col.covModel")}</th>
                  </tr>
                </thead>
                <tbody>
                  {MODEL_IDS.map((m) => {
                    const x = data.accuracy[m]?.[hk]?.[w];
                    if (!x) return null;
                    const sk = skill(m);
                    return (
                      <tr key={m} className={champ?.model === m ? "is-champion" : undefined}>
                        <th scope="row">
                          <div>{name(m)}</div>
                          <div className="stack" style={{ flexDirection: "row", gap: 6, marginBlockStart: 4, flexWrap: "wrap" }}>
                            <Badge tone="muted">{BASELINES.includes(m) ? t("model.baselineTag") : t("model.statTag")}</Badge>
                            {champ?.model === m && <Badge tone="ok">{t("ar.selected")}</Badge>}
                            {leader === m && w !== "dev" && <Badge tone="warn">{t("ar.testLeader")}</Badge>}
                          </div>
                        </th>
                        <td className="is-num"><Num>{num(x.n, lang, 0)}</Num></td>
                        <td className="is-num"><Num>{num(x.mae, lang, 3)}</Num></td>
                        <td className="is-num"><Num>{num(x.rmse, lang, 3)}</Num></td>
                        <td className="is-num"><Num>{num(x.mase, lang, 2)}</Num></td>
                        <td className="is-num"><Num>{num(x.yoy_mae_pp, lang, 2)}</Num></td>
                        <td className="is-num"><Num>{m === "naive" ? "–" : sk === null ? "–" : spct(sk, lang, 1)}</Num></td>
                        <td className="is-num"><Num>{m === "naive" ? "–" : pValue(x.dm_vs_naive?.p_value, lang)}</Num></td>
                        <td className="is-num"><Num>{ratioPct(x.cal_coverage80, lang, 0)}</Num></td>
                        <td className="is-num"><Num>{ratioPct(x.coverage80, lang, 0)}</Num></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="small muted">{t("ar.coverageNote")}</p>
            <p className="small muted">{t("ar.seasonalNote")}</p>
          </section>

          <div className="grid-2">
            <section className="panel" aria-labelledby="ar-skill">
              <div>
                <h2 className="panel__title" id="ar-skill">
                  {t("ar.skillTitle")}
                </h2>
                <p className="panel__sub">{t("ar.skillSub")}</p>
              </div>
              <div className="bars" role="list">
                {MODEL_IDS.map((m) => {
                  const v = skill(m);
                  if (v === null) return null;
                  const width = Math.min(Math.abs(v), 100);
                  return (
                    <div className="bar" role="listitem" key={m}>
                      <span>{t(`model.short.${m}` as const)}</span>
                      <span className="bar__track" aria-hidden="true">
                        <span className={`bar__fill ${v < -0.05 ? "is-better" : v > 0.05 ? "is-worse" : ""}`} style={{ width: `${Math.max(width, m === "naive" ? 1.5 : 1.5)}%` }} />
                      </span>
                      <b><Num>{m === "naive" ? "0.0%" : spct(v, lang, 1)}</Num></b>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="panel" aria-labelledby="ar-verdict">
              <h2 className="panel__title" id="ar-verdict">
                {t("ar.verdictTitle")}
              </h2>
              {champ && (
                <div className="stack">
                  <p>
                    {BASELINES.includes(champ.model)
                      ? t("ar.verdictBaseline", { h: t(`horizon.${h}` as const), model: name(champ.model) })
                      : t("ar.verdictStat", {
                          h: t(`horizon.${h}` as const),
                          model: name(champ.model),
                          imp: num(champ.improvement_vs_naive_pct, lang, 1),
                          sig:
                            champ.dm_p_vs_naive === null
                              ? t("ar.sig.na")
                              : t(champ.dm_p_vs_naive < 0.05 ? "ar.sig.yes" : "ar.sig.no", { p: pValue(champ.dm_p_vs_naive, lang) }),
                        })}
                  </p>
                  {leader && champ.test_rmse !== null && (
                    <p>
                      {t("ar.verdictTest", {
                        model: name(leader),
                        rmse: num(data.accuracy[leader]?.[hk]?.test?.rmse, lang, 3),
                        naive: num(data.accuracy.naive?.[hk]?.test?.rmse, lang, 3),
                      })}
                    </p>
                  )}
                  <Callout tone="warn">{t("ar.verdictCaveat", { n: num(data.config.test_months, lang, 0) })}</Callout>
                </div>
              )}
            </section>
          </div>

          <section className="panel" aria-labelledby="ar-bt">
            <div className="panel__head">
              <div>
                <h2 className="panel__title" id="ar-bt">
                  {t("ar.btTitle")}
                </h2>
                <p className="panel__sub">{t("st.btSub", { h: t(`horizon.${h}` as const) })}</p>
              </div>
              <SelectField
                label={t("common.model")}
                value={st.model}
                onChange={(model) => setArena({ model })}
                options={MODEL_IDS.map((m) => ({ value: m, label: name(m) }))}
              />
            </div>
            {bt.data ? <BacktestChart data={bt.data} interval="calibrated" height={presenting ? 380 : 320} model={bt.data.model} /> : bt.error ? <ErrorBox error={bt.error} onRetry={bt.reload} /> : <Loading height={320} />}
          </section>

          <section className="panel dev-only" aria-labelledby="ar-tech">
            <h2 className="panel__title" id="ar-tech">
              {t("ar.techTitle")}
            </h2>
            <dl className="kv">
              <dt>{t("ar.fitFailures")}</dt>
              <dd>
                {MODEL_IDS.map((m) => `${t(`model.short.${m}` as const)}: ${data.fit_failures[m]?.count ?? 0}`).join(" · ")}
              </dd>
              <dt>{t("ar.specs")}</dt>
              <dd>
                {(["ets", "sarima"] as const).map((m) => (
                  <div key={m}>
                    <b>{t(`model.short.${m}` as const)}</b>:{" "}
                    <Num>
                      {Object.entries(data.selected_specs[m] ?? {})
                        .sort((a, b) => b[1] - a[1])
                        .map(([k, v]) => `${k} ${ratioPct(v / data.design.origins, lang, 0)}`)
                        .join(" · ")}
                    </Num>
                  </div>
                ))}
              </dd>
            </dl>
          </section>
        </>
      )}
    </div>
  );
}
