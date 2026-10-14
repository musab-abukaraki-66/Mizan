# Methodology

## Definitions
```
Monthly change  = 100 * (CPI[t] / CPI[t-1]  - 1)
Annual change   = 100 * (CPI[t] / CPI[t-12] - 1)
Average-to-date = 100 * (mean CPI Jan..m this year / mean CPI Jan..m last year - 1)   # the "first N months" figure in DoS releases
```
CPI measures the price of a defined consumer basket; it is *not* "the cost of living".

## Models (all fitted only on data up to the forecast origin)
| id | Model | Notes |
|---|---|---|
| `naive` | last value | random-walk intervals from the log one-step changes of the last 60 months |
| `seasonal_naive` | same month last year | required benchmark; poor on a trending index by construction |
| `drift` | last value × average monthly growth of the previous 12 months | `σ·√(h + h²/12)` |
| `ets` | additive-error ETS on log CPI | trend ∈ {none, additive, damped} × seasonality ∈ {none, additive}, chosen by AICc |
| `sarima` | ARIMA(p,1,q)(P,0,Q)₁₂ + drift on log CPI | 12 specs, AICc; falls back to the next-best spec if the best does not converge |

Specification search is repeated every 6 origins (`reselect_every`); parameters are re-estimated at **every** origin.

## Backtest and leakage control
* Chronological, expanding window, **rolling origin**: first origin after `min_train = 96` months (Dec 2013); 153 origins.
* Horizons 1, 3, 6 are scored (all of 1–6 are produced, because calibration needs them).
* **Development window:** targets Jan 2014 – Sep 2024 → used to pick the model per horizon (lowest RMSE).
  **Final test window:** the last `test_months = 24` target months (Oct 2024 – Sep 2026) → never used for selection, reported separately.
* Nothing after an origin reaches a model: enforced by tests that rewrite all later data and assert forecasts at earlier
  origins are bit-identical (`tests/test_backtest.py`, `tests/test_models.py`).
* **Common sample:** every model is scored on the same (origin, horizon) pairs, so a model that fails at some origin
  cannot look better by being scored on fewer months (failures are counted and shown).

## Metrics
MAE and RMSE on the index (index points); **MASE** (scale = in-sample one-step naive MAE of the first 96 months = 0.516);
**inflation error** = MAE/RMSE of the implied annual rate in percentage points – reported separately; MAPE kept for
reference only. **Diebold–Mariano** test (squared-error loss) with the Harvey–Leybourne–Newbold small-sample correction
compares each model with naive.

## Prediction intervals
* *Model-based:* from the fitted error model (ETS, SARIMA) or random-walk scaling (baselines).
* *Calibrated (default):* half-width = the `⌈(n+1)·L⌉/n` empirical quantile of the model's own past out-of-sample
  |log(actual/forecast)| errors **that were already observable at the origin** (online split-conformal style; ≥ 24 errors needed).
* Empirical coverage of both is measured in the backtest. Model-based ETS/SARIMA intervals over-cover (≈ 95 % for nominal 80 %)
  because their σ is dominated by volatile 2007-08 history; calibrated intervals are closer to nominal (≈ 82-99 % for naive, drift, ETS and SARIMA in the
  development window; wider than needed in the calm test window). Neither is a guarantee.

## What the evidence says (from the committed run)
* **1 month:** SARIMA has the lowest development RMSE (0.447 vs 0.464 naive, −3.5 %), not statistically significant (DM p = 0.50); on the test window 0.326 vs 0.406.
* **3 and 6 months:** the naive baseline has the lowest *development* RMSE (0.983 and 1.575), so it is the selected model. On the final test window SARIMA (0.802, 1.050) and drift were more accurate than naive (0.967, 1.568) – differences are **not** significant at 5 % and rest on 24 months.
* No statistical model is significantly better than naive at any horizon on the development window. MIZAN reports this rather than choosing the prettiest line.

## Limits
Univariate extrapolation; no policy, fuel-price or exchange-rate information; no causality; short test window; known 2018 basket link; forecasts are not official estimates.
