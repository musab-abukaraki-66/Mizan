"""Chronological rolling-origin (expanding-window) backtest.

For each forecast origin t (the last month visible to the model) every model is
fitted on observations <= t only and forecasts t+1..t+H. Actuals after t are used
solely to score the forecast afterwards. Nothing is shuffled, scaled or selected
with future data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from mizan.config import ExperimentConfig
from mizan.forecasting.models import MODELS, ModelFitError


@dataclass
class BacktestResult:
    rows: pd.DataFrame
    failures: list[dict[str, Any]] = field(default_factory=list)
    n_origins: int = 0


def origin_indices(n: int, cfg: ExperimentConfig) -> list[int]:
    """0-based index of the last training observation for each forecast origin."""
    return list(range(cfg.min_train - 1, n - 1))


def window_of(target_idx: int, n: int, cfg: ExperimentConfig) -> str:
    """'test' for target months in the final untouched window, else 'dev'."""
    return "test" if target_idx >= n - cfg.test_months else "dev"


def split_origins(n: int, cfg: ExperimentConfig, horizon: int) -> dict[str, list[int]]:
    """Origins whose target (origin + horizon) falls in the dev vs the test window."""
    out: dict[str, list[int]] = {"dev": [], "test": []}
    for t in origin_indices(n, cfg):
        tgt = t + horizon
        if tgt <= n - 1:
            out[window_of(tgt, n, cfg)].append(t)
    return out


def backtest_model(model_id: str, series: pd.Series, cfg: ExperimentConfig) -> BacktestResult:
    model = MODELS[model_id]
    s = series.sort_index()
    n = len(s)
    vals = s.to_numpy(float)
    state: dict[str, Any] = {"spec": None, "reselect_every": cfg.reselect_every}
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    origins = origin_indices(n, cfg)
    for k, t in enumerate(origins):
        train = s.iloc[: t + 1]  # strictly <= origin: no future data reaches the model
        H = min(cfg.max_horizon, n - 1 - t)
        try:
            fc = model.forecast(train, H, cfg.levels, state, origin_no=k)
        except ModelFitError as exc:
            failures.append({"origin": train.index[-1].strftime("%Y-%m"), "reason": str(exc)})
            continue
        for h in range(1, H + 1):  # every horizon 1..max (calibration needs them all)
            tgt = t + h
            ref = vals[tgt - 12] if tgt - 12 >= 0 else np.nan  # observed at the origin when h <= 12
            row = {
                "model": model_id,
                "origin": train.index[-1].strftime("%Y-%m"),
                "target": s.index[tgt].strftime("%Y-%m"),
                "h": h,
                "window": window_of(tgt, n, cfg),
                "actual": vals[tgt],
                "forecast": float(fc.mean[h - 1]),
                "yoy_actual": 100 * (vals[tgt] / ref - 1),
                "yoy_forecast": 100 * (float(fc.mean[h - 1]) / ref - 1),
                "spec": fc.spec,
            }
            for lv in cfg.levels:
                tag = str(int(round(lv * 100)))
                row[f"lo{tag}"] = float(fc.lower[lv][h - 1])
                row[f"hi{tag}"] = float(fc.upper[lv][h - 1])
            rows.append(row)
    return BacktestResult(pd.DataFrame(rows), failures, len(origins))
