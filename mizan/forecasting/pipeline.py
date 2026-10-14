"""Build the full results bundle: backtests, accuracy tables, champions and live forecasts.

The bundle (data/results/results.json) is what the API serves. It is deterministic
for a given (data, code, config) triple; `cache_key` records that triple so a stale
cache is detected and rebuilt rather than silently served.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
import statsmodels

from mizan import __version__, config
from mizan.config import EXPERIMENT, ExperimentConfig
from mizan.forecasting import backtest as bt
from mizan.forecasting import intervals as iv
from mizan.forecasting import metrics as mx
from mizan.forecasting.models import BASELINES, MODELS, ModelFitError
from mizan.series.loader import load_cpi, load_provenance, sha256_file
from mizan.series.transforms import yoy_change
from mizan.series.validation import validate_series

SOURCE_FILES = ("models.py", "metrics.py", "backtest.py", "intervals.py", "pipeline.py")
WINDOWS = ("dev", "test", "all")


def compute_cache_key(data_sha256: str, cfg: ExperimentConfig = EXPERIMENT) -> str:
    h = hashlib.sha256()
    h.update(data_sha256.encode())
    h.update(json.dumps(cfg.__dict__, sort_keys=True, default=list).encode())
    for name in SOURCE_FILES:
        h.update((Path(__file__).parent / name).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def _round(x: Any, nd: int = 4) -> Any:
    if isinstance(x, float):
        return None if not np.isfinite(x) else round(x, nd)
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, nd) for v in x]
    return x


def _run_one(args: tuple[str, pd.Series, ExperimentConfig]) -> tuple[str, bt.BacktestResult]:
    model_id, series, cfg = args
    return model_id, bt.backtest_model(model_id, series, cfg)


def run_backtests(series: pd.Series, cfg: ExperimentConfig, parallel: bool = True) -> dict[str, bt.BacktestResult]:
    jobs = [(m, series, cfg) for m in MODELS]
    if parallel and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=min(len(jobs), 4)) as ex:
            return dict(ex.map(_run_one, jobs))
    return dict(map(_run_one, jobs))


def accuracy_tables(rows: pd.DataFrame, scale: float, cfg: ExperimentConfig) -> dict[str, Any]:
    """metrics[model][horizon][window] + Diebold-Mariano vs naive."""
    out: dict[str, Any] = {}
    for model_id in MODELS:
        out[model_id] = {}
        for h in cfg.horizons:
            sub = rows[(rows["model"] == model_id) & (rows["h"] == h)]
            blocks: dict[str, Any] = {}
            for w in WINDOWS:
                part = sub if w == "all" else sub[sub["window"] == w]
                blocks[w] = mx.accuracy(part, scale)
                if model_id != "naive" and len(part):
                    base = rows[(rows["model"] == "naive") & (rows["h"] == h)]
                    base = base if w == "all" else base[base["window"] == w]
                    merged = part.merge(base, on=["origin", "target"], suffixes=("", "_b"))
                    if len(merged):
                        dm = mx.diebold_mariano((merged["forecast"] - merged["actual"]).to_numpy(),
                                                (merged["forecast_b"] - merged["actual_b"]).to_numpy(), h)
                        blocks[w]["dm_vs_naive"] = dm
            out[model_id][str(h)] = blocks
    return out


def pick_champions(acc: dict[str, Any], cfg: ExperimentConfig) -> dict[str, Any]:
    """Champion per horizon = lowest development-window RMSE. The final test window is only reported."""
    champs: dict[str, Any] = {}
    for h in cfg.horizons:
        key = str(h)
        dev = {m: acc[m][key]["dev"].get("rmse") for m in MODELS if acc[m][key]["dev"].get("n", 0) > 0}
        if not dev:
            continue
        best = min(dev, key=lambda m: dev[m])
        naive_dev = acc["naive"][key]["dev"]["rmse"]
        test_best = acc[best][key]["test"].get("rmse")
        test_naive = acc["naive"][key]["test"].get("rmse")
        best_baseline = min((m for m in BASELINES if m in dev), key=lambda m: dev[m])
        dm = acc[best][key]["dev"].get("dm_vs_naive") if best != "naive" else None
        beats_dev = best not in BASELINES
        champs[key] = {
            "model": best,
            "dev_rmse": dev[best],
            "naive_dev_rmse": naive_dev,
            "best_baseline": best_baseline,
            "best_baseline_dev_rmse": dev[best_baseline],
            "improvement_vs_naive_pct": 100 * (1 - dev[best] / naive_dev) if naive_dev else None,
            "improvement_vs_best_baseline_pct": 100 * (1 - dev[best] / dev[best_baseline]) if dev[best_baseline] else None,
            "dm_p_vs_naive": dm["p_value"] if dm else None,
            "test_rmse": test_best,
            "naive_test_rmse": test_naive,
            "beats_naive_on_test": (test_best is not None and test_naive is not None and test_best < test_naive),
            "statistical_model_wins_dev": beats_dev,
        }
    return champs


def final_forecasts(series: pd.Series, cfg: ExperimentConfig, rows: pd.DataFrame) -> dict[str, Any]:
    """Fit every model on ALL observations and forecast the next max_horizon months."""
    last = series.index[-1]
    future = pd.date_range(last + pd.offsets.MonthBegin(1), periods=cfg.max_horizon, freq="MS")
    vals = series.to_numpy(float)
    out: dict[str, Any] = {"as_of": last.strftime("%Y-%m"), "periods": [d.strftime("%Y-%m") for d in future], "models": {}}
    for model_id, model in MODELS.items():
        state: dict[str, Any] = {"spec": None, "reselect_every": 1}
        try:
            fc = model.forecast(series, cfg.max_horizon, cfg.levels, state)
        except ModelFitError as exc:
            out["models"][model_id] = {"error": str(exc)}
            continue
        entry: dict[str, Any] = {"spec": fc.spec, "mean": fc.mean.tolist()}
        refs = np.array([vals[len(vals) - 12 + (h - 1)] for h in range(1, cfg.max_horizon + 1)])  # same month last year
        entry["yoy"] = (100 * (fc.mean / refs - 1)).tolist()
        for lv in cfg.levels:
            tag = str(int(round(lv * 100)))
            entry[f"lo{tag}"] = fc.lower[lv].tolist()
            entry[f"hi{tag}"] = fc.upper[lv].tolist()
            entry[f"yoy_lo{tag}"] = (100 * (fc.lower[lv] / refs - 1)).tolist()
            entry[f"yoy_hi{tag}"] = (100 * (fc.upper[lv] / refs - 1)).tolist()
        # empirically calibrated bands from this model's own past out-of-sample errors
        for lv in cfg.levels:
            tag = str(int(round(lv * 100)))
            hw = [iv.final_halfwidths(rows, model_id, h, (lv,))[lv] for h in range(1, cfg.max_horizon + 1)]
            if all(x is not None for x in hw):
                q = np.array(hw, dtype=float)
                entry[f"lo{tag}c"] = (fc.mean * np.exp(-q)).tolist()
                entry[f"hi{tag}c"] = (fc.mean * np.exp(q)).tolist()
                entry[f"yoy_lo{tag}c"] = (100 * (fc.mean * np.exp(-q) / refs - 1)).tolist()
                entry[f"yoy_hi{tag}c"] = (100 * (fc.mean * np.exp(q) / refs - 1)).tolist()
        out["models"][model_id] = entry
    return out


def backtest_series(rows: pd.DataFrame, cfg: ExperimentConfig) -> dict[str, Any]:
    """Compact per-model/per-horizon evaluation series for the UI charts."""
    res: dict[str, Any] = {}
    for model_id in MODELS:
        res[model_id] = {}
        for h in cfg.horizons:
            sub = rows[(rows["model"] == model_id) & (rows["h"] == h)]
            res[model_id][str(h)] = {
                "origin": sub["origin"].tolist(),
                "target": sub["target"].tolist(),
                "window": sub["window"].tolist(),
                "actual": _round(sub["actual"].round(4).tolist()),
                "forecast": _round(sub["forecast"].round(4).tolist()),
                "lo80": _round(sub["lo80"].round(4).tolist()),
                "hi80": _round(sub["hi80"].round(4).tolist()),
                "lo95": _round(sub["lo95"].round(4).tolist()),
                "hi95": _round(sub["hi95"].round(4).tolist()),
                "lo80c": _round(sub["lo80c"].round(4).tolist()),
                "hi80c": _round(sub["hi80c"].round(4).tolist()),
                "lo95c": _round(sub["lo95c"].round(4).tolist()),
                "hi95c": _round(sub["hi95c"].round(4).tolist()),
            }
    return res


def build_results(cfg: ExperimentConfig = EXPERIMENT, *, parallel: bool = True) -> dict[str, Any]:
    series = load_cpi()
    prov = load_provenance()
    csv_hash = sha256_file(config.SERIES_CSV)
    checks = validate_series(series, provenance=prov, csv_sha256=csv_hash)
    failed = [c for c in checks if c.status == "fail"]
    if failed:
        raise RuntimeError("data validation failed: " + "; ".join(f"{c.id}: {c.detail}" for c in failed))
    n = len(series)
    if n < cfg.min_train + cfg.test_months + max(cfg.horizons):
        raise RuntimeError(f"series too short ({n}) for the configured experiment")

    results = run_backtests(series, cfg, parallel=parallel)
    rows = pd.concat([r.rows for r in results.values() if len(r.rows)], ignore_index=True)
    # Fair comparison: score every model on the same (origin, horizon) pairs. A model that failed to fit at some
    # origin must not look better (or worse) merely because it was scored on fewer months.
    keysets = [set(zip(r.rows["origin"], r.rows["h"])) for r in results.values() if len(r.rows)]
    common = set.intersection(*keysets)
    before = len(rows)
    rows = rows[[(o, h) in common for o, h in zip(rows["origin"], rows["h"])]].reset_index(drop=True)
    rows = iv.add_calibrated_intervals(rows, cfg.levels)
    scale = mx.mase_scale(series.to_numpy(float)[: cfg.min_train])
    acc = accuracy_tables(rows, scale, cfg)
    champs = pick_champions(acc, cfg)
    fcs = final_forecasts(series, cfg, rows)

    split = {str(h): {w: len(v) for w, v in bt.split_origins(n, cfg, h).items()} for h in cfg.horizons}
    first_origin = series.index[cfg.min_train - 1]
    specs: dict[str, Any] = {}
    for m in ("ets", "sarima"):
        vc = rows[(rows["model"] == m) & (rows["h"] == 1)]["spec"].value_counts()
        specs[m] = {k: int(v) for k, v in vc.items()}
    bundle = {
        "meta": {
            "version": __version__,
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "cache_key": compute_cache_key(csv_hash, cfg),
            "data_sha256": csv_hash,
            "as_of": series.index[-1].strftime("%Y-%m"),
            "observations": n,
            "config": {**cfg.__dict__, "horizons": list(cfg.horizons), "levels": list(cfg.levels)},
            "design": {
                "first_origin": first_origin.strftime("%Y-%m"),
                "origins": len(bt.origin_indices(n, cfg)),
                "test_window": [series.index[n - cfg.test_months].strftime("%Y-%m"), series.index[-1].strftime("%Y-%m")],
                "dev_window": [series.index[cfg.min_train].strftime("%Y-%m"),
                               series.index[n - cfg.test_months - 1].strftime("%Y-%m")],
                "origins_by_horizon": split,
                "mase_scale": scale,
                "mase_scale_note": "mean absolute one-step naive error over the first min_train observations",
            },
            "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "pandas": pd.__version__,
                            "scipy": scipy.__version__, "statsmodels": statsmodels.__version__,
                            "platform": platform.system()},
        },
        "models": [{"id": m.id, "name": m.name, "description": m.description, "baseline": m.id in BASELINES}
                   for m in MODELS.values()],
        "fit_failures": {m: {"count": len(r.failures), "examples": r.failures[:3]} for m, r in results.items()},
        "comparison_sample": {"rule": "common (origin, horizon) pairs for which every model produced a forecast",
                              "rows_before": int(before), "rows_after": int(len(rows))},
        "selected_specs": specs,
        "accuracy": _round(acc, 5),
        "champions": _round(champs, 5),
        "forecasts": _round(fcs, 5),
        "backtests": backtest_series(rows, cfg),
        "latest_yoy": _round(float(yoy_change(series).iloc[-1]), 4),
    }
    return bundle


def save_results(bundle: dict[str, Any], path: Path | None = None) -> Path:
    path = path or config.RESULTS_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(bundle, fh, ensure_ascii=False, separators=(",", ":"))
    return path


def load_results(path: Path | None = None) -> dict[str, Any]:
    with open(path or config.RESULTS_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def results_are_fresh(path: Path | None = None) -> bool:
    """True when the cached bundle matches the current data, code and configuration."""
    path = path or config.RESULTS_JSON
    if not path.exists() or not config.SERIES_CSV.exists():
        return False
    try:
        cached = load_results(path)
        return cached["meta"]["cache_key"] == compute_cache_key(sha256_file(config.SERIES_CSV))
    except (KeyError, ValueError, OSError):
        return False
