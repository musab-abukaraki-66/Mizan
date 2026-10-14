"""Time-based split correctness and leakage prevention."""

import numpy as np
import pandas as pd
import pytest

from mizan.config import ExperimentConfig
from mizan.forecasting import backtest as bt
from tests.conftest import make_series

CFG = ExperimentConfig(horizons=(1, 3, 6), max_horizon=6, min_train=36, test_months=12, reselect_every=6)


def test_origins_start_after_min_train_and_leave_room_for_a_target():
    n = 80
    o = bt.origin_indices(n, CFG)
    assert o[0] == CFG.min_train - 1 and o[-1] == n - 2
    assert o == sorted(set(o))


def test_dev_and_test_windows_partition_targets():
    n = 80
    for h in (1, 3, 6):
        sp = bt.split_origins(n, CFG, h)
        dev_t = {t + h for t in sp["dev"]}
        test_t = {t + h for t in sp["test"]}
        assert not dev_t & test_t
        assert max(dev_t) < n - CFG.test_months <= min(test_t)
        assert max(test_t) == n - 1  # last observation is a test target
        assert len(test_t) == CFG.test_months


def test_rows_respect_chronology_and_windows():
    s = make_series(n=72, seed=1)
    res = bt.backtest_model("drift", s, CFG)
    r = res.rows
    assert (pd.to_datetime(r["origin"]) < pd.to_datetime(r["target"])).all()
    months_ahead = (pd.to_datetime(r["target"]).dt.year * 12 + pd.to_datetime(r["target"]).dt.month) - (
        pd.to_datetime(r["origin"]).dt.year * 12 + pd.to_datetime(r["origin"]).dt.month)
    assert (months_ahead == r["h"]).all()
    cutoff = s.index[len(s) - CFG.test_months].strftime("%Y-%m")
    assert (r.loc[r["window"] == "test", "target"] >= cutoff).all()
    assert (r.loc[r["window"] == "dev", "target"] < cutoff).all()
    assert r["origin"].min() == s.index[CFG.min_train - 1].strftime("%Y-%m")


def test_actuals_match_the_series():
    s = make_series(n=60, seed=2)
    r = bt.backtest_model("naive", s, CFG).rows
    lookup = {d.strftime("%Y-%m"): v for d, v in s.items()}
    assert np.allclose(r["actual"], [lookup[t] for t in r["target"]])


def test_naive_backtest_forecast_equals_origin_value():
    s = make_series(n=60, seed=2)
    r = bt.backtest_model("naive", s, CFG).rows
    lookup = {d.strftime("%Y-%m"): v for d, v in s.items()}
    assert np.allclose(r["forecast"], [lookup[o] for o in r["origin"]])


@pytest.mark.parametrize("model_id", ["naive", "drift", "seasonal_naive", "ets"])
def test_no_leakage_future_changes_do_not_alter_earlier_forecasts(model_id):
    """Rewriting every observation after month k must leave all forecasts made at origins <= k unchanged."""
    s = make_series(n=66, seed=7)
    k = 50
    mutated = s.copy()
    mutated.iloc[k + 1:] = mutated.iloc[k + 1:] * 3.0
    a = bt.backtest_model(model_id, s, CFG).rows
    b = bt.backtest_model(model_id, mutated, CFG).rows
    cut = s.index[k].strftime("%Y-%m")
    a_early, b_early = a[a["origin"] <= cut], b[b["origin"] <= cut]
    assert len(a_early) == len(b_early) > 0
    assert np.array_equal(a_early["forecast"].to_numpy(), b_early["forecast"].to_numpy())
    assert np.array_equal(a_early["lo80"].to_numpy(), b_early["lo80"].to_numpy())


def test_yoy_columns_use_observed_reference_month():
    s = make_series(n=60, seed=2)
    r = bt.backtest_model("naive", s, CFG).rows
    lookup = {d.strftime("%Y-%m"): v for d, v in s.items()}
    row = r.iloc[10]
    ref_period = (pd.Period(row["target"]) - 12).strftime("%Y-%m")
    assert row["yoy_actual"] == pytest.approx(100 * (row["actual"] / lookup[ref_period] - 1))
    assert row["yoy_forecast"] == pytest.approx(100 * (row["forecast"] / lookup[ref_period] - 1))


def test_model_failures_are_recorded_not_hidden():
    s = make_series(n=40, seed=2)  # too short for some models at early origins
    cfg = ExperimentConfig(min_train=14, test_months=6)
    res = bt.backtest_model("seasonal_naive", s, cfg)
    assert res.failures and all("reason" in f for f in res.failures)
    assert res.n_origins == len(bt.origin_indices(len(s), cfg))
