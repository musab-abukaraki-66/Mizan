"""Export every API response the UI can request as a static JSON file.

The web app only reads precomputed results, so it can be hosted as a plain static site
(no Python server). File layout (mirrored by frontend/src/lib/api.ts in static mode):

    api/{meta,series,overview,arena,quality}.json
    api/forecast/{horizon}/{model|champion}/{calibrated|model}.json
    api/backtest/{model}/{horizon}.json
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from mizan.api.main import app
from mizan.forecasting.models import MODELS

HORIZONS = (1, 3, 6)


def export(out: Path) -> int:
    client = TestClient(app)
    api = out / "api"
    n = 0

    def save(url: str, rel: str) -> None:
        nonlocal n
        r = client.get(url)
        if r.status_code != 200:
            raise RuntimeError(f"{url} -> {r.status_code}: {r.text[:200]}")
        dest = api / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(r.json(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        n += 1

    for name in ("meta", "series", "overview", "arena", "quality"):
        save(f"/api/{name}", f"{name}.json")
    for h in HORIZONS:
        for interval in ("calibrated", "model"):
            save(f"/api/forecast?horizon={h}&interval={interval}", f"forecast/{h}/champion/{interval}.json")
            for m in MODELS:
                save(f"/api/forecast?horizon={h}&model={m}&interval={interval}", f"forecast/{h}/{m}/{interval}.json")
        for m in MODELS:
            save(f"/api/backtest?model={m}&horizon={h}", f"backtest/{m}/{h}.json")
    return n
