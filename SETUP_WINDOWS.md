# Setup on Windows

## What you need (once)
* **Windows 10/11**, a modest laptop is enough (≈ 400 MB disk, 4 GB RAM).
* **Python 3.10 – 3.13** (3.12 recommended): <https://www.python.org/downloads/> → during install tick **"Add python.exe to PATH"**.
* **Internet only for the first run**, to install the pinned Python packages. After that MIZAN runs fully offline.
* Node.js is **not** needed (the web UI is pre-built and committed in `mizan/web`).

## First time
1. Download / clone this repository (green **Code → Download ZIP**, then *Extract All*).
2. Double-click **`START_MIZAN.bat`**.
   * It creates `.venv`, installs `requirements.txt` (pinned), validates the data, checks the cached results and starts the server.
   * Your browser opens **http://127.0.0.1:8765/** (if that port is busy it uses 8766 … 8774 and prints the address).
3. Keep the black window open while presenting. Close it, press **Ctrl+C**, or double-click **`STOP_MIZAN.bat`** to stop.

Double-clicking START again while MIZAN is already running just re-opens the browser (no duplicate servers).

## Manual fallback (PowerShell or cmd, inside the project folder)
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m mizan validate
.\.venv\Scripts\python -m mizan serve --port 8765
# then open http://127.0.0.1:8765/
```
Optional – rebuild cached forecasts (≈ 2–6 minutes): `.\.venv\Scripts\python -m mizan backtest --force`.

## Troubleshooting
| Symptom | Fix |
|---|---|
| "Python was not found" | Install Python (see above) and tick *Add to PATH*; or use `py -3 launcher.py`. |
| `pip` fails / proxy | Connect to the internet once; behind a proxy set `HTTPS_PROXY`. Or pre-install on another machine. |
| "Python 3.14 … no matching distribution" | Install Python 3.12 (wheels for the pinned packages exist for 3.10–3.13). |
| Windows SmartScreen / antivirus warns about the .bat | Choose *More info → Run anyway*, or run the manual commands above. |
| Port in use | The launcher picks the next free port automatically; read the printed URL. |
| Blank page / "server not reachable" | The black window was closed. Run START_MIZAN.bat again. |
| Stale-results warning | Run `.\.venv\Scripts\python -m mizan backtest --force`. |
| Need logs | `runtime\mizan.log` |
| Corporate laptop blocks scripts | Use the manual fallback; nothing needs administrator rights. |

## Developer setup (optional)
```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt     # Windows: .venv\Scripts\...
cd frontend && npm ci && npm run build        # rebuilds mizan/web
pytest -q && ruff check . && (cd frontend && npm test && npm run lint && npm run e2e)
```
