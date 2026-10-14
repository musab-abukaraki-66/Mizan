import socket
import sys

from fastapi.testclient import TestClient

import launcher
from mizan.api.main import app


def test_venv_python_path_matches_platform():
    p = launcher.venv_python()
    assert p.parent.parent.name == ".venv"
    assert p.name == ("python.exe" if sys.platform == "win32" else "python")


def test_choose_port_skips_busy_foreign_port():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0))
    s.listen()
    busy = s.getsockname()[1]
    try:
        port, running = launcher.choose_port(busy)
        assert port != busy and not running
    finally:
        s.close()


def test_tail_handles_missing_file(tmp_path):
    assert launcher.tail(tmp_path / "nope.log") == "(no log)"


def test_batch_files_use_crlf_and_reference_launcher():
    start = (launcher.ROOT / "START_MIZAN.bat").read_bytes()
    assert b"\r\n" in start and b"launcher.py" in start
    assert b"taskkill" in (launcher.ROOT / "STOP_MIZAN.bat").read_bytes()


def test_prebuilt_frontend_is_served_by_the_api():
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code == 200 and "<div id=\"root\">" in r.text
    assert c.get("/#/studio").status_code == 200
    assert c.get("/favicon.svg").status_code == 200
    assert c.get("/..%2f..%2fpyproject.toml").text.startswith("<!doctype html>")  # no path traversal; SPA fallback
