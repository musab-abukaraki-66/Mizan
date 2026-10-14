"""Forecast accuracy metrics. Index-scale errors and inflation-rate errors are named separately."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t as student_t


def mase_scale(train_values: np.ndarray) -> float:
    """In-sample mean absolute one-step naive error (the MASE denominator)."""
    d = np.abs(np.diff(np.asarray(train_values, dtype=float)))
    if len(d) == 0 or not np.all(np.isfinite(d)) or d.mean() == 0:
        raise ValueError("cannot compute a MASE scale from this training sample")
    return float(d.mean())


def accuracy(df: pd.DataFrame, scale: float) -> dict[str, Any]:
    """Metrics for one block of backtest rows (one model, one horizon, one window).

    Required columns: actual, forecast, lo80, hi80, lo95, hi95, yoy_actual, yoy_forecast.
    """
    n = len(df)
    if n == 0:
        return {"n": 0}
    e = (df["forecast"] - df["actual"]).to_numpy(float)
    a = df["actual"].to_numpy(float)
    ey = (df["yoy_forecast"] - df["yoy_actual"]).to_numpy(float)
    ok_y = np.isfinite(ey)
    out: dict[str, Any] = {
        "n": int(n),
        "mae": float(np.mean(np.abs(e))),
        "rmse": float(np.sqrt(np.mean(e**2))),
        "mase": float(np.mean(np.abs(e)) / scale),
        "mape_pct": float(100 * np.mean(np.abs(e) / a)),
        "bias": float(np.mean(e)),
        "yoy_mae_pp": float(np.mean(np.abs(ey[ok_y]))) if ok_y.any() else None,
        "yoy_rmse_pp": float(np.sqrt(np.mean(ey[ok_y] ** 2))) if ok_y.any() else None,
    }
    for lv in ("80", "95"):
        lo, hi = df[f"lo{lv}"].to_numpy(float), df[f"hi{lv}"].to_numpy(float)
        out[f"coverage{lv}"] = float(np.mean((a >= lo) & (a <= hi)))
        out[f"width{lv}"] = float(np.mean(hi - lo))
        if f"lo{lv}c" in df.columns:
            c = df[[f"lo{lv}c", f"hi{lv}c", "actual"]].dropna()
            out["cal_n"] = int(len(c))
            if len(c):
                out[f"cal_coverage{lv}"] = float(np.mean((c["actual"] >= c[f"lo{lv}c"]) & (c["actual"] <= c[f"hi{lv}c"])))
                out[f"cal_width{lv}"] = float(np.mean(c[f"hi{lv}c"] - c[f"lo{lv}c"]))
    return out


def diebold_mariano(err_model: np.ndarray, err_base: np.ndarray, h: int) -> dict[str, Any] | None:
    """Diebold-Mariano test (squared-error loss) with the Harvey-Leybourne-Newbold small-sample correction.

    H0: equal predictive accuracy. A negative statistic means the model has the smaller squared error.
    Returns None when the sample is too small for a meaningful test.
    """
    e1, e2 = np.asarray(err_model, float), np.asarray(err_base, float)
    n = len(e1)
    if n < max(8, 2 * h) or n != len(e2):
        return None
    d = e1**2 - e2**2
    dbar = d.mean()
    dc = d - dbar
    gamma0 = float(np.dot(dc, dc) / n)
    var = gamma0
    for k in range(1, h):
        gk = float(np.dot(dc[k:], dc[:-k]) / n)
        var += 2 * gk
    if not math.isfinite(var) or var <= 0:
        return None
    dm = dbar / math.sqrt(var / n)
    hln = math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat = hln * dm
    p = 2 * float(student_t.sf(abs(stat), df=n - 1))
    return {"stat": float(stat), "p_value": p, "n": int(n)}
