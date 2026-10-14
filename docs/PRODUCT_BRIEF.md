# MIZAN – Product brief

**Name:** MIZAN (ميزان) · **Descriptor:** Jordan Forecasting & Statistical Intelligence Lab
**Tagline:** From Official Statistics to Reliable Forecasts.

## Problem
Official statistics are published as tables; forecasting experiments are usually shown as a single line with no evidence
of how well the method performed on history it had not seen. MIZAN shows the whole chain – traceable data → transparent
models → honest out-of-sample evidence → clearly labelled forecasts – for one indicator, done carefully.

## Users
* Statisticians and analysts at a national statistics office who want to see a reproducible forecasting workflow.
* Interviewers / reviewers who need a 2-minute, non-technical explanation and a defensible technical appendix.

## Scope (v1) – one indicator, done completely
Jordan's **monthly headline CPI (2018 = 100)**, Jan 2006 – Sep 2026 (249 months).

| In scope | Out of scope (deliberately) |
|---|---|
| Verified source series with provenance & checksums | GDP nowcasting, unemployment, other indicators |
| MoM / YoY inflation (explicit formulas) | CPI sub-groups (the data model can take them later) |
| Naive, seasonal naive, drift, ETS, SARIMA | Machine-learning / multivariate models |
| Rolling-origin backtests, untouched test window, DM test | Scenario / policy simulation |
| 80 % / 95 % prediction intervals, with measured coverage | Any claim of causality or policy advice |
| Arabic (RTL) + English, presentation mode, Windows launcher | Cloud hosting, accounts, databases |

## Principles
1. Real data only by default; synthetic data exists only in test fixtures.
2. Observed ≠ derived ≠ forecast – always visually and verbally distinct.
3. Report honestly when a complex model does **not** beat the naive baseline.
4. Never imply official status: MIZAN is an independent project.
5. Runs offline on a modest Windows laptop.
