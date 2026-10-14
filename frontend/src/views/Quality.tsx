import { Badge, Callout, ErrorBox, Loading, Num, PageHead, StatusBadge } from "../components/ui";
import { useApp } from "../context";
import { useApi } from "../lib/api";
import { bytesLabel, dateTimeLabel, monthLabel, num } from "../lib/format";
import type { Check, Quality as QualityData } from "../lib/types";
import type { Key } from "../i18n";

const INGEST_IDS = ["dos_average_column", "imf_crosscheck", "press_crosscheck"];

function CheckList({ checks }: { checks: Check[] }) {
  const { t, lang } = useApp();
  return (
    <ul className="checks">
      {checks.map((c) => (
        <li className="check" key={c.id}>
          <StatusBadge status={c.status} />
          <span className="check__label">{t(`chk.${c.id}` as Key) === `chk.${c.id}` ? c.label : t(`chk.${c.id}` as Key)}</span>
          <span className="check__detail" lang="en" dir="ltr" style={{ textAlign: lang === "ar" ? "right" : undefined }}>
            {c.detail}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function Quality() {
  const { t, lang } = useApp();
  const { data: q, error, reload } = useApi<QualityData>("/api/quality");

  if (error) return <div className="page"><PageHead eyebrow={t("dq.eyebrow")} title={t("dq.title")} /><ErrorBox error={error} onRetry={reload} /></div>;
  if (!q) return <div className="page"><PageHead eyebrow={t("dq.eyebrow")} title={t("dq.title")} /><Loading height={320} /></div>;

  const s = q.series;
  const v = q.live_validation.summary;
  const dupOk = q.live_validation.checks.find((c) => c.id === "unique")?.status === "pass";
  const press = q.crosschecks.press_release;
  const imf = q.crosschecks.imf;
  const rebase = q.crosschecks.rebase;
  const ingestChecks = q.ingest_validation.checks.filter((c) => INGEST_IDS.includes(c.id));
  const pm = press ? monthLabel(press.reference_month, lang) : "";
  const pressLabel = (id: string): string =>
    id.startsWith("yoy") ? t("dq.press.yoy", { m: pm }) : id.startsWith("mom") ? t("dq.press.mom", { m: pm }) : t("dq.press.avg", { m: pm });
  const bad = imf?.mismatched_months ?? [];
  const maxBad = bad.length ? bad.reduce((a, b) => (Math.abs(b.diff) > Math.abs(a.diff) ? b : a)) : null;

  return (
    <div className="page">
      <PageHead eyebrow={t("dq.eyebrow")} title={t("dq.title")} lead={t("dq.lead")} />

      <section aria-label={t("dq.coverage")}>
        <div className="tiles">
          <div className="tile">
            <div className="tile__v" style={{ fontSize: "1.05rem" }}>
              {monthLabel(s.first_period, lang)} – {monthLabel(s.last_period, lang)}
            </div>
            <div className="tile__l">{t("dq.coverage")}</div>
          </div>
          <div className="tile">
            <div className="tile__v"><Num>{num(s.rows, lang, 0)}</Num></div>
            <div className="tile__l">{t("dq.obs")}</div>
          </div>
          <div className="tile">
            <div className="tile__v"><Num>{num(s.missing_periods.length, lang, 0)}</Num></div>
            <div className="tile__l">{t("dq.missing")}</div>
          </div>
          <div className="tile">
            <div className="tile__v"><Num>{dupOk ? num(0, lang, 0) : "!"}</Num></div>
            <div className="tile__l">{t("dq.dups")}</div>
          </div>
          <div className="tile">
            <div className="tile__v"><Num>2018 = 100</Num></div>
            <div className="tile__l">{t("dq.base")}</div>
          </div>
          <div className="tile">
            <div className="tile__v" style={{ fontSize: "1.02rem" }}>
              {t("dq.checksValue", { p: num(v.passed, lang, 0), w: num(v.warnings, lang, 0), f: num(v.failed, lang, 0) })}
            </div>
            <div className="tile__l">{t("dq.checks")}</div>
          </div>
        </div>
      </section>

      <div className="grid-2">
        <section className="panel" aria-labelledby="dq-source">
          <h2 className="panel__title" id="dq-source">
            {t("dq.sourceTitle")}
          </h2>
          <dl className="kv">
            <dt>{t("dq.publisher")}</dt>
            <dd>{lang === "ar" ? q.source.publisher_ar : q.source.publisher}</dd>
            <dt>{t("dq.dataset")}</dt>
            <dd><span lang="en" dir="ltr">{q.source.dataset}</span></dd>
            <dt>{t("dq.page")}</dt>
            <dd>
              <a href={q.source.landing_page} target="_blank" rel="noreferrer noopener" dir="ltr">
                dosweb.dos.gov.jo
              </a>
            </dd>
            <dt>{t("dq.definition")}</dt>
            <dd><span lang="en" dir="ltr">{s.definition}</span></dd>
            <dt>{t("dq.frequency")}</dt>
            <dd>{t("dq.freq.monthly")}</dd>
            <dt>{t("dq.base")}</dt>
            <dd><span lang="en" dir="ltr">{s.base}</span></dd>
            <dt>{t("dq.units")}</dt>
            <dd><span lang="en" dir="ltr">{s.units}</span></dd>
            <dt>{t("dq.sa")}</dt>
            <dd><span lang="en" dir="ltr">{s.seasonal_adjustment}</span></dd>
            <dt>{t("dq.retrieved")}</dt>
            <dd>{dateTimeLabel(q.retrieval.retrieved_at_utc, lang)}</dd>
            <dt>{t("dq.derived")}</dt>
            <dd>{t("dq.derivedValue")}</dd>
          </dl>
        </section>

        <section className="panel" aria-labelledby="dq-checks">
          <h2 className="panel__title" id="dq-checks">
            {t("dq.checksTitle")}
          </h2>
          <CheckList checks={q.live_validation.checks} />
        </section>
      </div>

      <section className="panel" aria-labelledby="dq-ingest">
        <div>
          <h2 className="panel__title" id="dq-ingest">
            {t("dq.ingestTitle")}
          </h2>
          <p className="panel__sub">{t("dq.ingestSub")}</p>
        </div>
        <CheckList checks={ingestChecks} />
        {press && (
          <div className="stack">
            <div>
              <h3 className="panel__title" style={{ fontSize: "1rem" }}>{t("dq.pressTitle")}</h3>
              <p className="panel__sub">{t("dq.pressSub")}</p>
            </div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">{t("dq.press.item")}</th>
                    <th scope="col" className="is-num">{t("dq.press.stated")}</th>
                    <th scope="col" className="is-num">{t("dq.press.computed")}</th>
                  </tr>
                </thead>
                <tbody>
                  {press.results.map((r) => (
                    <tr key={r.id}>
                      <th scope="row" className="wrap">{pressLabel(r.id)}</th>
                      <td className="is-num"><Num>{num(r.stated, lang, 2)}%</Num></td>
                      <td className="is-num"><Num>{num(r.computed, lang, 3)}%</Num> {r.ok ? <Badge tone="ok">✓</Badge> : <Badge tone="bad">✗</Badge>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="small muted">
              <a href={press.source.url} target="_blank" rel="noreferrer noopener" dir="ltr">{press.source.name}</a>
            </p>
          </div>
        )}
        {imf?.overlap_months !== undefined && (
          <Callout tone={bad.length ? "warn" : "info"} title={t("dq.imfTitle")}>
            {bad.length === 0
              ? t("dq.imfAll", { n: num(imf.overlap_months, lang, 0) })
              : t("dq.imfText", {
                  ok: num(imf.overlap_months - bad.length, lang, 0),
                  n: num(imf.overlap_months, lang, 0),
                  bad: num(bad.length, lang, 0),
                  max: maxBad ? `${monthLabel(maxBad.period, lang, "short")}: ${num(maxBad.dos, lang, 2)} / ${num(maxBad.imf, lang, 2)}` : "",
                })}
          </Callout>
        )}
        {rebase && (
          <Callout tone="warn" title={t("dq.breakTitle")}>
            {t("dq.breakText", {
              a: num(rebase.jan_2018_mom_pct_2018base, lang, 2),
              b: num(rebase.jan_2018_mom_pct_2010base, lang, 2),
            })}
          </Callout>
        )}
      </section>

      <div className="grid-2">
        <section className="panel" aria-labelledby="dq-dict">
          <h2 className="panel__title" id="dq-dict">
            {t("dq.dictTitle")}
          </h2>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">{t("dq.dict.field")}</th>
                  <th scope="col">{t("dq.dict.type")}</th>
                  <th scope="col">{t("dq.dict.desc")}</th>
                </tr>
              </thead>
              <tbody>
                {q.dictionary.map((d) => (
                  <tr key={d.field}>
                    <th scope="row"><code>{d.field}</code></th>
                    <td lang="en" dir="ltr">{d.type}</td>
                    <td className="wrap" lang="en" dir="ltr">{d.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <Callout tone="info" title={t("dq.licenseTitle")} id="license">
          {t("dq.licenseText")}
        </Callout>
      </div>

      <details className="details dev-only">
        <summary>{t("dq.techTitle")}</summary>
        <div>
          <dl className="kv">
            <dt>{t("dq.tech.csv")}</dt>
            <dd className="mono num" dir="ltr">{s.csv_sha256}</dd>
            <dt>{t("dq.tech.cache")}</dt>
            <dd className="mono num" dir="ltr">{q.cache_key?.slice(0, 32)}…</dd>
            <dt>{t("dq.tech.generated")}</dt>
            <dd>{q.results_generated_at_utc ? dateTimeLabel(q.results_generated_at_utc, lang) : "–"}</dd>
            <dt>{t("dq.tech.env")}</dt>
            <dd className="num" dir="ltr">{q.environment ? Object.entries(q.environment).map(([k, val]) => `${k} ${val}`).join(" · ") : "–"}</dd>
          </dl>
          <h3 className="panel__title" style={{ fontSize: "1rem" }}>{t("dq.tech.files")}</h3>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">{t("dq.tech.year")}</th>
                  <th scope="col" className="is-num">{t("dq.tech.size")}</th>
                  <th scope="col">{t("dq.tech.sha")}</th>
                  <th scope="col">{t("dq.tech.avg")}</th>
                </tr>
              </thead>
              <tbody>
                {q.retrieval.files.map((f) => (
                  <tr key={f.year}>
                    <th scope="row"><Num>{f.year}</Num></th>
                    <td className="is-num"><Num>{bytesLabel(f.bytes, lang)}</Num></td>
                    <td className="mono">{f.sha256.slice(0, 20)}…</td>
                    <td>{f.average_check.checked ? (f.average_check.ok ? <Badge tone="ok">✓</Badge> : <Badge tone="bad">✗</Badge>) : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </details>
    </div>
  );
}
