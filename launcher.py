#!/usr/bin/env python3
"""MIZAN launcher - one command to set up (first run) and start the demo.

Uses only the Python standard library so it can run before any dependency is installed.
Steps: check Python -> create .venv -> install pinned requirements (first run / when changed)
-> validate the bundled data -> rebuild cached results only if stale -> pick a free port ->
start the server -> wait for /api/health -> open the browser.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
RUNTIME = ROOT / "runtime"
PID_FILE = RUNTIME / "mizan.pid"
PORT_FILE = RUNTIME / "mizan.port"
LOG_FILE = RUNTIME / "mizan.log"
REQ = ROOT / "requirements.txt"
MARKER = VENV / ".mizan-requirements.sha256"
DEFAULT_PORT = 8765
MIN_PY, MAX_PY = (3, 10), (3, 13)
IS_WIN = os.name == "nt"


def say(msg: str = "") -> None:
    print(msg, flush=True)


def fail(msg: str, hint: str = "") -> None:
    say(f"\n[MIZAN] ERROR: {msg}")
    if hint:
        say(f"        {hint}")
    say("        More help: SETUP_WINDOWS.md (Troubleshooting).")
    sys.exit(1)


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def check_python() -> None:
    v = sys.version_info[:2]
    say(f"[MIZAN] Python {sys.version.split()[0]} found.")
    if v < MIN_PY:
        fail(f"Python {MIN_PY[0]}.{MIN_PY[1]} or newer is required.",
             "Install Python 3.12 from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'.")
    if v > MAX_PY:
        say(f"[MIZAN] Note: tested on Python {MIN_PY[0]}.{MIN_PY[1]}-{MAX_PY[0]}.{MAX_PY[1]}. "
            "Newer versions may lack prebuilt packages; if installation fails, install Python 3.12.")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, **kw)


def ensure_venv(skip_install: bool) -> Path:
    py = venv_python()
    if not py.exists():
        say("[MIZAN] Creating local virtual environment (.venv) - first run only ...")
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
        if not py.exists():
            fail("Could not create the virtual environment.", "Try: python -m venv .venv")
    want = hashlib.sha256(REQ.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    have = MARKER.read_text().strip() if MARKER.exists() else ""
    if want != have and not skip_install:
        say("[MIZAN] Installing pinned dependencies (needs internet this one time) ...")
        r = run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQ)])
        if r.returncode != 0:
            fail("Dependency installation failed.",
                 "Check your internet connection / proxy, then run START_MIZAN.bat again.")
        MARKER.write_text(want)
    return py


def data_ok(py: Path) -> None:
    say("[MIZAN] Checking the bundled data and its provenance ...")
    r = run([str(py), "-m", "mizan", "validate"], capture_output=True, text=True)
    if r.returncode != 0:
        say(r.stdout[-1500:])
        fail("Data validation failed.", "Do not demo with unverified data. Run: python -m mizan ingest")
    say("        " + r.stdout.strip().splitlines()[-1])


def ensure_results(py: Path) -> None:
    code = "import sys; from mizan.forecasting import pipeline; sys.exit(0 if pipeline.results_are_fresh() else 1)"
    if run([str(py), "-c", code]).returncode == 0:
        say("[MIZAN] Cached forecast results are up to date.")
        return
    say("[MIZAN] Cached results are missing or out of date - rebuilding (a few minutes, one time) ...")
    if run([str(py), "-m", "mizan", "backtest", "--force"]).returncode != 0:
        fail("Could not rebuild the forecast results.")


def health(port: int, timeout: float = 1.5) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0 if IS_WIN else 1)
        return s.connect_ex(("127.0.0.1", port)) != 0


def choose_port(preferred: int) -> tuple[int, bool]:
    """Return (port, already_running). Reuses a running MIZAN, never kills foreign processes."""
    for port in range(preferred, preferred + 10):
        h = health(port)
        if h and h.get("app") == "mizan":
            return port, True
        if port_free(port):
            if port != preferred:
                say(f"[MIZAN] Port {preferred} is used by another program - using {port} instead.")
            return port, False
    fail(f"No free port between {preferred} and {preferred + 9}.", "Close other local servers and retry.")
    raise SystemExit(1)


def tail(path: Path, n: int = 30) -> str:
    try:
        return "\n".join(path.read_text(errors="replace").splitlines()[-n:])
    except OSError:
        return "(no log)"


def serve(py: Path, port: int, open_browser: bool) -> None:
    RUNTIME.mkdir(exist_ok=True)
    url = f"http://127.0.0.1:{port}/"
    say(f"[MIZAN] Starting server on {url} ...")
    log = open(LOG_FILE, "w", encoding="utf-8")
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if IS_WIN else 0
    proc = subprocess.Popen([str(py), "-m", "mizan", "serve", "--port", str(port)], cwd=ROOT,
                            stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    PID_FILE.write_text(str(proc.pid))
    PORT_FILE.write_text(str(port))
    deadline = time.time() + 90
    ok = False
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        h = health(port)
        if h and h.get("app") == "mizan":
            ok = True
            if h.get("status") != "ok":
                say(f"[MIZAN] Warning: server reports status '{h.get('status')}' (see /api/health).")
            break
        time.sleep(0.5)
    if not ok:
        log.flush()
        say(tail(LOG_FILE))
        proc.kill()
        fail("The server did not become ready.", f"Log: {LOG_FILE}")
    say("[MIZAN] Ready.  Opening your browser ...")
    say(f"\n        >>>  {url}  <<<\n")
    say("        Keep this window open while presenting. Close it (or press Ctrl+C) to stop MIZAN,")
    say("        or run STOP_MIZAN.bat.\n")
    if open_browser:
        webbrowser.open(url)
    try:
        proc.wait()
    except KeyboardInterrupt:
        say("\n[MIZAN] Stopping ...")
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        for f in (PID_FILE, PORT_FILE):
            f.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Set up and start MIZAN")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--skip-install", action="store_true", help="do not run pip (offline use)")
    ap.add_argument("--check", action="store_true", help="run all checks, do not start the server")
    args = ap.parse_args()

    say("=" * 60)
    say("  MIZAN - Jordan Forecasting & Statistical Intelligence Lab")
    say("=" * 60)
    check_python()
    py = ensure_venv(args.skip_install)
    data_ok(py)
    ensure_results(py)
    if not (ROOT / "mizan" / "web" / "index.html").exists():
        fail("The front-end bundle (mizan/web) is missing.",
             "Re-download the repository, or build it with Node: cd frontend && npm ci && npm run build")
    if args.check:
        say("[MIZAN] All checks passed.")
        return
    port, running = choose_port(args.port)
    if running:
        say(f"[MIZAN] MIZAN is already running on port {port} - opening it.")
        if not args.no_browser:
            webbrowser.open(f"http://127.0.0.1:{port}/")
        return
    serve(py, port, not args.no_browser)


if __name__ == "__main__":
    main()
