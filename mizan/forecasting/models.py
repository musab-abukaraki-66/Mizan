"""Forecast models for the monthly CPI index.

All models take only the training series (everything observed up to the forecast
origin) and return point forecasts plus prediction intervals on the index scale.
Model families that are multiplicative in nature (ETS, ARIMA) are fitted to
log(CPI). Specification search (information criterion) uses the training window
only, so no model ever sees data after its forecast origin.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

SIGMA_WINDOW = 60  # months of history used to scale baseline prediction intervals


class ModelFitError(RuntimeError):
    """Raised when a model cannot be fitted or forecast on the given history."""


@dataclass
class Forecast:
    mean: np.ndarray  # (H,) point forecast on the index scale
    lower: dict[float, np.ndarray] = field(default_factory=dict)
    upper: dict[float, np.ndarray] = field(default_factory=dict)
    spec: str = ""


def _z(level: float) -> float:
    return float(norm.ppf(0.5 + level / 2.0))


def _logs(train: pd.Series) -> np.ndarray:
    v = train.to_numpy(dtype=float)
    if len(v) < 14 or not np.all(np.isfinite(v)) or np.any(v <= 0):
        raise ModelFitError("insufficient or invalid history")
    return np.log(v)


def _bands_from_sd(center_log: np.ndarray, sd: np.ndarray, levels: tuple[float, ...]) -> tuple[dict, dict]:
    lo = {lv: np.exp(center_log - _z(lv) * sd) for lv in levels}
    hi = {lv: np.exp(center_log + _z(lv) * sd) for lv in levels}
    return lo, hi


def _recent_std(x: np.ndarray, window: int = SIGMA_WINDOW) -> float:
    x = x[-window:]
    if len(x) < 6:
        raise ModelFitError("not enough observations to scale prediction intervals")
    return float(np.std(x, ddof=1))


class Model:
    id = ""
    name = ""
    description = ""

    def forecast(self, train: pd.Series, horizon: int, levels: tuple[float, ...], state: dict[str, Any],
                 origin_no: int = 0) -> Forecast:
        raise NotImplementedError


class Naive(Model):
    id = "naive"
    name = "Naive (last value)"
    description = "Every future month equals the last observed index value."

    def forecast(self, train, horizon, levels, state, origin_no=0):
        ly = _logs(train)
        sigma = _recent_std(np.diff(ly))
        h = np.arange(1, horizon + 1)
        center = np.full(horizon, ly[-1])
        lo, hi = _bands_from_sd(center, sigma * np.sqrt(h), levels)
        return Forecast(np.exp(center), lo, hi, "random walk")


class SeasonalNaive(Model):
    id = "seasonal_naive"
    name = "Seasonal naive (same month last year)"
    description = "Every future month equals the index value of the same calendar month one year earlier."

    def forecast(self, train, horizon, levels, state, origin_no=0):
        ly = _logs(train)
        if len(ly) < 24:
            raise ModelFitError("needs at least 24 observations")
        h = np.arange(1, horizon + 1)
        center = np.array([ly[len(ly) - 12 + ((k - 1) % 12)] for k in h])
        sigma = _recent_std(ly[12:] - ly[:-12])
        sd = sigma * np.sqrt((h - 1) // 12 + 1)
        lo, hi = _bands_from_sd(center, sd, levels)
        return Forecast(np.exp(center), lo, hi, "seasonal random walk (lag 12)")


class Drift(Model):
    id = "drift"
    name = "Drift (12-month average growth)"
    description = "Last value grown at the average monthly growth rate of the previous 12 months."

    def __init__(self, window: int = 12):
        self.window = window

    def forecast(self, train, horizon, levels, state, origin_no=0):
        ly = _logs(train)
        d1 = np.diff(ly)
        if len(d1) < self.window + 6:
            raise ModelFitError("not enough history for the drift window")
        drift = float(np.mean(d1[-self.window:]))
        sigma = _recent_std(d1)
        h = np.arange(1, horizon + 1)
        center = ly[-1] + drift * h
        sd = sigma * np.sqrt(h + h**2 / self.window)  # accounts for drift-estimation error
        lo, hi = _bands_from_sd(center, sd, levels)
        return Forecast(np.exp(center), lo, hi, f"drift {100 * drift:.3f}%/month")


def _aicc(res: Any, nobs: int) -> float:
    k = len(res.params)
    aic = float(res.aic)
    denom = nobs - k - 1
    return aic + 2.0 * k * (k + 1) / denom if denom > 0 else np.inf


def _month_series(values: np.ndarray, last: pd.Timestamp) -> pd.Series:
    idx = pd.date_range(end=last, periods=len(values), freq="MS")
    return pd.Series(values, index=idx)


class ETS(Model):
    """Additive-error exponential smoothing on log(CPI); trend/damping/seasonality picked by AICc."""

    id = "ets"
    name = "ETS (exponential smoothing)"
    description = ("State-space exponential smoothing fitted to log CPI. Trend (none / additive / damped) and additive "
                   "seasonality are chosen by AICc on the training window.")
    GRID = [
        (None, False, None),
        ("add", True, None),
        ("add", False, None),
        (None, False, "add"),
        ("add", True, "add"),
        ("add", False, "add"),
    ]

    def _fit(self, ly: pd.Series, spec):
        from statsmodels.tsa.exponential_smoothing.ets import ETSModel

        trend, damped, seasonal = spec
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod = ETSModel(ly, error="add", trend=trend, damped_trend=damped, seasonal=seasonal,
                           seasonal_periods=12 if seasonal else None)
            return mod.fit(disp=False, maxiter=200)

    @staticmethod
    def _label(spec) -> str:
        trend, damped, seasonal = spec
        t = "N" if trend is None else ("Ad" if damped else "A")
        return f"ETS(A,{t},{'A' if seasonal else 'N'})"

    def forecast(self, train, horizon, levels, state, origin_no=0):
        ly = _month_series(_logs(train), train.index[-1])
        if state.get("spec") is None or origin_no - state.get("selected_at", -10**9) >= state["reselect_every"]:
            best, best_ic = None, np.inf
            for spec in self.GRID:
                try:
                    res = self._fit(ly, spec)
                    ic = _aicc(res, len(ly))
                except Exception:  # noqa: BLE001 - a failing candidate is simply not eligible
                    continue
                if np.isfinite(ic) and ic < best_ic:
                    best, best_ic = spec, ic
            if best is None:
                raise ModelFitError("no ETS specification could be fitted")
            state["spec"], state["selected_at"] = best, origin_no
        spec = state["spec"]
        try:
            res = self._fit(ly, spec)
        except Exception as exc:  # noqa: BLE001
            raise ModelFitError(f"{self._label(spec)} failed: {exc}") from exc
        n = len(ly)
        try:
            frames = {lv: res.get_prediction(start=n, end=n + horizon - 1).summary_frame(alpha=1 - lv) for lv in levels}
        except Exception as exc:  # noqa: BLE001
            raise ModelFitError(f"{self._label(spec)} could not forecast: {exc}") from exc
        mean_log = frames[levels[0]]["mean"].to_numpy(float)
        lo = {lv: np.exp(f["pi_lower"].to_numpy(float)) for lv, f in frames.items()}
        hi = {lv: np.exp(f["pi_upper"].to_numpy(float)) for lv, f in frames.items()}
        out = Forecast(np.exp(mean_log), lo, hi, self._label(spec))
        if not (np.all(np.isfinite(out.mean)) and all(np.all(np.isfinite(v)) for v in (*lo.values(), *hi.values()))):
            raise ModelFitError("non-finite ETS forecast")
        return out


class Sarima(Model):
    """ARIMA(p,1,q)(P,0,Q)12 with drift on log(CPI); orders picked by AICc on the training window."""

    id = "sarima"
    name = "SARIMA"
    description = ("Seasonal ARIMA with one difference and a drift term, fitted to log CPI. The AR/MA and seasonal "
                   "AR/MA orders are chosen from a small grid by AICc on the training window.")
    GRID = [((p, 1, q), (P, 0, Q, 12)) for (p, q) in [(1, 0), (0, 1), (1, 1), (2, 1)] for (P, Q) in [(0, 0), (1, 0), (0, 1)]]

    def _fit(self, ly: pd.Series, spec):
        from statsmodels.tsa.arima.model import ARIMA

        order, sorder = spec
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            res = ARIMA(ly, order=order, seasonal_order=sorder, trend="t").fit(method_kwargs={"maxiter": 300})
        if any("onverge" in str(w.message) for w in caught):
            raise ModelFitError("did not converge")
        return res

    @staticmethod
    def _label(spec) -> str:
        (p, d, q), (P, D, Q, s) = spec
        seasonal = f"({P},{D},{Q})[{s}]" if (P or Q) else ""
        return f"ARIMA({p},{d},{q}){seasonal} + drift"

    def forecast(self, train, horizon, levels, state, origin_no=0):
        ly = _month_series(_logs(train), train.index[-1])
        if not state.get("ranked") or origin_no - state.get("selected_at", -10**9) >= state["reselect_every"]:
            scored: list[tuple[float, Any]] = []
            for spec in self.GRID:
                try:
                    ic = _aicc(self._fit(ly, spec), len(ly))
                except Exception:  # noqa: BLE001 - a failing candidate is simply not eligible
                    continue
                if np.isfinite(ic):
                    scored.append((ic, spec))
            if not scored:
                raise ModelFitError("no SARIMA specification converged")
            state["ranked"] = [sp for _, sp in sorted(scored, key=lambda x: x[0])]
            state["selected_at"] = origin_no
        last_exc: Exception | None = None
        for spec in state["ranked"]:  # best-AICc spec first; fall back to the next-best if it fails to converge
            try:
                res = self._fit(ly, spec)
                fc = res.get_forecast(horizon)
                mean_log = np.asarray(fc.predicted_mean, dtype=float)
                ci = {lv: np.asarray(fc.conf_int(alpha=1 - lv), dtype=float) for lv in levels}
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                continue
            lo = {lv: np.exp(c[:, 0]) for lv, c in ci.items()}
            hi = {lv: np.exp(c[:, 1]) for lv, c in ci.items()}
            out = Forecast(np.exp(mean_log), lo, hi, self._label(spec))
            if np.all(np.isfinite(out.mean)) and all(np.all(np.isfinite(v)) for v in (*lo.values(), *hi.values())):
                return out
        raise ModelFitError(f"no SARIMA specification could be fitted at this origin: {last_exc}")


MODELS: dict[str, Model] = {m.id: m for m in (Naive(), SeasonalNaive(), Drift(), ETS(), Sarima())}
BASELINES = ("naive", "seasonal_naive", "drift")
