"""Index-to-inflation transforms. Formulas are the ones documented in docs/METHODOLOGY.md."""

from __future__ import annotations

import pandas as pd


def mom_change(cpi: pd.Series) -> pd.Series:
    """Month-over-month % change: 100 * (CPI_t / CPI_(t-1) - 1)."""
    return 100.0 * (cpi / cpi.shift(1) - 1.0)


def yoy_change(cpi: pd.Series) -> pd.Series:
    """Year-over-year % change: 100 * (CPI_t / CPI_(t-12) - 1)."""
    return 100.0 * (cpi / cpi.shift(12) - 1.0)


def average_inflation(cpi: pd.Series, year: int, through_month: int) -> float:
    """Average-to-date inflation: mean(CPI, Jan..m of `year`) vs the same months of year-1, in %.

    This is the "first N months" measure used in Department of Statistics press releases.
    """
    cur = cpi[(cpi.index.year == year) & (cpi.index.month <= through_month)]
    prev = cpi[(cpi.index.year == year - 1) & (cpi.index.month <= through_month)]
    if len(cur) != through_month or len(prev) != through_month:
        raise ValueError("incomplete data for the requested average-to-date window")
    return 100.0 * (cur.mean() / prev.mean() - 1.0)
