"""Independent verification of the DoS series.

1. IMF CPI dataset (IMF.STA:CPI) - independent transmission of the same national series.
   Used for comparison only; IMF data is NOT bundled (IMF terms restrict systematic redistribution).
2. Figures stated in the Department of Statistics' own press release (as reported by QNA).
3. Re-basing diagnostics: pre-2018 values vs the legacy 2010=100 workbooks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import openpyxl
import pandas as pd

from mizan.series.transforms import average_inflation, mom_change, yoy_change

IMF_URL = "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI/JOR.CPI._T.IX.M?startPeriod=2006-01"
IMF_DATASET_URL = "https://data.imf.org/datasets/IMF.STA%3ACPI"

PRESS_SOURCE = {
    "name": "QNA, reporting the Jordan Department of Statistics release of 2026-10-12",
    "url": "https://qna.org.qa/en/News-Area/News/2026-10/12/jordans-inflation-rises-226-percent-since-start-of-2026",
    "retrieved": "2026-10-14",
}
# Statements copied from the article above (Sept-2026 CPI release).
PRESS_STATEMENTS = [
    {"id": "yoy_2026_09", "text": "annual inflation rate in September 2026", "stated": 2.73},
    {"id": "mom_2026_09", "text": "inflation in September compared to August", "stated": 0.16},
    {"id": "avg_2026_jan_sep", "text": "inflation in the first nine months vs the same period of 2025", "stated": 2.26},
]


def imf_crosscheck(cpi: pd.Series, client: httpx.Client | None = None) -> dict[str, Any]:
    """Compare the DoS series with the IMF CPI series for Jordan (overlapping months)."""
    own = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True)
    try:
        resp = client.get(IMF_URL, headers={"Accept": "application/json"})
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if own:
            client.close()
    series = next(iter(payload["dataSets"][0]["series"].values()))
    periods = [v["id"] for v in payload["structure"]["dimensions"]["observation"][0]["values"]]
    imf: dict[str, float] = {}
    for k, obs in series["observations"].items():
        val = obs[0]
        if val is not None:
            y, m = periods[int(k)].split("-M")
            imf[f"{y}-{m}"] = float(val)
    dos = {d.strftime("%Y-%m"): float(v) for d, v in cpi.items()}
    common = sorted(set(imf) & set(dos))
    diffs = [abs(imf[p] - dos[p]) for p in common]
    mismatched = [{"period": p, "dos": round(dos[p], 3), "imf": round(imf[p], 3), "diff": round(dos[p] - imf[p], 3)}
                  for p in common if abs(imf[p] - dos[p]) > 0.01]
    imf_2018 = [v for p, v in imf.items() if p.startswith("2018-")]
    return {
        "dataset": "IMF.STA:CPI (Consumer Price Index), Jordan, headline, index, monthly",
        "dataset_url": IMF_DATASET_URL,
        "api_url": IMF_URL,
        "overlap_months": len(common),
        "imf_first": min(imf), "imf_last": max(imf),
        "max_abs_diff": max(diffs) if diffs else None,
        "mean_abs_diff": sum(diffs) / len(diffs) if diffs else None,
        "months_with_diff_above_0_01": len(mismatched),
        "mismatched_months": mismatched,
        "imf_2018_average": sum(imf_2018) / len(imf_2018) if len(imf_2018) == 12 else None,
        "dos_2018_average": sum(v for p, v in dos.items() if p.startswith("2018-")) / 12,
        "ok": bool(diffs) and not mismatched,
        "dos_months_not_in_imf": [p for p in sorted(dos) if p not in imf][:12],
    }


def press_crosscheck(cpi: pd.Series) -> dict[str, Any]:
    """Recompute the headline statistics in the DoS release from the series and compare."""
    last = cpi.index.max()
    computed = {
        "yoy_2026_09": float(yoy_change(cpi).loc[last]),
        "mom_2026_09": float(mom_change(cpi).loc[last]),
        "avg_2026_jan_sep": average_inflation(cpi, last.year, last.month),
    }
    results = []
    for s in PRESS_STATEMENTS:
        val = computed[s["id"]]
        results.append({**s, "computed": round(val, 4), "ok": bool(abs(round(val, 2) - s["stated"]) < 1e-9)})
    return {"source": PRESS_SOURCE, "reference_month": last.strftime("%Y-%m"),
            "results": results, "ok": all(r["ok"] for r in results)}


def _parse_all_items(path: Path) -> list[float]:
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    for r in ws.iter_rows(values_only=True):
        if any(isinstance(c, str) and "All Items" in c for c in r):
            nums = [c for c in r if isinstance(c, (int, float)) and not isinstance(c, bool)]
            return [float(x) for x in nums[1:13]]
    raise ValueError(f"no All Items row in {path.name}")


def rebase_diagnostics(raw_2010_dir: Path, cpi: pd.Series) -> dict[str, Any]:
    """Compare 2018=100 values with the legacy 2010=100 workbooks for 2017 and 2018.

    2017: the 2018=100 series is a constant-factor rescale of the 2010=100 series.
    2018: DoS introduced a new basket - the ratio is NOT constant (a one-time link at Jan 2018).
    """
    out: dict[str, Any] = {"files": {}, "note": ""}
    for year in (2017, 2018):
        legacy = _parse_all_items(raw_2010_dir / f"{year}_2010base.xlsx")
        new = [float(cpi.loc[f"{year}-{m:02d}-01"]) for m in range(1, 13)]
        ratio = [n / o for n, o in zip(new, legacy)]
        out["files"][str(year)] = {
            "ratio_min": min(ratio), "ratio_max": max(ratio),
            "relative_spread_pct": 100 * (max(ratio) - min(ratio)) / (sum(ratio) / len(ratio)),
        }
    out["jan_2018_mom_pct_2018base"] = float(mom_change(cpi).loc["2018-01-01"])
    dec17_old = _parse_all_items(raw_2010_dir / "2017_2010base.xlsx")[-1]
    jan18_old = _parse_all_items(raw_2010_dir / "2018_2010base.xlsx")[0]
    out["jan_2018_mom_pct_2010base"] = 100 * (jan18_old / dec17_old - 1)
    out["note"] = (
        "Values before 2018 are the legacy 2010=100 series rescaled by DoS with one constant factor; "
        "from January 2018 DoS uses a new basket. The Dec-2017 to Jan-2018 change therefore contains a "
        "one-time link between two baskets and should not be read as a pure price movement."
    )
    return out
