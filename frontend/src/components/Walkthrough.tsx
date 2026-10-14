import { useEffect } from "react";
import { fetchJson } from "../lib/api";
import type { Overview } from "../lib/types";
import { num } from "../lib/format";
import { useApp } from "../context";
import { useState } from "react";

const STEPS = [
  { id: "prov-strip", key: "1" },
  { id: "headline", key: "2" },
  { id: "main-chart", key: "3" },
  { id: "evidence", key: "4" },
  { id: "caveats", key: "5" },
] as const;

export function Walkthrough() {
  const { t, lang, tourStep, setTourStep, route } = useApp();
  const [origins, setOrigins] = useState<number | null>(null);

  useEffect(() => {
    if (tourStep === null) return;
    let alive = true;
    fetchJson<Overview>("/api/overview")
      .then((o) => alive && setOrigins(o.design.origins))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [tourStep]);

  useEffect(() => {
    if (tourStep === null) return;
    const step = STEPS[tourStep];
    const el = step ? document.getElementById(step.id) : null;
    if (!el) return;
    el.setAttribute("data-spotlight", "on");
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
    return () => el.removeAttribute("data-spotlight");
  }, [tourStep]);

  useEffect(() => {
    if (route !== "overview" && tourStep !== null) setTourStep(null);
  }, [route, tourStep, setTourStep]);

  useEffect(() => {
    if (tourStep === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTourStep(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tourStep, setTourStep]);

  if (tourStep === null) return null;
  const step = STEPS[tourStep];
  if (!step) return null;
  const last = tourStep === STEPS.length - 1;
  const n = origins === null ? "" : num(origins, lang, 0);
  const titleKey = `tour.${step.key}.title` as const;
  const bodyKey = `tour.${step.key}.body` as const;

  return (
    <div className="tour" role="dialog" aria-modal="false" aria-labelledby="tour-title" aria-describedby="tour-body">
      <div className="tour__card">
        <span className="tour__step">{t("tour.step", { n: num(tourStep + 1, lang, 0), total: num(STEPS.length, lang, 0) })}</span>
        <div className="tour__title" id="tour-title">
          {t(titleKey)}
        </div>
        <p className="tour__body" id="tour-body">
          {t(bodyKey, { n })}
        </p>
        <div className="tour__actions">
          <div className="tour__dots" aria-hidden="true">
            {STEPS.map((s, i) => (
              <span key={s.id} className={`tour__dot${i === tourStep ? " is-on" : ""}`} />
            ))}
          </div>
          <button type="button" className="btn" onClick={() => setTourStep(null)}>
            {t("tour.close")}
          </button>
          {tourStep > 0 && (
            <button type="button" className="btn" onClick={() => setTourStep(tourStep - 1)}>
              {t("tour.back")}
            </button>
          )}
          <button type="button" className="btn btn--primary" onClick={() => setTourStep(last ? null : tourStep + 1)} autoFocus>
            {last ? t("tour.finish") : t("tour.next")}
          </button>
        </div>
      </div>
    </div>
  );
}
