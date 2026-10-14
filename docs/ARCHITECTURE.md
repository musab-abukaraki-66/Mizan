# Architecture

```
 DoS yearly .xlsx ──► mizan.ingest ──► data/processed/jordan_cpi_monthly.csv + provenance.json
 (data/raw, ignored)   (parse, validate,        │
                        cross-check)            ▼
                              mizan.series (loader · transforms · validation)
                                                │
                                                ▼
                  mizan.forecasting  models ─► backtest ─► metrics/intervals ─► pipeline ──► data/results/results.json
                                                                                     (cache_key = data+code+config hash)
                                                │
                                                ▼
                          mizan.api (FastAPI)  /api/health /meta /series /overview /forecast /arena /backtest /quality
                                                │ serves JSON + the pre-built UI (mizan/web)
                                                ▼
                  frontend/ (React + TypeScript + Vite, custom SVG charts, bundled fonts; ar/en, RTL)
```
* **One process, one port.** FastAPI serves both the API and the static UI bundle (`mizan/web`, committed, rebuilt with
  `cd frontend && npm run build`). The demo laptop needs **only Python** at runtime – no Node, no internet, no external fonts/scripts.
* **Cache, not magic:** `results.json` is committed so the app opens instantly. `cache_key` hashes the data checksum, the
  experiment config and the forecasting source files; if anything changes, `/api/health` reports `results_fresh: false`
  and the launcher rebuilds (`python -m mizan backtest --force`, ≈ 2 min on 4 cores).
* **Boundaries:** ingestion (network, parsing) ∦ validation (pure) ∦ models (pure, train-only input) ∦ backtest (loop,
  no future access) ∦ metrics/intervals (pure) ∦ API (read-only) ∦ UI.
* **Tests:** `pytest` (95), `vitest` (15), Playwright e2e (11), `ruff`, `tsc --strict`, `eslint`.
* **Launcher:** `START_MIZAN.bat` → `launcher.py` (stdlib only): Python check → `.venv` → pinned `requirements.txt` →
  data validation → cache check → free port → health wait → browser. `STOP_MIZAN.bat` kills the recorded PID tree.
