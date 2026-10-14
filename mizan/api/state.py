"""Loads (and caches by file modification time) the series, provenance and results bundle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from mizan import config
from mizan.forecasting import pipeline
from mizan.series.loader import load_cpi, load_provenance, sha256_file
from mizan.series.transforms import average_inflation, mom_change, yoy_change
from mizan.series.validation import Check, summarize, validate_series


class ResultsUnavailable(RuntimeError):
    pass


@dataclass
class AppState:
    cpi: pd.Series
    mom: pd.Series
    yoy: pd.Series
    provenance: dict[str, Any]
    results: dict[str, Any] | None
    results_fresh: bool
    checks: list[Check]
    csv_sha256: str

    @property
    def last_period(self) -> str:
        return self.cpi.index[-1].strftime("%Y-%m")


_cache: dict[str, Any] = {"key": None, "state": None}


def _key() -> tuple:
    def mt(p):
        return p.stat().st_mtime_ns if p.exists() else None

    return (mt(config.SERIES_CSV), mt(config.PROVENANCE_JSON), mt(config.RESULTS_JSON))


def get_state(force: bool = False) -> AppState:
    key = _key()
    if not force and _cache["key"] == key and _cache["state"] is not None:
        return _cache["state"]
    cpi = load_cpi()
    prov = load_provenance()
    sha = sha256_file(config.SERIES_CSV)
    checks = validate_series(cpi, provenance=prov, csv_sha256=sha)
    results = None
    fresh = False
    if config.RESULTS_JSON.exists():
        results = pipeline.load_results()
        fresh = pipeline.results_are_fresh()
    st = AppState(cpi, mom_change(cpi), yoy_change(cpi), prov, results, fresh, checks, sha)
    _cache.update(key=key, state=st)
    return st


def require_results(st: AppState) -> dict[str, Any]:
    if st.results is None:
        raise ResultsUnavailable("Forecast results have not been built. Run: python -m mizan backtest")
    return st.results


def latest_snapshot(st: AppState) -> dict[str, Any]:
    last = st.cpi.index[-1]
    ytd = average_inflation(st.cpi, last.year, last.month) if len(st.cpi[st.cpi.index.year == last.year - 1]) >= last.month else None
    prev = st.cpi.index[-2]
    return {
        "period": last.strftime("%Y-%m"),
        "cpi": float(st.cpi.iloc[-1]),
        "mom": float(st.mom.iloc[-1]),
        "yoy": float(st.yoy.iloc[-1]),
        "yoy_prev": float(st.yoy.iloc[-2]),
        "prev_period": prev.strftime("%Y-%m"),
        "avg_to_date": ytd,
        "avg_to_date_months": last.month,
        "cpi_12m_ago": float(st.cpi.iloc[-13]),
        "validation": summarize(st.checks),
    }
