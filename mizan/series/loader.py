"""Load the verified monthly CPI series and its provenance record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from mizan import config


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cpi(path: Path | None = None) -> pd.Series:
    """Return the headline CPI as a float Series indexed by month start (freq=MS)."""
    path = path or config.SERIES_CSV
    df = pd.read_csv(path, dtype={"period": str})
    idx = pd.to_datetime(df["period"] + "-01")
    s = pd.Series(df["cpi"].astype(float).to_numpy(), index=pd.DatetimeIndex(idx, freq=None), name="cpi")
    s.index.name = "period"
    try:
        s.index.freq = "MS"
    except ValueError:  # gaps - leave freq unset; validation reports them
        pass
    return s


def load_provenance(path: Path | None = None) -> dict[str, Any]:
    path = path or config.PROVENANCE_JSON
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
