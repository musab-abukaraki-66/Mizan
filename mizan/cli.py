"""Command line: python -m mizan <ingest|validate|backtest|serve|status>."""

from __future__ import annotations

import argparse
import sys

from mizan import config


def _validate() -> int:
    from mizan.series.loader import load_cpi, load_provenance, sha256_file
    from mizan.series.validation import summarize, validate_series

    cpi = load_cpi()
    checks = validate_series(cpi, provenance=load_provenance(), csv_sha256=sha256_file(config.SERIES_CSV))
    for c in checks:
        print(f"[{c.status.upper():4}] {c.label}: {c.detail}")
    s = summarize(checks)
    print(f"\n{s['passed']} passed, {s['warnings']} warnings, {s['failed']} failed; "
          f"{len(cpi)} months, latest {cpi.index[-1]:%Y-%m}")
    return 0 if s["ok"] else 1


def _backtest(force: bool) -> int:
    from mizan.forecasting import pipeline

    if not force and pipeline.results_are_fresh():
        print("cached results are up to date (use --force to rebuild)")
        return 0
    print("running rolling-origin backtests (this takes a few minutes) ...", flush=True)
    bundle = pipeline.build_results()
    path = pipeline.save_results(bundle)
    print(f"wrote {path}")
    return 0


def _serve(host: str, port: int) -> int:
    import uvicorn

    uvicorn.run("mizan.api.main:app", host=host, port=port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mizan", description="MIZAN forecasting lab")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ing = sub.add_parser("ingest", help="download + verify the DoS CPI series")
    ing.add_argument("--from-raw", action="store_true")
    ing.add_argument("--skip-crosschecks", action="store_true")
    sub.add_parser("validate", help="validate the bundled series")
    bt = sub.add_parser("backtest", help="(re)build cached backtest results")
    bt.add_argument("--force", action="store_true")
    ex = sub.add_parser("export-static", help="write the API as static JSON for static hosting")
    ex.add_argument("--out", default="site")
    sv = sub.add_parser("serve", help="start the web app")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    if args.cmd == "ingest":
        from mizan.ingest.run import main as ingest_main

        flags = (["--from-raw"] if args.from_raw else []) + (["--skip-crosschecks"] if args.skip_crosschecks else [])
        return ingest_main(flags)
    if args.cmd == "validate":
        return _validate()
    if args.cmd == "backtest":
        return _backtest(args.force)
    if args.cmd == "export-static":
        from pathlib import Path

        from mizan.export_static import export

        print(f"exported {export(Path(args.out))} files to {args.out}/api")
        return 0
    return _serve(args.host, args.port)


if __name__ == "__main__":
    sys.exit(main())
