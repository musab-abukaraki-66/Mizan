"""Empirically calibrated prediction intervals (online split-conformal style).

Model-based intervals assume the fitted error model is right; in practice they can be too
wide or too narrow. Here the half-width comes from the model's own *past out-of-sample*
forecast errors: at an origin t only errors that were already observable at t (errors
whose target month <= t) are used, so evaluating the coverage of these intervals in the
backtest is itself leakage-free.

Half-width (log scale) for level L with n past errors:
    q = quantile(|log(actual / forecast)|, min(1, ceil((n + 1) * L) / n))   ("higher" rule)
    interval = forecast * exp(-q) ... forecast * exp(+q)
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

MIN_CALIBRATION = 24


def conformal_halfwidth(abs_log_errors: np.ndarray, level: float) -> float | None:
    n = len(abs_log_errors)
    if n < MIN_CALIBRATION:
        return None
    rank = min(1.0, math.ceil((n + 1) * level) / n)
    return float(np.quantile(abs_log_errors, rank, method="higher"))


def _per(period: str) -> int:
    y, m = period.split("-")
    return int(y) * 12 + int(m) - 1


def add_calibrated_intervals(rows: pd.DataFrame, levels: tuple[float, ...]) -> pd.DataFrame:
    """Add lo80c/hi80c/lo95c/hi95c columns (NaN while fewer than MIN_CALIBRATION past errors exist)."""
    out = rows.copy()
    for lv in levels:
        tag = str(int(round(lv * 100)))
        out[f"lo{tag}c"] = np.nan
        out[f"hi{tag}c"] = np.nan
    for (_, _h), g in out.groupby(["model", "h"], sort=False):
        g = g.sort_values("origin")
        origin_t = g["origin"].map(_per).to_numpy()
        target_t = g["target"].map(_per).to_numpy()
        abs_err = np.abs(np.log(g["actual"].to_numpy(float) / g["forecast"].to_numpy(float)))
        fc = g["forecast"].to_numpy(float)
        for pos, idx in enumerate(g.index):
            known = abs_err[target_t <= origin_t[pos]]  # errors already observed at this origin
            for lv in levels:
                q = conformal_halfwidth(known, lv)
                if q is None:
                    continue
                tag = str(int(round(lv * 100)))
                out.at[idx, f"lo{tag}c"] = fc[pos] * math.exp(-q)
                out.at[idx, f"hi{tag}c"] = fc[pos] * math.exp(q)
    return out


def final_halfwidths(rows: pd.DataFrame, model: str, h: int, levels: tuple[float, ...]) -> dict[float, float | None]:
    """Half-widths for the live forecast: every backtest error observed so far for (model, h)."""
    g = rows[(rows["model"] == model) & (rows["h"] == h)]
    err = np.abs(np.log(g["actual"].to_numpy(float) / g["forecast"].to_numpy(float)))
    return {lv: conformal_halfwidth(err, lv) for lv in levels}
