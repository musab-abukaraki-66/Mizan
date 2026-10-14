"""The committed dataset must be real, complete, consistent with its provenance and with the DoS release."""

import json

import pytest

from mizan import config
from mizan.ingest.crosscheck import PRESS_STATEMENTS, press_crosscheck
from mizan.series.loader import load_cpi, load_provenance, sha256_file
from mizan.series.validation import summarize, validate_series


@pytest.fixture(scope="module")
def cpi():
    return load_cpi()


def test_bundled_series_passes_validation(cpi):
    checks = validate_series(cpi, provenance=load_provenance(), csv_sha256=sha256_file(config.SERIES_CSV))
    assert summarize(checks)["ok"], [c for c in checks if c.status == "fail"]


def test_coverage_and_latest_month(cpi):
    assert cpi.index[0].strftime("%Y-%m") == "2006-01"
    assert cpi.index[-1].strftime("%Y-%m") == load_provenance()["series"]["last_period"]
    assert len(cpi) >= 12 * 8  # the task requires at least 8-10 years of history
    assert cpi.index.is_monotonic_increasing and not cpi.index.duplicated().any()


def test_base_year_average_is_100(cpi):
    assert cpi[cpi.index.year == 2018].mean() == pytest.approx(100.0, abs=1e-6)


def test_press_release_figures_reproduced(cpi):
    res = press_crosscheck(cpi)
    assert res["ok"], res
    assert len(res["results"]) == len(PRESS_STATEMENTS)


def test_provenance_record_complete():
    p = load_provenance()
    for key in ("publisher", "dataset", "landing_page", "terms_url"):
        assert p["source"][key]
    assert p["retrieval"]["retrieved_at_utc"].endswith("Z")
    assert len(p["retrieval"]["files"]) >= 20
    assert all(len(f["sha256"]) == 64 for f in p["retrieval"]["files"])
    assert p["series"]["csv_sha256"] == sha256_file(config.SERIES_CSV)
    assert p["series"]["base"].startswith("2018")
    assert "not" in p["license"]["dos"].lower() and "raw" in p["license"]["dos"].lower()


def test_raw_workbooks_are_not_committed():
    gi = (config.ROOT / ".gitignore").read_text()
    assert "data/raw/" in gi


def test_provenance_json_is_valid_json():
    json.loads(config.PROVENANCE_JSON.read_text(encoding="utf-8"))
