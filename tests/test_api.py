import pytest
from fastapi.testclient import TestClient

from mizan import config
from mizan.api import state as S
from mizan.api.main import app
from mizan.series.loader import load_cpi

client = TestClient(app)
_CPI = load_cpi()
N = len(_CPI)
LAST = _CPI.index[-1].strftime("%Y-%m")
NEXT = (_CPI.index[-1] + __import__("pandas").offsets.MonthBegin(1)).strftime("%Y-%m")


@pytest.fixture(autouse=True)
def _reset_state():
    S.get_state(force=True)
    yield
    S.get_state(force=True)


def test_health():
    r = client.get("/api/health").json()
    assert r["app"] == "mizan" and r["status"] == "ok" and r["results_fresh"] and r["data_ok"]


def test_series_rows_and_derived_fields():
    d = client.get("/api/series").json()
    rows = d["rows"]
    assert len(rows) == N and rows[0]["mom"] is None and rows[11]["yoy"] is None and rows[12]["yoy"] is not None
    last, prev = rows[-1], rows[-2]
    assert last["mom"] == pytest.approx(100 * (last["cpi"] / prev["cpi"] - 1))
    assert last["yoy"] == pytest.approx(100 * (last["cpi"] / rows[-13]["cpi"] - 1))
    assert d["latest"]["period"] == last["period"] == LAST


def test_overview_has_forecast_for_each_horizon_with_ordered_bands():
    d = client.get("/api/overview").json()
    assert set(d["forecast_summary"]) == {"1", "3", "6"}
    for f in d["forecast_summary"].values():
        assert f["lower"] <= f["point"] <= f["upper"]
        assert f["champion"]["model"] == f["model"]


@pytest.mark.parametrize("h", [1, 3, 6])
def test_forecast_endpoint_shape(h):
    d = client.get(f"/api/forecast?horizon={h}").json()
    assert len(d["periods"]) == len(d["mean"]) == len(d["yoy"]) == h
    assert d["periods"][0] == NEXT
    for tag in ("80", "95"):
        b = d["bands"][tag]
        assert all(lo <= m <= hi for lo, m, hi in zip(b["lower"], d["mean"], b["upper"]))
    assert d["evaluation"]["dev"]["n"] > 0 and d["baseline_evaluation"]["test"]["n"] == 24


def test_forecast_model_and_interval_selection():
    a = client.get("/api/forecast?horizon=6&model=sarima&interval=model").json()
    b = client.get("/api/forecast?horizon=6&model=sarima&interval=calibrated").json()
    assert a["interval_method"] == "model" and b["interval_method"] == "calibrated"
    assert a["mean"] == b["mean"] and a["bands"]["80"] != b["bands"]["80"]


def test_error_handling():
    r = client.get("/api/forecast?model=nope")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "unknown_model"
    r = client.get("/api/forecast?horizon=4")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_horizon"
    assert client.get("/api/forecast?horizon=x").status_code == 422
    assert client.get("/api/backtest?model=nope&horizon=1").status_code == 404
    assert client.get("/api/backtest?model=naive&horizon=2").status_code == 422
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "not_found"


def test_backtest_and_arena():
    b = client.get("/api/backtest?model=ets&horizon=3").json()
    n = len(b["series"]["target"])
    assert n == b["metrics"]["all"]["n"] and len(b["series"]["actual"]) == n
    a = client.get("/api/arena").json()
    assert [m["id"] for m in a["models"]] == ["naive", "seasonal_naive", "drift", "ets", "sarima"]
    assert a["design"]["test_window"][1] == LAST


def test_quality_endpoint_exposes_provenance():
    q = client.get("/api/quality").json()
    assert q["live_validation"]["summary"]["ok"] and q["series"]["rows"] == N
    assert len(q["series"]["csv_sha256"]) == 64 and q["retrieval"]["files"]
    assert q["crosschecks"]["press_release"]["ok"] is True


def test_missing_results_returns_503_not_a_crash(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "RESULTS_JSON", tmp_path / "absent.json")
    S.get_state(force=True)
    r = client.get("/api/overview")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "results_unavailable"
    h = client.get("/api/health").json()
    assert h["status"] == "degraded" and h["results_available"] is False
    assert client.get("/api/series").status_code == 200  # data endpoints keep working


def test_stale_results_are_flagged(monkeypatch, tmp_path):
    import json
    stale = tmp_path / "r.json"
    data = json.loads(config.RESULTS_JSON.read_text(encoding="utf-8"))
    data["meta"]["cache_key"] = "stale"
    stale.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(config, "RESULTS_JSON", stale)
    S.get_state(force=True)
    assert client.get("/api/health").json()["results_fresh"] is False
