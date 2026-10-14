import numpy as np
import pandas as pd

from mizan.series.validation import missing_periods, summarize, validate_series


def _full(n=36, start="2017-01-01"):
    return pd.Series(np.linspace(95, 105, n), index=pd.date_range(start, periods=n, freq="MS"))


def _status(checks, cid):
    return next(c.status for c in checks if c.id == cid)


def test_clean_series_has_no_failures():
    s = pd.Series(100 + np.arange(36) * 0.1, index=pd.date_range("2017-01-01", periods=36, freq="MS"))
    s[s.index.year == 2018] = 100.0
    assert summarize(validate_series(s))["ok"]


def test_detects_missing_month():
    s = _full().drop(pd.Timestamp("2018-03-01"))
    checks = validate_series(s)
    assert _status(checks, "complete") == "fail"
    assert missing_periods(s.index) == ["2018-03"]


def test_detects_duplicate_period():
    s = _full()
    s = pd.concat([s, s.iloc[[5]]]).sort_index()
    assert _status(validate_series(s), "unique") == "fail"


def test_detects_unsorted_index():
    s = _full().iloc[::-1]
    assert _status(validate_series(s), "sorted") == "fail"


def test_detects_non_finite_and_non_positive():
    s = _full()
    s.iloc[3] = np.nan
    assert _status(validate_series(s), "numeric") == "fail"
    s2 = _full()
    s2.iloc[3] = -1.0
    assert _status(validate_series(s2), "positive") == "fail"


def test_detects_mid_month_dates():
    s = _full()
    s.index = s.index + pd.Timedelta(days=14)
    assert _status(validate_series(s), "datetime_index") == "fail"


def test_base_year_mismatch_fails():
    s = _full()
    s[s.index.year == 2018] = 110.0
    assert _status(validate_series(s), "base_year") == "fail"


def test_extreme_jump_is_a_warning_not_a_failure():
    s = _full()
    s.iloc[20:] = s.iloc[20:] * 1.2
    checks = validate_series(s)
    assert _status(checks, "no_extreme_jumps") == "warn"


def test_provenance_mismatch_detected():
    s = _full()
    prov = {"series": {"rows": 99, "last_period": "2000-01", "csv_sha256": "abc"}}
    checks = validate_series(s, provenance=prov, csv_sha256="def")
    assert _status(checks, "prov_rows") == "fail"
    assert _status(checks, "prov_last") == "fail"
    assert _status(checks, "prov_checksum") == "fail"


def test_empty_series():
    assert validate_series(pd.Series(dtype=float, index=pd.DatetimeIndex([])))[0].status == "fail"
