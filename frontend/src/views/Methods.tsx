import { Callout, PageHead } from "../components/ui";
import { useApp } from "../context";
import { useApi } from "../lib/api";
import { monthLabel, num } from "../lib/format";
import { MODEL_IDS, type Arena } from "../lib/types";

export function Methods() {
  const { t, lang } = useApp();
  const { data } = useApi<Arena>("/api/arena");
  const d = data?.design;
  const c = data?.config;
  const L = (p: string) => (p ? monthLabel(p, lang) : "…");
  const nTrain = c?.min_train ?? 96;
  const nDev = d ? d.origins_by_horizon["1"]?.dev ?? 0 : 0;
  const nTest = c?.test_months ?? 24;
  const total = nTrain + nDev + nTest;

  return (
    <div className="page">
      <PageHead eyebrow={t("me.eyebrow")} title={t("me.title")} lead={t("me.lead")} />

      <section className="prose" aria-labelledby="me-1">
        <h2 id="me-1" className="section-title">{t("me.s1")}</h2>
        <p>{t("me.s1p1")}</p>
        <div className="formula">{t("me.f.mom")}</div>
        <div className="formula">{t("me.f.yoy")}</div>
        <div className="formula">{t("me.f.avg")}</div>
      </section>

      <section className="stack" aria-labelledby="me-2">
        <div className="prose">
          <h2 id="me-2" className="section-title">{t("me.s2")}</h2>
          <p>{t("me.s2p")}</p>
        </div>
        <div className="method-grid">
          {MODEL_IDS.map((m) => (
            <article className="method-card" key={m}>
              <h3>{t(`model.${m}` as const)}</h3>
              <p>{t(`model.desc.${m}` as const)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="prose" aria-labelledby="me-3">
        <h2 id="me-3" className="section-title">{t("me.s3")}</h2>
        <p>{t("me.s3p1")}</p>
        <p>
          {t("me.s3p2", {
            minTrain: num(nTrain, lang, 0),
            first: L(d?.first_origin ?? ""),
            devEnd: L(d?.dev_window[1] ?? ""),
            testN: num(nTest, lang, 0),
            testStart: L(d?.test_window[0] ?? ""),
            testEnd: L(d?.test_window[1] ?? ""),
          })}
        </p>
        <div role="img" aria-label={`${t("me.timeline.train")} → ${t("me.timeline.dev")} → ${t("me.timeline.test")}`}>
          <div style={{ display: "flex", height: 18, borderRadius: 9, overflow: "hidden", border: "1px solid var(--line)" }}>
            <div style={{ flex: nTrain / total, background: "#d9d5c8" }} />
            <div style={{ flex: nDev / total, background: "color-mix(in srgb, var(--forecast) 45%, white)" }} />
            <div style={{ flex: nTest / total, background: "var(--accent)" }} />
          </div>
          <div className="chart__legend" style={{ marginBlockStart: 10 }}>
            <span className="chart__legend-item"><i className="chart__legend-swatch chart__legend-swatch--band" style={{ background: "#9c978a", opacity: 0.6 }} />{t("me.timeline.train")}</span>
            <span className="chart__legend-item"><i className="chart__legend-swatch chart__legend-swatch--band" style={{ background: "var(--forecast)", opacity: 0.55 }} />{t("me.timeline.dev")}</span>
            <span className="chart__legend-item"><i className="chart__legend-swatch chart__legend-swatch--band" style={{ background: "var(--accent)", opacity: 1 }} />{t("me.timeline.test")}</span>
          </div>
        </div>
      </section>

      <section className="prose" aria-labelledby="me-4">
        <h2 id="me-4" className="section-title">{t("me.s4")}</h2>
        <ul>
          <li>{t("me.s4l1")}</li>
          <li>{t("me.s4l2", { minTrain: num(nTrain, lang, 0), scale: d ? num(d.mase_scale, lang, 3) : "…" })}</li>
          <li>{t("me.s4l3")}</li>
          <li>{t("me.s4l4")}</li>
          <li>{t("me.s4l5")}</li>
        </ul>
      </section>

      <section className="prose" aria-labelledby="me-5">
        <h2 id="me-5" className="section-title">{t("me.s5")}</h2>
        <p>{t("me.s5p1")}</p>
        <p>{t("me.s5p2")}</p>
      </section>

      <section className="prose" aria-labelledby="me-6">
        <h2 id="me-6" className="section-title">{t("me.s6")}</h2>
        <ul>
          <li>{t("me.s6l1")}</li>
          <li>{t("me.s6l2")}</li>
          <li>{t("me.s6l3")}</li>
          <li>{t("me.s6l4")}</li>
        </ul>
      </section>

      <section aria-labelledby="me-7" className="stack">
        <h2 id="me-7" className="section-title">{t("me.s7")}</h2>
        <Callout tone="info">{t("me.s7p")}</Callout>
      </section>
    </div>
  );
}
