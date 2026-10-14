import numpy as np
import pandas as pd
import pytest

from mizan.series.transforms import average_inflation, mom_change, yoy_change


def _series(values, start="2024-01-01"):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="MS"))


def test_mom_formula_exact():
    s = _series([100.0, 101.0, 100.0])
    m = mom_change(s)
    assert np.isnan(m.iloc[0])
    assert m.iloc[1] == pytest.approx(1.0)
    assert m.iloc[2] == pytest.approx(100 * (100 / 101 - 1))


def test_yoy_formula_exact():
    s = _series([100.0] * 12 + [103.0, 99.0])
    y = yoy_change(s)
    assert y.iloc[:12].isna().all()
    assert y.iloc[12] == pytest.approx(3.0)
    assert y.iloc[13] == pytest.approx(-1.0)


def test_yoy_uses_same_calendar_month():
    s = _series(list(range(100, 124)))  # 100..123
    y = yoy_change(s)
    assert y.loc["2025-03-01"] == pytest.approx(100 * (s.loc["2025-03-01"] / s.loc["2024-03-01"] - 1))


def test_average_inflation_to_date():
    s = _series([100.0] * 12 + [110.0, 120.0])  # Jan-Feb 2025 avg 115 vs 100
    assert average_inflation(s, 2025, 2) == pytest.approx(15.0)


def test_average_inflation_requires_complete_window():
    s = _series([100.0] * 12 + [110.0])
    with pytest.raises(ValueError):
        average_inflation(s, 2025, 2)
