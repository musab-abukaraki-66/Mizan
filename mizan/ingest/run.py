"""Orchestrates ingestion: download -> parse -> validate -> write series + provenance."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from mizan import config
from mizan.ingest import crosscheck, dos_cpi
from mizan.series.loader import sha256_file
from mizan.series.validation import summarize, validate_series

LEGACY_URL = "https://dosweb.dos.gov.jo/DataBank/Economic/Price_Indices/CPI/2010/{year}.xlsx"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _json_default(o: Any) -> Any:
    if hasattr(o, "item"):  # numpy scalar
        return o.item()
    raise TypeError(f"not JSON serializable: {type(o).__name__}")


def run(*, download: bool = True, crosschecks: bool = True) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    last_year = dos_cpi.current_year()
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    file_records: list[dict[str, Any]] = []
    parses: list[dos_cpi.WorkbookParse] = []

    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "MIZAN-research-demo/1.0"}) as client:
        for year in range(config.FIRST_YEAR, last_year + 1):
            path = config.RAW_DIR / f"{year}.xlsx"
            if download or not path.exists():
                _log(f"downloading {year} ...")
                try:
                    rec = dos_cpi.download_year(year, path, client=client)
                except RuntimeError as exc:
                    if year == last_year and year > config.FIRST_YEAR:  # new year's workbook not published yet
                        _log(f"{year}: not available yet ({exc}) - continuing with earlier years")
                        continue
                    raise
            else:
                rec = dos_cpi.describe_file(year, path)
            parse = dos_cpi.parse_workbook(path, year)
            rec.update({"sheet": parse.sheet, "title_en": parse.title_en, "notes": parse.notes,
                        "months_found": len(parse.values), "average_check": dos_cpi.check_average(parse)})
            file_records.append(rec)
            parses.append(parse)

        df = dos_cpi.build_series(parses)
        config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(config.SERIES_CSV, index=False, lineterminator="\n")
        csv_hash = sha256_file(config.SERIES_CSV)

        idx = pd.to_datetime(df["period"] + "-01")
        cpi = pd.Series(df["cpi"].to_numpy(float), index=pd.DatetimeIndex(idx, freq="MS"), name="cpi")

        cross: dict[str, Any] = {}
        if crosschecks:
            try:
                cross["imf"] = crosscheck.imf_crosscheck(cpi, client)
            except Exception as exc:  # noqa: BLE001 - reported, not fatal
                cross["imf"] = {"error": str(exc), "ok": None}
            cross["press_release"] = crosscheck.press_crosscheck(cpi)
            legacy_dir = config.RAW_DIR / "legacy"
            legacy_dir.mkdir(exist_ok=True)
            try:
                for y in (2017, 2018):
                    p = legacy_dir / f"{y}_2010base.xlsx"
                    if download or not p.exists():
                        r = client.get(LEGACY_URL.format(year=y))
                        r.raise_for_status()
                        p.write_bytes(r.content)
                cross["rebase"] = crosscheck.rebase_diagnostics(legacy_dir, cpi)
            except Exception as exc:  # noqa: BLE001
                cross["rebase"] = {"error": str(exc)}

    if not download:  # report when the raw files were actually fetched, not when they were re-parsed
        newest = max(Path(config.RAW_DIR / f"{r['year']}.xlsx").stat().st_mtime for r in file_records)
        now = datetime.fromtimestamp(newest, timezone.utc).replace(microsecond=0)
    prov: dict[str, Any] = {
        "schema_version": 1,
        "project": "MIZAN",
        "source": {
            "publisher": "Jordan Department of Statistics (DoS)",
            "publisher_ar": "دائرة الإحصاءات العامة - الأردن",
            "dataset": "Monthly Consumer Price Index (2018=100) - Tables of price indices",
            "landing_page": config.DOS_PAGE_URL,
            "file_url_pattern": config.DOS_FILE_URL,
            "terms_url": "https://dosweb.dos.gov.jo/terms-conditions/",
        },
        "retrieval": {"retrieved_at_utc": now.isoformat().replace("+00:00", "Z"),
                      "command": "python -m mizan ingest" + ("" if download else " --from-raw"), "files": file_records},
        "series": {
            "name": "Consumer Price Index, all items (headline)",
            "definition": "Monthly index of the prices of the DoS consumer basket (~850 items); not 'the cost of living'.",
            "frequency": "monthly",
            "base": "2018 = 100 (annual average of 2018 equals 100)",
            "units": "index points",
            "seasonal_adjustment": "Not stated by DoS; treated as not seasonally adjusted.",
            "geography": "Jordan (Kingdom level)",
            "rows": len(df),
            "first_period": df["period"].iloc[0],
            "last_period": df["period"].iloc[-1],
            "missing_periods": [],
            "csv": str(config.SERIES_CSV.relative_to(config.ROOT)).replace("\\", "/"),
            "csv_sha256": csv_hash,
            "transformations": [
                "Extracted the 'All Items' row of each yearly DoS workbook (months located by header text).",
                "No interpolation, smoothing, seasonal adjustment or gap filling.",
                "Values kept at full published precision.",
            ],
        },
        "license": {
            "dos": "DoS Terms & Conditions state its information is subject to intellectual-property (copyright) law "
                   "'unless noted otherwise' and give no open licence. Only the extracted headline series (index values, "
                   "with attribution) is included for non-commercial research/demonstration; the raw DoS workbooks are "
                   "NOT redistributed (checksums recorded instead). Rights remain with DoS.",
            "imf": "IMF series used only for comparison and not redistributed (IMF terms: no systematic redistribution).",
        },
        "crosschecks": cross,
    }
    checks = validate_series(cpi, provenance=None)
    avg_fail = [r["year"] for r in file_records if r["average_check"].get("ok") is False]
    from mizan.series.validation import Check
    checks.append(Check("dos_average_column", "Monthly values reproduce DoS's published yearly Average column",
                        "pass" if not avg_fail else "fail",
                        f"{sum(bool(r['average_check'].get('checked')) for r in file_records)} yearly workbooks checked"
                        + (f"; mismatches in {avg_fail}" if avg_fail else "; all match within 0.01")))
    if "imf" in cross and cross["imf"].get("overlap_months"):
        c = cross["imf"]
        bad = c["mismatched_months"]
        if not bad:
            status, detail = "pass", f"{c['overlap_months']} overlapping months, all within 0.01 index points"
        else:
            span = f"{bad[0]['period']}..{bad[-1]['period']}"
            status = "warn"
            mar = next((m for m in bad if m["period"] == "2018-03"), None)
            detail = (f"{c['overlap_months'] - len(bad)} of {c['overlap_months']} overlapping months match within 0.01; "
                      f"{len(bad)} differ, all in {span} (max |diff| {max(abs(m['diff']) for m in bad):.2f}"
                      + (f", Mar-2018: DoS {mar['dos']} vs IMF {mar['imf']}" if mar else "")
                      + "). Both series average 100 in 2018, so only the within-year profile differs; the cause was "
                      "not determined. DoS workbooks are used (they reproduce DoS's own Average column and the latest release).")
        checks.append(Check("imf_crosscheck", "Compared with the IMF CPI dataset (independent transmission)", status, detail))
    if "press_release" in cross:
        c = cross["press_release"]
        checks.append(Check("press_crosscheck", "Reproduces the headline figures in the latest DoS release",
                            "pass" if c["ok"] else "fail",
                            "; ".join(f"{r['id']}: {r['computed']:.2f} vs {r['stated']}" for r in c["results"])))
    prov["validation"] = {"summary": summarize(checks), "checks": [c.as_dict() for c in checks]}
    with open(config.PROVENANCE_JSON, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(prov, fh, indent=2, ensure_ascii=False, default=_json_default)
        fh.write("\n")
    _log(f"wrote {config.SERIES_CSV} ({len(df)} rows, last {df['period'].iloc[-1]}) and {config.PROVENANCE_JSON}")
    return prov


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Download and verify the DoS monthly CPI series")
    ap.add_argument("--from-raw", action="store_true", help="re-use already downloaded workbooks in data/raw")
    ap.add_argument("--skip-crosschecks", action="store_true", help="skip IMF / press-release / legacy checks")
    args = ap.parse_args(argv)
    prov = run(download=not args.from_raw, crosschecks=not args.skip_crosschecks)
    return 0 if prov["validation"]["summary"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
