"""Metrics checked against independently calculated expected values on small fixed fixtures."""

import math

import numpy as np
import pandas as pd
import pytest

from mizan.forecasting import metrics as mx


def _block():
    # actual vs forecast: errors (f - a) = +1, -2, +3, 0
    return pd.DataFrame({
        "actual": [100.0, 102.0, 104.0, 106.0], "forecast": [101.0, 100.0, 107.0, 106.0],
        "lo80": [99.0, 99.0, 100.0, 103.0], "hi80": [102.0, 103.0, 106.0, 109.0],
        "lo95": [98.0, 97.0, 99.0, 102.0], "hi95": [103.0, 104.0, 108.0, 110.0],
        "yoy_actual": [2.0, 2.0, 2.0, 2.0], "yoy_forecast": [3.0, 0.0, 5.0, 2.0],
    })


def test_accuracy_matches_hand_calculation():
    m = mx.accuracy(_block(), scale=2.0)
    assert m["n"] == 4
    assert m["mae"] == pytest.approx((1 + 2 + 3 + 0) / 4)  # 1.5
    assert m["rmse"] == pytest.approx(math.sqrt((1 + 4 + 9 + 0) / 4))
    assert m["mase"] == pytest.approx(1.5 / 2.0)
    assert m["bias"] == pytest.approx((1 - 2 + 3 + 0) / 4)
    assert m["mape_pct"] == pytest.approx(100 * np.mean([1 / 100, 2 / 102, 3 / 104, 0]))
    assert m["yoy_mae_pp"] == pytest.approx((1 + 2 + 3 + 0) / 4)
    assert m["yoy_rmse_pp"] == pytest.approx(math.sqrt((1 + 4 + 9 + 0) / 4))


def test_coverage_and_width():
    m = mx.accuracy(_block(), scale=1.0)
    # actuals 100,102,104,106 inside 80% bands [99,102],[99,103],[100,106],[103,109]: all four
    assert m["coverage80"] == pytest.approx(1.0)
    # 95% bands: [98,103] ok, [97,104] ok, [99,108] ok, [102,110] ok
    assert m["coverage95"] == pytest.approx(1.0)
    assert m["width80"] == pytest.approx(np.mean([3, 4, 6, 6]))
    b = _block()
    b.loc[0, ["lo80", "hi80"]] = [101.0, 102.0]  # actual 100 now outside
    assert mx.accuracy(b, 1.0)["coverage80"] == pytest.approx(0.75)


def test_mase_scale_is_in_sample_naive_mae():
    assert mx.mase_scale(np.array([10.0, 12.0, 11.0, 15.0])) == pytest.approx((2 + 1 + 4) / 3)
    with pytest.raises(ValueError):
        mx.mase_scale(np.array([5.0, 5.0, 5.0]))
    with pytest.raises(ValueError):
        mx.mase_scale(np.array([5.0]))


def test_empty_block():
    assert mx.accuracy(_block().iloc[0:0], 1.0) == {"n": 0}


def test_dm_equal_forecasts_has_no_power():
    e = np.array([1.0, -2, 3, -1, 2, -3, 1, 2, -1, 1])
    assert mx.diebold_mariano(e, e, 1) is None  # identical errors: zero variance, test undefined


def test_dm_hand_calculated_h1():
    e1 = np.array([1.0, 2, 1, 3, 2, 1, 2, 3, 1, 2])
    e2 = np.array([2.0, 3, 2, 4, 3, 2, 4, 5, 2, 3])
    d = e1**2 - e2**2
    dbar, n = d.mean(), len(d)
    var = np.var(d)  # h=1: population variance (denominator n)
    hln = math.sqrt((n + 1 - 2 + 0) / n)
    expected = hln * dbar / math.sqrt(var / n)
    out = mx.diebold_mariano(e1, e2, 1)
    assert out["stat"] == pytest.approx(expected)
    assert out["stat"] < 0 and out["p_value"] < 0.01  # model 1 clearly better
    assert out["n"] == 10


def test_dm_requires_enough_observations():
    assert mx.diebold_mariano(np.ones(5), np.zeros(5), 1) is None
    assert mx.diebold_mariano(np.arange(10.0), np.arange(10.0) + 1, 6) is None  # n < 2h
