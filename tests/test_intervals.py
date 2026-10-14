import math

import numpy as np
import pandas as pd
import pytest

from mizan.forecasting import intervals as iv


def test_conformal_halfwidth_matches_manual_quantile():
    errs = np.arange(1, 41) / 100.0  # 0.01 .. 0.40  (n = 40)
    n, level = 40, 0.8
    rank = math.ceil((n + 1) * level) / n  # 33/40 = 0.825
    assert iv.conformal_halfwidth(errs, level) == pytest.approx(np.quantile(errs, rank, method="higher"))
    assert iv.conformal_halfwidth(errs, 0.95) == pytest.approx(0.39 + 0.01)  # rank capped near the maximum


def test_too_few_errors_gives_no_band():
    assert iv.conformal_halfwidth(np.ones(iv.MIN_CALIBRATION - 1) * 0.01, 0.8) is None


def _rows(n=60, h=2):
    origins = pd.period_range("2015-01", periods=n, freq="M")
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "model": "m", "h": h,
        "origin": [p.strftime("%Y-%m") for p in origins],
        "target": [(p + h).strftime("%Y-%m") for p in origins],
        "actual": 100 * np.exp(rng.normal(0, 0.01, n)), "forecast": 100.0,
    })


def test_calibration_uses_only_errors_observable_at_the_origin():
    rows = _rows()
    out = iv.add_calibrated_intervals(rows, (0.8,))
    # Poison the error of one late origin: bands at earlier origins must be unchanged.
    poisoned = rows.copy()
    poisoned.loc[50, "actual"] = 500.0
    out2 = iv.add_calibrated_intervals(poisoned, (0.8,))
    # error at origin index 50 has target index 52 -> only affects origins >= 52
    assert out.loc[:51, "hi80c"].equals(out2.loc[:51, "hi80c"])
    assert not out.loc[52:, "hi80c"].equals(out2.loc[52:, "hi80c"])


def test_calibrated_bands_are_ordered_and_start_after_min_history():
    out = iv.add_calibrated_intervals(_rows(), (0.8, 0.95))
    ok = out.dropna(subset=["lo80c"])
    assert len(ok) < len(out) and ok["origin"].iloc[0] > out["origin"].iloc[0]
    assert (ok["lo80c"] < ok["forecast"]).all() and (ok["forecast"] < ok["hi80c"]).all()
    assert (ok["lo95c"] <= ok["lo80c"]).all() and (ok["hi95c"] >= ok["hi80c"]).all()


def test_calibrated_coverage_is_roughly_nominal_on_iid_errors():
    rng = np.random.default_rng(1)
    n = 400
    origins = pd.period_range("1990-01", periods=n, freq="M")
    rows = pd.DataFrame({"model": "m", "h": 1, "origin": [p.strftime("%Y-%m") for p in origins],
                         "target": [(p + 1).strftime("%Y-%m") for p in origins],
                         "actual": 100 * np.exp(rng.normal(0, 0.01, n)), "forecast": 100.0})
    out = iv.add_calibrated_intervals(rows, (0.8,)).dropna(subset=["lo80c"])
    cov = np.mean((out["actual"] >= out["lo80c"]) & (out["actual"] <= out["hi80c"]))
    assert 0.74 <= cov <= 0.90
