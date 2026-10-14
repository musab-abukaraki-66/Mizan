import json

import pandas as pd
import pytest

from mizan import config
from mizan.config import ExperimentConfig
from mizan.forecasting import pipeline as pl
from tests.conftest import make_series


def test_accuracy_tables_and_champions_on_small_synthetic_fixture(synth):
    cfg = ExperimentConfig(horizons=(1, 3), max_horizon=3, min_train=36, test_months=12, reselect_every=6)
    results = {m: pl.bt.backtest_model(m, synth, cfg) for m in ("naive", "drift")}
    rows = pd.concat([r.rows for r in results.values()], ignore_index=True)
    rows = pl.iv.add_calibrated_intervals(rows, cfg.levels)
    acc = pl.mx.accuracy(rows[(rows["model"] == "naive") & (rows["h"] == 1)], 0.5)
    assert acc["n"] > 0
    # restrict MODELS used by pick_champions to what we computed
    saved = dict(pl.MODELS)
    try:
        pl.MODELS.clear()
        pl.MODELS.update({k: saved[k] for k in ("naive", "drift")})
        tables = pl.accuracy_tables(rows, 0.5, cfg)
        champs = pl.pick_champions(tables, cfg)
    finally:
        pl.MODELS.clear()
        pl.MODELS.update(saved)
    assert set(champs) == {"1", "3"}
    for h, c in champs.items():
        assert c["model"] in ("naive", "drift")
        dev = {m: tables[m][h]["dev"]["rmse"] for m in ("naive", "drift")}
        assert dev[c["model"]] == min(dev.values())  # champion = best DEVELOPMENT rmse, test only reported
        assert c["test_rmse"] == tables[c["model"]][h]["test"]["rmse"]


def test_cache_key_changes_with_data_and_config():
    k1 = pl.compute_cache_key("a" * 64)
    assert k1 == pl.compute_cache_key("a" * 64)
    assert k1 != pl.compute_cache_key("b" * 64)
    assert k1 != pl.compute_cache_key("a" * 64, ExperimentConfig(min_train=60))


def test_bundled_results_are_fresh_and_consistent():
    assert pl.results_are_fresh(), "data/results/results.json is stale - run: python -m mizan backtest --force"
    r = pl.load_results()
    n = r["meta"]["observations"]
    d = r["meta"]["design"]
    assert r["meta"]["as_of"] == pd.read_csv(config.SERIES_CSV)["period"].iloc[-1]
    for h in ("1", "3", "6"):
        assert d["origins_by_horizon"][h]["test"] == r["meta"]["config"]["test_months"]
        # every model is scored on the identical sample
        ns = {m: r["accuracy"][m][h]["all"]["n"] for m in r["accuracy"]}
        assert len(set(ns.values())) == 1, ns
        champ = r["champions"][h]
        dev = {m: r["accuracy"][m][h]["dev"]["rmse"] for m in r["accuracy"]}
        assert dev[champ["model"]] == min(dev.values())
    assert n >= 96 + 24


def test_bundled_results_intervals_ordered():
    r = pl.load_results()
    for m, e in r["forecasts"]["models"].items():
        for tag in ("80", "95"):
            for lo, mean, hi in zip(e[f"lo{tag}"], e["mean"], e[f"hi{tag}"]):
                assert lo <= mean + 1e-6 <= hi + 2e-6, (m, tag)
        for lo80, lo95, hi80, hi95 in zip(e["lo80"], e["lo95"], e["hi80"], e["hi95"]):
            assert lo95 <= lo80 and hi95 >= hi80


def test_results_json_is_plain_json():
    json.loads(config.RESULTS_JSON.read_text(encoding="utf-8"))


def test_build_results_refuses_when_validation_fails(tmp_path, monkeypatch):
    bad = tmp_path / "s.csv"
    bad.write_text("period,cpi\n2020-01,100\n2020-03,101\n", encoding="utf-8")  # missing 2020-02
    monkeypatch.setattr(config, "SERIES_CSV", bad)
    with pytest.raises(RuntimeError, match="validation failed"):
        pl.build_results(parallel=False)


def test_final_forecast_horizons_follow_last_observation(synth):
    cfg = ExperimentConfig(horizons=(1, 3), max_horizon=3, min_train=36, test_months=12)
    rows = pl.bt.backtest_model("naive", synth, cfg).rows
    rows = pl.iv.add_calibrated_intervals(rows, cfg.levels)
    saved = dict(pl.MODELS)
    try:
        pl.MODELS.clear()
        pl.MODELS["naive"] = saved["naive"]
        out = pl.final_forecasts(synth, cfg, rows)
    finally:
        pl.MODELS.clear()
        pl.MODELS.update(saved)
    assert out["as_of"] == synth.index[-1].strftime("%Y-%m")
    assert out["periods"][0] == (synth.index[-1] + pd.offsets.MonthBegin(1)).strftime("%Y-%m")
    assert len(out["periods"]) == 3 and len(out["models"]["naive"]["mean"]) == 3
    assert make_series is not None
