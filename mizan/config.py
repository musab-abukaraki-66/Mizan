"""Central configuration: paths and the (frozen) forecasting-experiment design."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"  # downloaded source workbooks - git-ignored, never redistributed
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"
SERIES_CSV = PROCESSED_DIR / "jordan_cpi_monthly.csv"
PROVENANCE_JSON = PROCESSED_DIR / "provenance.json"
RESULTS_JSON = RESULTS_DIR / "results.json"
WEB_DIR = Path(__file__).resolve().parent / "web"  # pre-built front-end bundle
RUNTIME_DIR = ROOT / "runtime"  # logs / pid files - git-ignored

DOS_PAGE_URL = "https://dosweb.dos.gov.jo/economic/price-indices/table-price-indices/"
DOS_FILE_URL = "https://dosweb.dos.gov.jo/DataBank/Economic/Price_Indices/CPI/{year}.xlsx"
FIRST_YEAR = 2006  # first year DoS publishes on the 2018=100 base


@dataclass(frozen=True)
class ExperimentConfig:
    """Design of the forecasting experiment. Changing any value invalidates the cache."""

    horizons: tuple[int, ...] = (1, 3, 6)
    max_horizon: int = 6
    min_train: int = 96  # 8 years of monthly history before the first forecast origin
    test_months: int = 24  # final, untouched evaluation window (by target month)
    reselect_every: int = 6  # re-run order selection every N origins (parameters refit each origin)
    levels: tuple[float, ...] = (0.80, 0.95)
    drift_window: int = 12  # trailing window (months) for the drift baseline
    seasonal_period: int = 12


EXPERIMENT = ExperimentConfig()
