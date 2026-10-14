"""Ingest the headline monthly CPI (2018=100) from the Jordan Department of Statistics.

DoS publishes one workbook per calendar year on its "Tables of price indices" page.
Each workbook has an "All Items" row with the 12 monthly index values and a
yearly "Average" column. Since 2006 the whole history is published on the same
2018=100 base, so no splicing is performed here.

Parsing is done by header text (month names), never by fixed column position, and
every year is checked against DoS's own Average column.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import openpyxl
import pandas as pd

from mizan import config

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


@dataclass
class WorkbookParse:
    year: int
    sheet: str
    title_en: str
    values: dict[int, float]  # month number (1-12) -> index
    average: float | None
    notes: list[str] = field(default_factory=list)


def _clean(cell: Any) -> str:
    return str(cell).replace("\xa0", " ").strip().lower() if cell is not None else ""


def parse_workbook(path: Path, year: int) -> WorkbookParse:
    """Extract the All-Items monthly series from one DoS yearly workbook."""
    wb = openpyxl.load_workbook(path, data_only=True, read_only=False)
    ws = wb.worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]

    title_en = ""
    for r in rows[:4]:
        for c in r:
            if isinstance(c, str) and "consumer price" in c.lower() and "monthly" in c.lower() and c.isascii():
                title_en = c.strip()
    month_cols: dict[int, int] = {}
    avg_col: int | None = None
    header_row = None
    for i, r in enumerate(rows[:12]):
        cleaned = [_clean(c) for c in r]
        hits = {m: j for j, c in enumerate(cleaned) for m, name in enumerate(MONTHS, 1) if c.startswith(name)}
        if len(hits) == 12:
            month_cols, header_row = hits, i
            for j, c in enumerate(cleaned):
                if c.startswith("average"):
                    avg_col = j
            break
    if header_row is None:
        raise ValueError(f"{path.name}: could not find the month header row")

    item_row = None
    for r in rows[header_row + 1 : header_row + 8]:
        if any("all items" in _clean(c) for c in r):
            item_row = r
            break
    if item_row is None:
        raise ValueError(f"{path.name}: could not find the 'All Items' row")

    values: dict[int, float] = {}
    for m, j in month_cols.items():
        v = item_row[j] if j < len(item_row) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            values[m] = float(v)
    average = item_row[avg_col] if avg_col is not None and isinstance(item_row[avg_col], (int, float)) else None

    notes: list[str] = []
    if "2018=100" not in title_en.replace(" ", ""):
        notes.append(f"title does not state the 2018=100 base: {title_en!r}")
    if str(year) not in title_en:
        notes.append(f"title names a different year than the file ({title_en!r}); year taken from the file name/URL")
    return WorkbookParse(year, ws.title, title_en, values, float(average) if average is not None else None, notes)


def download_year(year: int, dest: Path, *, retries: int = 5, client: httpx.Client | None = None) -> dict[str, Any]:
    """Download one yearly workbook (with retries - the DoS host sometimes resets connections)."""
    url = config.DOS_FILE_URL.format(year=year)
    dest.parent.mkdir(parents=True, exist_ok=True)
    own = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "MIZAN-research-demo/1.0"})
    last_err: Exception | None = None
    try:
        for attempt in range(1, retries + 1):
            try:
                resp = client.get(url)
                resp.raise_for_status()
                body = resp.content
                if not body.startswith(b"PK"):
                    raise ValueError("response is not an .xlsx (zip) file")
                dest.write_bytes(body)
                return {
                    "year": year,
                    "url": url,
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "http_last_modified": resp.headers.get("last-modified"),
                }
            except Exception as exc:  # noqa: BLE001 - retried, then re-raised below
                last_err = exc
                time.sleep(min(2.0 * attempt, 8.0))
    finally:
        if own:
            client.close()
    raise RuntimeError(f"could not download {url}: {last_err}")


def describe_file(year: int, path: Path) -> dict[str, Any]:
    body = path.read_bytes()
    return {"year": year, "url": config.DOS_FILE_URL.format(year=year), "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(), "http_last_modified": None}


def check_average(parse: WorkbookParse, tol: float = 0.01) -> dict[str, Any]:
    """Compare mean of the monthly values to DoS's own published Average column."""
    if parse.average is None or not parse.values:
        return {"checked": False, "ok": None}
    mean = sum(parse.values.values()) / len(parse.values)
    return {"checked": True, "ok": abs(mean - parse.average) <= tol, "mean_of_months": mean,
            "published_average": parse.average, "abs_diff": abs(mean - parse.average),
            "months": len(parse.values)}


def build_series(parses: list[WorkbookParse]) -> pd.DataFrame:
    rows = []
    for p in sorted(parses, key=lambda x: x.year):
        months = sorted(p.values)
        if months and months != list(range(1, months[-1] + 1)):
            raise ValueError(f"{p.year}: months are not contiguous from January: {months}")
        for m in months:
            rows.append((f"{p.year}-{m:02d}", p.values[m]))
    df = pd.DataFrame(rows, columns=["period", "cpi"])
    return df


def current_year() -> int:
    return datetime.now(timezone.utc).year
