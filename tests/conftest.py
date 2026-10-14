"""Shared fixtures. Synthetic series here are TEST FIXTURES ONLY - the app never uses them."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from mizan.config import ExperimentConfig


def make_series(n: int = 72, start: str = "2010-01-01", growth: float = 0.002, seed: int = 0, noise: float = 0.002) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="MS")
    log = np.cumsum(growth + rng.normal(0, noise, n)) + np.log(90)
    return pd.Series(np.exp(log), index=idx, name="cpi")


@pytest.fixture()
def synth() -> pd.Series:
    return make_series()


@pytest.fixture()
def small_cfg() -> ExperimentConfig:
    return ExperimentConfig(horizons=(1, 3, 6), max_horizon=6, min_train=36, test_months=12, reselect_every=6)
