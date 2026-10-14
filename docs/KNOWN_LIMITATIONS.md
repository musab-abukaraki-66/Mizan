# Known limitations

* **Data licence:** DoS grants no open licence; only the extracted headline series is bundled (see DATA_SOURCES.md).
* **2018 discrepancy vs IMF:** 12 months of 2018 differ from the IMF's copy (max 0.72 index points); cause not determined.
* **2018 basket link:** Dec 2017 → Jan 2018 includes a one-time basket link; models see it as a jump.
* **Short, calm test window:** 24 months of ~2 % inflation. Rankings may change in a more volatile period; DM tests have low power with overlapping multi-step errors.
* **Statistical models do not significantly beat naive** at any horizon on the development window. The selected model at 3 and 6 months is therefore the naive baseline (a flat forecast), even though SARIMA/drift did better on the recent test window.
* **Intervals are imperfect:** model-based ETS/SARIMA bands over-cover; calibrated bands depend on past error scale and can be too wide in calm periods or too narrow after a regime change.
* **Univariate:** no information on tax/subsidy changes, fuel prices or exchange rates; no causal claims.
* **Headline CPI only**; sub-groups (COICOP) are not modelled yet.
* **Windows launcher not executed on Windows in this build:** it was developed and tested on Linux (the Python launcher, health checks, port fallback and stop logic all ran); `.bat` wrappers are simple and reviewed but unverified on a real Windows machine.
* **Light theme only** (no dark mode).
* **Browser coverage:** end-to-end tests ran in Chromium only.
* No Haiku sub-model was used; all work was done with the primary model.
