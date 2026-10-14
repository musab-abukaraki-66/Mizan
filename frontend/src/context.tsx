import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { makeT, type TFn } from "./i18n";
import type { Horizon, Lang, ModelId } from "./lib/types";

export type Route = "overview" | "studio" | "arena" | "quality" | "methods";
export const ROUTES: Route[] = ["overview", "studio", "arena", "quality", "methods"];
export type Measure = "index" | "yoy";
export type IntervalMethod = "calibrated" | "model";

export interface StudioState {
  horizon: Horizon;
  model: ModelId | null; // null = the selected (champion) model for the horizon
  measure: Measure;
  interval: IntervalMethod;
}
export interface OverviewState {
  years: 3 | 5 | 10 | 0; // 0 = all
  measure: Measure;
}
export interface ArenaState {
  horizon: Horizon;
  window: "dev" | "test" | "all";
  model: ModelId;
}

const DEFAULT_LANG: Lang = "ar";
export const DEFAULTS = {
  studio: { horizon: 3, model: null, measure: "index", interval: "calibrated" } as StudioState,
  overview: { years: 5, measure: "index" } as OverviewState,
  arena: { horizon: 3, window: "dev", model: "sarima" } as ArenaState,
};

function store(key: string, value?: string | null): string | null {
  try {
    if (value === undefined) return window.localStorage.getItem(key);
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode, blocked) - the app works without it */
  }
  return null;
}

function initialLang(): Lang {
  const q = new URLSearchParams(window.location.search).get("lang");
  if (q === "ar" || q === "en") return q;
  const saved = store("mizan.lang");
  if (saved === "ar" || saved === "en") return saved;
  return DEFAULT_LANG;
}
function initialPresenting(): boolean {
  const q = new URLSearchParams(window.location.search).get("present");
  if (q === "1") return true;
  if (q === "0") return false;
  return store("mizan.present") === "1";
}
export function parseRoute(hash: string): Route {
  const name = hash.replace(/^#\/?/, "").split(/[?/]/)[0] as Route;
  return ROUTES.includes(name) ? name : "overview";
}

interface AppCtx {
  lang: Lang;
  rtl: boolean;
  t: TFn;
  setLang: (l: Lang) => void;
  toggleLang: () => void;
  route: Route;
  navigate: (r: Route) => void;
  presenting: boolean;
  togglePresenting: () => void;
  tourStep: number | null;
  startTour: () => void;
  setTourStep: (n: number | null) => void;
  resetDemo: () => void;
  studio: StudioState;
  setStudio: (p: Partial<StudioState>) => void;
  overview: OverviewState;
  setOverview: (p: Partial<OverviewState>) => void;
  arena: ArenaState;
  setArena: (p: Partial<ArenaState>) => void;
}

const Ctx = createContext<AppCtx | null>(null);

export function useApp(): AppCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useApp must be used inside <AppProvider>");
  return c;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  const [presenting, setPresenting] = useState<boolean>(initialPresenting);
  const [tourStep, setTourStep] = useState<number | null>(null);
  const [studio, setStudioState] = useState<StudioState>(DEFAULTS.studio);
  const [overview, setOverviewState] = useState<OverviewState>(DEFAULTS.overview);
  const [arena, setArenaState] = useState<ArenaState>(DEFAULTS.arena);

  const t = useMemo(() => makeT(lang), [lang]);
  const rtl = lang === "ar";

  useEffect(() => {
    const root = document.documentElement;
    root.lang = lang;
    root.dir = rtl ? "rtl" : "ltr";
    document.title = t("app.title");
    store("mizan.lang", lang);
  }, [lang, rtl, t]);

  useEffect(() => {
    document.body.classList.toggle("presenting", presenting);
    store("mizan.present", presenting ? "1" : "0");
  }, [presenting]);

  useEffect(() => {
    const onHash = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = useCallback((r: Route) => {
    window.location.hash = `#/${r}`;
    setRoute(r);
    window.scrollTo({ top: 0 });
  }, []);

  const value = useMemo<AppCtx>(
    () => ({
      lang,
      rtl,
      t,
      setLang: setLangState,
      toggleLang: () => setLangState((l) => (l === "ar" ? "en" : "ar")),
      route,
      navigate,
      presenting,
      togglePresenting: () => {
        setPresenting((p) => {
          if (!p) {
            window.location.hash = "#/overview"; // presentation always starts on the best overview screen
            setRoute("overview");
            window.scrollTo({ top: 0 });
          }
          setTourStep(null);
          return !p;
        });
      },
      tourStep,
      startTour: () => {
        window.location.hash = "#/overview";
        setRoute("overview");
        window.scrollTo({ top: 0 });
        setTourStep(0);
      },
      setTourStep,
      resetDemo: () => {
        setLangState(DEFAULT_LANG);
        setPresenting(false);
        setTourStep(null);
        setStudioState(DEFAULTS.studio);
        setOverviewState(DEFAULTS.overview);
        setArenaState(DEFAULTS.arena);
        window.location.hash = "#/overview";
        setRoute("overview");
        window.scrollTo({ top: 0 });
      },
      studio,
      setStudio: (p) => setStudioState((s) => ({ ...s, ...p })),
      overview,
      setOverview: (p) => setOverviewState((s) => ({ ...s, ...p })),
      arena,
      setArena: (p) => setArenaState((s) => ({ ...s, ...p })),
    }),
    [lang, rtl, t, route, navigate, presenting, tourStep, studio, overview, arena],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
