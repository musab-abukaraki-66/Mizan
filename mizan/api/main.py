"""FastAPI application: JSON API + the pre-built front-end bundle, one process, one port."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from mizan import __version__, config
from mizan.api import state as S
from mizan.forecasting import pipeline

app = FastAPI(title="MIZAN API", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")

HORIZON_KEYS = ("1", "3", "6")


def _horizon(h: int) -> int:
    if str(h) not in HORIZON_KEYS:
        allowed = ", ".join(HORIZON_KEYS)
        raise _err(422, "invalid_horizon", f"horizon must be one of {allowed} (months); got {h}")
    return h


@app.exception_handler(S.ResultsUnavailable)
async def _results_unavailable(_: Request, exc: S.ResultsUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": {"code": "results_unavailable", "message": str(exc)}})


def _err(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _model_ids(results: dict[str, Any]) -> list[str]:
    return [m["id"] for m in results["models"]]


def _check_model(results: dict[str, Any], model: str) -> None:
    if model not in _model_ids(results):
        raise _err(404, "unknown_model", f"unknown model '{model}'. Available: {', '.join(_model_ids(results))}")


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        st = S.get_state()
    except Exception as exc:  # noqa: BLE001 - health must never raise
        return {"app": "mizan", "version": __version__, "status": "error", "message": str(exc)}
    ok = st.results is not None and st.results_fresh and S.summarize(st.checks)["ok"]
    return {"app": "mizan", "version": __version__, "status": "ok" if ok else "degraded",
            "data_ok": S.summarize(st.checks)["ok"], "results_available": st.results is not None,
            "results_fresh": st.results_fresh, "latest_period": st.last_period, "observations": len(st.cpi)}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    st = S.get_state()
    p = st.provenance
    return {
        "publisher": p["source"]["publisher"], "publisher_ar": p["source"]["publisher_ar"],
        "dataset": p["source"]["dataset"], "landing_page": p["source"]["landing_page"],
        "retrieved_at_utc": p["retrieval"]["retrieved_at_utc"],
        "series": p["series"], "latest": S.latest_snapshot(st),
        "results_fresh": st.results_fresh,
        "provenance_verified": S.summarize(st.checks)["ok"],
        "disclaimer": "Independent research project - not an official Department of Statistics product. "
                      "Forecasts are statistical projections, not official estimates.",
    }


@app.get("/api/series")
def series() -> dict[str, Any]:
    st = S.get_state()
    rows = [{"period": d.strftime("%Y-%m"), "cpi": float(v),
             "mom": None if np.isnan(m) else float(m), "yoy": None if np.isnan(y) else float(y)}
            for (d, v), m, y in zip(st.cpi.items(), st.mom.to_numpy(), st.yoy.to_numpy())]
    return {"rows": rows, "latest": S.latest_snapshot(st)}


def _band(entry: dict[str, Any], key: str, method: str, prefix: str = "") -> dict[str, Any]:
    sfx = "c" if method == "calibrated" else ""
    out = {}
    for tag in ("80", "95"):
        lo, hi = entry.get(f"{prefix}lo{tag}{sfx}"), entry.get(f"{prefix}hi{tag}{sfx}")
        if lo is not None and hi is not None:
            out[tag] = {"lower": lo[: int(key)], "upper": hi[: int(key)]}
    return out


def _forecast_payload(results: dict[str, Any], model: str, horizon: int, method: str) -> dict[str, Any]:
    fc = results["forecasts"]
    entry = fc["models"].get(model)
    if entry is None or "error" in entry:
        raise _err(503, "model_unavailable", f"model '{model}' could not be fitted on the current data")
    key = str(horizon)
    used = method
    if method == "calibrated" and "lo80c" not in entry:
        used = "model"
    acc = results["accuracy"][model][str(horizon if str(horizon) in HORIZON_KEYS else 1)]
    return {
        "model": model, "spec": entry["spec"], "as_of": fc["as_of"], "horizon": horizon,
        "periods": fc["periods"][:horizon], "mean": entry["mean"][:horizon],
        "yoy": entry["yoy"][:horizon],
        "bands": _band(entry, key, used), "yoy_bands": _band(entry, key, used, prefix="yoy_"),
        "interval_method": used,
        "evaluation": {w: acc[w] for w in ("dev", "test", "all")},
        "baseline_evaluation": {w: results["accuracy"]["naive"][str(horizon)][w] for w in ("dev", "test", "all")},
    }


@app.get("/api/forecast")
def forecast(horizon: int = Query(3), model: str | None = Query(None),
             interval: Literal["calibrated", "model"] = Query("calibrated")) -> dict[str, Any]:
    _horizon(horizon)
    st = S.get_state()
    results = S.require_results(st)
    champ = results["champions"][str(horizon)]
    chosen = model or champ["model"]
    _check_model(results, chosen)
    payload = _forecast_payload(results, chosen, horizon, interval)
    payload["champion"] = champ
    payload["is_champion"] = chosen == champ["model"]
    return payload


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    st = S.get_state()
    results = S.require_results(st)
    summary = {}
    for h in HORIZON_KEYS:
        champ = results["champions"][h]
        p = _forecast_payload(results, champ["model"], int(h), "calibrated")
        i = int(h) - 1
        b80 = p["bands"].get("80")
        yb80 = p["yoy_bands"].get("80")
        summary[h] = {
            "model": champ["model"], "period": p["periods"][-1], "point": p["mean"][i], "yoy": p["yoy"][i],
            "lower": b80["lower"][i] if b80 else None, "upper": b80["upper"][i] if b80 else None,
            "yoy_lower": yb80["lower"][i] if yb80 else None, "yoy_upper": yb80["upper"][i] if yb80 else None,
            "interval_method": p["interval_method"], "champion": champ,
        }
    return {"latest": S.latest_snapshot(st), "forecast_summary": summary,
            "design": results["meta"]["design"], "results_fresh": st.results_fresh}


@app.get("/api/arena")
def arena() -> dict[str, Any]:
    results = S.require_results(S.get_state())
    keep = ("models", "accuracy", "champions", "fit_failures", "selected_specs", "comparison_sample")
    return {**{k: results[k] for k in keep}, "design": results["meta"]["design"],
            "config": results["meta"]["config"], "as_of": results["meta"]["as_of"]}


@app.get("/api/backtest")
def backtest(model: str = Query(...), horizon: int = Query(1)) -> dict[str, Any]:
    _horizon(horizon)
    results = S.require_results(S.get_state())
    _check_model(results, model)
    key = str(horizon)
    return {"model": model, "horizon": horizon, "series": results["backtests"][model][key],
            "metrics": results["accuracy"][model][key], "test_window": results["meta"]["design"]["test_window"]}


@app.get("/api/quality")
def quality() -> dict[str, Any]:
    st = S.get_state()
    p = st.provenance
    return {
        "source": p["source"], "retrieval": p["retrieval"], "series": p["series"], "license": p["license"],
        "ingest_validation": p["validation"], "crosschecks": p["crosschecks"],
        "live_validation": {"summary": S.summarize(st.checks), "checks": [c.as_dict() for c in st.checks]},
        "results_fresh": st.results_fresh,
        "dictionary": [
            {"field": "period", "type": "month (YYYY-MM)", "description": "Reference month of the observation."},
            {"field": "cpi", "type": "float", "description": "Headline consumer price index, all items, 2018 = 100."},
            {"field": "mom", "type": "float, %", "description": "100 x (CPI_t / CPI_(t-1) - 1). Derived by MIZAN."},
            {"field": "yoy", "type": "float, %", "description": "100 x (CPI_t / CPI_(t-12) - 1). Derived by MIZAN."},
        ],
        "cache_key": st.results["meta"]["cache_key"] if st.results else None,
        "results_generated_at_utc": st.results["meta"]["generated_at_utc"] if st.results else None,
        "environment": st.results["meta"]["environment"] if st.results else None,
    }


@app.get("/api/{rest:path}")
def api_not_found(rest: str) -> None:
    raise _err(404, "not_found", f"no such API route: /api/{rest}")


if config.WEB_DIR.exists() and (config.WEB_DIR / "index.html").exists():
    if (config.WEB_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=config.WEB_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        candidate = (config.WEB_DIR / path).resolve()
        if path and candidate.is_file() and config.WEB_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(config.WEB_DIR / "index.html")
else:

    @app.get("/", include_in_schema=False)
    def no_web() -> dict[str, str]:
        return {"app": "mizan", "note": "front-end bundle not built; see docs/ARCHITECTURE.md", "api": "/api/docs"}


__all__ = ["app", "pipeline"]
