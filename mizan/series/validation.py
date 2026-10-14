"""Data validation for the monthly CPI series.

Every check returns a `Check` so the same report is shown in the UI, written to
provenance.json and asserted in tests. Nothing is interpolated or repaired here -
problems are reported, never silently fixed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    status: str  # "pass" | "warn" | "fail"
    detail: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def expected_periods(first: pd.Timestamp, last: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(first, last, freq="MS")


def missing_periods(index: pd.DatetimeIndex) -> list[str]:
    if len(index) == 0:
        return []
    full = expected_periods(index.min(), index.max())
    return [d.strftime("%Y-%m") for d in full.difference(index)]


def validate_series(
    cpi: pd.Series,
    *,
    base_year: int = 2018,
    provenance: dict[str, Any] | None = None,
    csv_sha256: str | None = None,
) -> list[Check]:
    """Run all structural and provenance checks on a monthly CPI series."""
    checks: list[Check] = []

    def add(cid: str, label: str, ok: bool, detail: str, *, warn: bool = False) -> None:
        checks.append(Check(cid, label, "pass" if ok else ("warn" if warn else "fail"), detail))

    n = len(cpi)
    add("non_empty", "Series is not empty", n > 0, f"{n} observations")
    if n == 0:
        return checks

    idx = cpi.index
    add("datetime_index", "Index is a month-start DatetimeIndex",
        isinstance(idx, pd.DatetimeIndex) and bool((idx.day == 1).all()),
        "all periods fall on the first day of a month")
    add("sorted", "Periods are in chronological order", bool(idx.is_monotonic_increasing),
        "monotonic increasing")
    dup = int(idx.duplicated().sum())
    add("unique", "No duplicate periods", dup == 0, f"{dup} duplicate periods")
    miss = missing_periods(idx.drop_duplicates().sort_values())
    add("complete", "No missing months between first and last period", not miss,
        "0 missing months" if not miss else f"missing: {', '.join(miss[:12])}")
    nan = int(cpi.isna().sum())
    add("numeric", "All values are finite numbers", nan == 0 and bool(np.isfinite(cpi.to_numpy(float)).all()),
        f"{nan} missing / non-finite values")
    add("positive", "All index values are positive", bool((cpi > 0).all()),
        f"min = {cpi.min():.2f}")
    add("plausible_range", "Index values within a plausible range (30-300)",
        bool(cpi.between(30, 300).all()), f"range {cpi.min():.2f} - {cpi.max():.2f}")

    mom = 100 * (cpi / cpi.shift(1) - 1)
    big = mom.abs() > 5
    add("no_extreme_jumps", "No month-over-month change above 5% in absolute value",
        not bool(big.any()), f"largest |MoM| = {mom.abs().max():.2f}%", warn=True)

    base = cpi[cpi.index.year == base_year]
    if len(base) == 12:
        avg = float(base.mean())
        add("base_year", f"Base-year consistency: {base_year} average equals 100",
            abs(avg - 100.0) < 0.05, f"{base_year} average = {avg:.4f}")
    else:
        add("base_year", f"Base-year consistency: {base_year} average equals 100", False,
            f"{base_year} has {len(base)} months")

    if provenance is not None:
        prov_rows = provenance.get("series", {}).get("rows")
        add("prov_rows", "Row count matches provenance record", prov_rows == n,
            f"data {n} vs provenance {prov_rows}")
        prov_last = provenance.get("series", {}).get("last_period")
        add("prov_last", "Latest period matches provenance record",
            prov_last == idx.max().strftime("%Y-%m"), f"data {idx.max():%Y-%m} vs provenance {prov_last}")
        if csv_sha256 is not None:
            want = provenance.get("series", {}).get("csv_sha256")
            add("prov_checksum", "Series file SHA-256 matches provenance record", want == csv_sha256,
                f"{(csv_sha256 or '')[:16]}... vs {(want or '')[:16]}...")
    return checks


def summarize(checks: list[Check]) -> dict[str, Any]:
    return {
        "passed": sum(c.status == "pass" for c in checks),
        "warnings": sum(c.status == "warn" for c in checks),
        "failed": sum(c.status == "fail" for c in checks),
        "total": len(checks),
        "ok": all(c.status != "fail" for c in checks),
    }
