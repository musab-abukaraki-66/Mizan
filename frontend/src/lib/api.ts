import { useCallback, useEffect, useState } from "react";

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const cache = new Map<string, Promise<unknown>>();

/** Static hosting (VITE_STATIC=1): map /api/x?query to the pre-exported JSON file (see mizan/export_static.py). */
export function resolveApiPath(path: string, isStatic: boolean = import.meta.env.VITE_STATIC === "1"): string {
  if (!isStatic) return path;
  const u = new URL(path, "http://local");
  const q = u.searchParams;
  if (u.pathname === "/api/forecast")
    return `/api/forecast/${q.get("horizon") ?? "3"}/${q.get("model") ?? "champion"}/${q.get("interval") ?? "calibrated"}.json`;
  if (u.pathname === "/api/backtest") return `/api/backtest/${q.get("model")}/${q.get("horizon") ?? "1"}.json`;
  return `${u.pathname}.json`;
}

async function request<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(resolveApiPath(path), { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError(0, "network", "The MIZAN server is not reachable.");
  }
  if (!res.ok) {
    let code = "http_error";
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      const d = body?.detail;
      if (d && typeof d === "object" && !Array.isArray(d)) {
        code = d.code ?? code;
        message = d.message ?? message;
      } else if (Array.isArray(d)) {
        code = "invalid_request";
        message = d.map((x: { msg?: string }) => x.msg).join("; ");
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code, message);
  }
  return (await res.json()) as T;
}

export function fetchJson<T>(path: string, fresh = false): Promise<T> {
  if (fresh) cache.delete(path);
  let p = cache.get(path) as Promise<T> | undefined;
  if (!p) {
    p = request<T>(path);
    cache.set(path, p);
    p.catch(() => cache.delete(path)); // never cache failures
  }
  return p;
}

export function clearApiCache(): void {
  cache.clear();
}

export interface ApiState<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
}

export function useApi<T>(path: string | null): ApiState<T> {
  const [state, setState] = useState<{ data: T | null; error: ApiError | null; loading: boolean; path: string | null }>({
    data: null,
    error: null,
    loading: path !== null,
    path,
  });
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (path === null) return;
    let alive = true;
    setState((s) => (s.path === path ? { ...s, loading: true, error: null } : { data: null, error: null, loading: true, path }));
    fetchJson<T>(path, tick > 0)
      .then((data) => alive && setState({ data, error: null, loading: false, path }))
      .catch((error: ApiError) => alive && setState({ data: null, error, loading: false, path }));
    return () => {
      alive = false;
    };
  }, [path, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  const current = state.path === path;
  return { data: current ? state.data : null, error: current ? state.error : null, loading: path !== null && (!current || state.loading), reload };
}
