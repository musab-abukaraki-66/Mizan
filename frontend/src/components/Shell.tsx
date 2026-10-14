import { useApi } from "../lib/api";
import type { Meta } from "../lib/types";
import { ROUTES, useApp, type Route } from "../context";
import { monthLabel } from "../lib/format";

export function BrandMark({ size = 30 }: { size?: number }) {
  return (
    <svg className="brand__mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="8" fill="currentColor" />
      <g fill="none" stroke="#f6f4ee" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 7v18M8 11.5h16M11 25h10" />
        <path d="M8 11.5 5 18h6zM24 11.5 21 18h6z" strokeWidth="1.6" />
      </g>
    </svg>
  );
}

const Icon = {
  present: (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="1.5" y="2.5" width="13" height="8.5" rx="1.5" />
      <path d="M8 11v3M5 14h6" />
    </svg>
  ),
  play: (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M4 2.8v10.4a.6.6 0 0 0 .9.5l8.4-5.2a.6.6 0 0 0 0-1L4.9 2.3a.6.6 0 0 0-.9.5z" />
    </svg>
  ),
  reset: (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2.5 8a5.5 5.5 0 1 0 1.9-4.1M2.5 2.5v3h3" />
    </svg>
  ),
};

export function TopBar() {
  const { t, route, navigate, toggleLang, presenting, togglePresenting, startTour, resetDemo } = useApp();
  const go = (r: Route) => (e: React.MouseEvent) => {
    e.preventDefault();
    navigate(r);
  };
  return (
    <header className="topbar">
      <div className="topbar__inner">
        <a className="brand" href="#/overview" onClick={go("overview")} aria-label={`${t("brand.name")} – ${t("brand.sub")}`}>
          <BrandMark />
          <span className="brand__text">
            <span className="brand__name">{t("brand.name")}</span>
            <span className="brand__sub">{t("brand.sub")}</span>
          </span>
        </a>
        <nav className="nav" aria-label={t("nav.label")}>
          {ROUTES.map((r) => (
            <a key={r} className="nav__link" href={`#/${r}`} onClick={go(r)} aria-current={route === r ? "page" : undefined}>
              {t(`nav.${r}` as const)}
            </a>
          ))}
        </nav>
        <div className="tools">
          {presenting && (
            <>
              <button type="button" className="btn btn--primary" onClick={startTour}>
                {Icon.play}
                {t("tools.tour")}
              </button>
              <button type="button" className="btn btn--ghost" onClick={resetDemo} title={t("tools.reset")}>
                {Icon.reset}
                <span>{t("tools.reset")}</span>
              </button>
            </>
          )}
          <button type="button" className="btn" onClick={togglePresenting} aria-pressed={presenting}>
            {Icon.present}
            <span>{presenting ? t("tools.presentExit") : t("tools.present")}</span>
          </button>
          <button type="button" className="btn" onClick={toggleLang} aria-label={t("tools.lang.label")} lang={presenting ? undefined : undefined}>
            {t("tools.lang")}
          </button>
          {!presenting && (
            <button type="button" className="btn btn--ghost dev-only" onClick={resetDemo} title={t("tools.reset")} aria-label={t("tools.reset")}>
              {Icon.reset}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

export function ProvenanceStrip() {
  const { t, lang } = useApp();
  const { data, error } = useApi<Meta>("/api/meta");
  const verified = !!data && data.provenance_verified;
  return (
    <div className="prov" id="prov-strip" role="region" aria-label={t("prov.verified")}>
      <div className="prov__inner">
        <span className={`prov__status${verified || (!data && !error) ? "" : " is-warn"}`}>
          <span className="prov__dot" aria-hidden="true" />
          {data || error ? (verified ? t("prov.verified") : t("prov.unverified")) : t("prov.loading")}
        </span>
        <span className="prov__item">
          {t("prov.source")}: <b>{t("prov.sourceName")}</b>
        </span>
        {data && (
          <span className="prov__item">
            {t("prov.latest")}: <b>{monthLabel(data.latest.period, lang)}</b>
          </span>
        )}
        <span className="prov__item">{t("prov.base")}</span>
        <span className="prov__note">{t("prov.note")}</span>
      </div>
    </div>
  );
}

export function Footer() {
  const { t } = useApp();
  return (
    <footer className="footer">
      <div className="footer__inner">
        <span>{t("footer.left")}</span>
        <span>{t("footer.right")}</span>
      </div>
    </footer>
  );
}
