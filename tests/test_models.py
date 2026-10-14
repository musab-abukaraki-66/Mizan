import numpy as np
import pandas as pd
import pytest

from mizan.forecasting.models import MODELS, Drift, ModelFitError, Naive, SeasonalNaive
from tests.conftest import make_series

LEVELS = (0.8, 0.95)


def _state():
    return {"spec": None, "reselect_every": 1}


@pytest.mark.parametrize("model_id", list(MODELS))
def test_horizon_length_and_interval_ordering(model_id):
    s = make_series(n=96, seed=3)
    for h in (1, 3, 6):
        fc = MODELS[model_id].forecast(s, h, LEVELS, _state())
        assert len(fc.mean) == h
        for lv in LEVELS:
            assert len(fc.lower[lv]) == h and len(fc.upper[lv]) == h
            assert np.all(fc.lower[lv] <= fc.mean + 1e-9) and np.all(fc.mean <= fc.upper[lv] + 1e-9)
        assert np.all(fc.lower[0.95] <= fc.lower[0.8] + 1e-9)
        assert np.all(fc.upper[0.95] >= fc.upper[0.8] - 1e-9)
        assert np.all(np.isfinite(fc.mean))


@pytest.mark.parametrize("model_id", ["naive", "drift", "ets", "sarima"])
def test_intervals_widen_with_horizon(model_id):
    s = make_series(n=96, seed=4)
    fc = MODELS[model_id].forecast(s, 6, LEVELS, _state())
    width = fc.upper[0.95] - fc.lower[0.95]
    assert width[-1] > width[0]


def test_naive_is_last_value():
    s = make_series(n=40)
    fc = Naive().forecast(s, 4, LEVELS, _state())
    assert np.allclose(fc.mean, s.iloc[-1])


def test_seasonal_naive_repeats_last_year():
    s = make_series(n=40)
    fc = SeasonalNaive().forecast(s, 6, LEVELS, _state())
    assert np.allclose(fc.mean, s.iloc[-12:-6].to_numpy())


def test_drift_recovers_constant_growth():
    idx = pd.date_range("2015-01-01", periods=60, freq="MS")
    s = pd.Series(100 * np.exp(0.003 * np.arange(60)), index=idx)
    # noise-free series: sigma would be ~0 -> add tiny jitter so interval scaling is defined
    s = s * (1 + 1e-6 * np.sin(np.arange(60)))
    fc = Drift().forecast(s, 3, LEVELS, _state())
    expected = s.iloc[-1] * np.exp(0.003 * np.arange(1, 4))
    assert np.allclose(fc.mean, expected, rtol=1e-3)


@pytest.mark.parametrize("model_id", list(MODELS))
def test_insufficient_history_raises_clean_error(model_id):
    s = make_series(n=10)
    with pytest.raises(ModelFitError):
        MODELS[model_id].forecast(s, 3, LEVELS, _state())


def test_invalid_values_raise_clean_error():
    s = make_series(n=60)
    s.iloc[5] = -1.0
    with pytest.raises(ModelFitError):
        Naive().forecast(s, 2, LEVELS, _state())


def test_forecast_does_not_depend_on_data_after_origin():
    """Forecasts use only the series passed in; corrupting 'future' values appended later cannot change them."""
    s = make_series(n=90, seed=5)
    train = s.iloc[:72]
    base = {m: MODELS[m].forecast(train, 6, LEVELS, _state()).mean for m in ("naive", "drift", "ets", "sarima")}
    corrupted = s.copy()
    corrupted.iloc[72:] = corrupted.iloc[72:] * 5.0
    train2 = corrupted.iloc[:72]
    for m in base:
        assert np.array_equal(base[m], MODELS[m].forecast(train2, 6, LEVELS, _state()).mean)
